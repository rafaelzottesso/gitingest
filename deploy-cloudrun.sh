#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Deploy & Cost-Control Script for Gitingest on Google Cloud Run
# ==============================================================================
# Configuration (override via environment variables if needed)
PROJECT_ID="${PROJECT_ID:-gitingest-514516}"
SERVICE_NAME="${SERVICE_NAME:-gitingest}"
REGION="${REGION:-us-central1}"
CUSTOM_DOMAIN="${CUSTOM_DOMAIN:-gitingest.zotts.com.br}"

# gcloud account used for every command in this script (does not change your global gcloud config)
GCLOUD_ACCOUNT="${GCLOUD_ACCOUNT:-rafael.zottesso@ifpr.edu.br}"
export CLOUDSDK_CORE_ACCOUNT="${GCLOUD_ACCOUNT}"

# Cloud Run Free-Tier friendly settings:
# - min-instances=0: scales to zero when idle ($0 idle cost)
# - cpu-throttling: request-based billing (billed only during active requests)
# - max-instances=1: caps cost and ensures /tmp digest downloads hit the same instance
# - 1 vCPU + 1Gi RAM: fits cleanly in Always Free Tier (180k vCPU-s, 360k GiB-s/mo)
CPU="${CPU:-1}"
MEMORY="${MEMORY:-1Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-1}"
CONCURRENCY="${CONCURRENCY:-10}"
TIMEOUT="${TIMEOUT:-120}"

# Retention policies
KEEP_REVISIONS="${KEEP_REVISIONS:-3}"
KEEP_IMAGES="${KEEP_IMAGES:-2}"
STAGING_BUCKET_RETENTION_DAYS="${STAGING_BUCKET_RETENTION_DAYS:-7}"

ALLOWED_HOSTS="${ALLOWED_HOSTS:-${CUSTOM_DOMAIN},*.run.app,*.a.run.app,localhost,127.0.0.1}"
AR_REPO="${AR_REPO:-cloud-run-source-deploy}"
IMAGE_PATH="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${SERVICE_NAME}"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "==> [1/5] Deploying '${SERVICE_NAME}' to Cloud Run (${PROJECT_ID} / ${REGION})..."
gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --source=. \
  --region="${REGION}" \
  --allow-unauthenticated \
  --min-instances="${MIN_INSTANCES}" \
  --max-instances="${MAX_INSTANCES}" \
  --cpu="${CPU}" \
  --memory="${MEMORY}" \
  --concurrency="${CONCURRENCY}" \
  --timeout="${TIMEOUT}" \
  --cpu-throttling \
  --set-env-vars="^@^ALLOWED_HOSTS=${ALLOWED_HOSTS}" \
  --quiet

echo "==> [2/5] Cleaning up old Cloud Run revisions (keeping latest ${KEEP_REVISIONS})..."
ACTIVE_REVISIONS="$(
  gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format="value(status.traffic[].revisionName)" \
    --quiet | tr ';' '\n' | sort -u
)"

ALL_REVISIONS="$(
  gcloud run revisions list \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --service="${SERVICE_NAME}" \
    --sort-by="~metadata.creationTimestamp" \
    --format="value(metadata.name)" \
    --quiet
)"

rev_index=0
while IFS= read -r rev; do
  [[ -z "$rev" ]] && continue
  rev_index=$((rev_index + 1))
  if (( rev_index <= KEEP_REVISIONS )); then
    continue
  fi
  if printf '%s\n' "${ACTIVE_REVISIONS}" | grep -qx "${rev}"; then
    echo "    Skipping active revision: ${rev}"
    continue
  fi
  echo "    Deleting old revision: ${rev}"
  gcloud run revisions delete "${rev}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --quiet
done <<< "${ALL_REVISIONS}"

echo "==> [3/5] Applying Artifact Registry cleanup policy (keep ${KEEP_IMAGES} versions)..."
cat > "${TMP_DIR}/ar-cleanup-policy.json" <<EOF
[
  {
    "name": "keep-recent-versions",
    "action": {"type": "Keep"},
    "mostRecentVersions": {
      "keepCount": ${KEEP_IMAGES}
    }
  },
  {
    "name": "delete-old-versions",
    "action": {"type": "Delete"},
    "condition": {
      "tagState": "any",
      "olderThan": "1d"
    }
  }
]
EOF

gcloud artifacts repositories set-cleanup-policies "${AR_REPO}" \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --policy="${TMP_DIR}/ar-cleanup-policy.json" \
  --no-dry-run \
  --quiet

echo "==> [4/5] Deleting older Artifact Registry image digests immediately (keeping latest ${KEEP_IMAGES})..."
ALL_DIGESTS="$(
  gcloud artifacts docker images list "${IMAGE_PATH}" \
    --project="${PROJECT_ID}" \
    --include-tags \
    --sort-by="~UPDATE_TIME" \
    --format="value(version)" \
    --quiet || true
)"

img_index=0
while IFS= read -r digest; do
  [[ -z "$digest" ]] && continue
  img_index=$((img_index + 1))
  if (( img_index <= KEEP_IMAGES )); then
    continue
  fi
  echo "    Deleting old image digest: ${digest}"
  gcloud artifacts docker images delete "${IMAGE_PATH}@${digest}" \
    --project="${PROJECT_ID}" \
    --delete-tags \
    --quiet || true
done <<< "${ALL_DIGESTS}"

echo "==> [5/5] Ensuring GCS Cloud Build / source staging buckets auto-expire after ${STAGING_BUCKET_RETENTION_DAYS} days..."
cat > "${TMP_DIR}/gcs-lifecycle.json" <<EOF
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {"age": ${STAGING_BUCKET_RETENTION_DAYS}}
    }
  ]
}
EOF

for bucket in \
  "gs://run-sources-${PROJECT_ID}-${REGION}" \
  "gs://${PROJECT_ID}_cloudbuild"; do
  if gcloud storage buckets describe "${bucket}" --project="${PROJECT_ID}" --quiet >/dev/null 2>&1; then
    gcloud storage buckets update "${bucket}" \
      --project="${PROJECT_ID}" \
      --lifecycle-file="${TMP_DIR}/gcs-lifecycle.json" \
      --quiet
    echo "    Lifecycle rule applied to ${bucket}"
  fi
done

SERVICE_URL="$(
  gcloud run services describe "${SERVICE_NAME}" \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format="value(status.url)" \
    --quiet
)"

echo ""
echo "Deploy complete!"
echo "Service URL: ${SERVICE_URL}"
