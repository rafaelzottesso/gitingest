# Gitingest

![Screenshot of Gitingest front page](docs/frontpage.png)


Turn any Git repository into a prompt-friendly text ingest for LLMs.

> **This is a personal/academic fork** of [coderamp-labs/gitingest](https://github.com/coderamp-labs/gitingest)
> (by Romain Courtois, Filip Christiansen and contributors), released under the [MIT License](./LICENSE).
> It is not affiliated with, endorsed by, or the same service as [gitingest.com](https://gitingest.com).
> It is not published to PyPI and is not maintained as a public project: install and run it from source.

## 🔀 What is different in this fork

- **Include and exclude together (web UI and API)**: the web form has separate *Include* and *Exclude* fields, so you
  can, for example, include `*.py` and exclude `__init__.py` in the same run. The API accepts `include_pattern` and
  `exclude_pattern` (the old `pattern_type` + `pattern` pair is still accepted and mapped to the new fields).
- **Token-saving options** (opt-in checkboxes under *Reduce tokens*, also API parameters):
  - `compact_whitespace`: trims trailing spaces, collapses blank-line runs and shrinks consistent 4-space indentation to 2.
  - `strip_comments`: removes comments (and Python docstrings) for Python, JS/TS, Java, C-family, Go, Rust, PHP and CSS, and
    full-line `#` comments for shell, Ruby, YAML, TOML and Dockerfile. Files that cannot be parsed safely are left untouched.
    It is lossy and heuristic (e.g. a JavaScript regex literal containing `//` may be misread), so it is off by default.
  - `compact_format`: short `### path` file headers and a plain indented tree instead of `====` blocks and box-drawing characters.
- **Compatibility**: templates use the request-first `TemplateResponse(request, name, context)` signature, so the server runs on
  current Starlette (1.x) as well as older releases.

These options exist only in the web server and its API; the `gitingest` CLI and the Python `ingest()` function have no flags for them yet.

## 🚀 Features

- **Easy code context**: Get a text digest from a Git repository URL or a directory
- **Smart Formatting**: Optimized output format for LLM prompts
- **Statistics about**:
  - File and directory structure
  - Size of the extract
  - Token count
- **CLI tool**: Run it as a shell command
- **Python package**: Import it in your code

## 📚 Requirements

- Python 3.8+
- For private repositories: A GitHub Personal Access Token (PAT). [Generate your token **here**!](https://github.com/settings/tokens/new?description=gitingest&scopes=repo)

### 📦 Installation (from source)

This fork is not on PyPI (the `gitingest` package there is the original project). Clone it and install in a virtual environment:

```bash
git clone https://github.com/rafaelzottesso/gitingest.git
cd gitingest
python -m venv .venv && source .venv/bin/activate
pip install -e ".[server]"
```

Omit `[server]` if you only need the CLI / Python package.

## 💡 Command line usage

The `gitingest` command line tool allows you to analyze codebases and create a text dump of their contents.

```bash
# Basic usage (writes to digest.txt by default)
gitingest /path/to/directory

# From URL
gitingest https://github.com/coderamp-labs/gitingest

# or from specific subdirectory
gitingest https://github.com/coderamp-labs/gitingest/tree/main/src/gitingest/utils
```

For private repositories, use the `--token/-t` option.

```bash
# Get your token from https://github.com/settings/personal-access-tokens
gitingest https://github.com/username/private-repo --token github_pat_...

# Or set it as an environment variable
export GITHUB_TOKEN=github_pat_...
gitingest https://github.com/username/private-repo

# Include repository submodules
gitingest https://github.com/username/repo-with-submodules --include-submodules
```

By default, files listed in `.gitignore` are skipped. Use `--include-gitignored` if you
need those files in the digest.

By default, the digest is written to a text file (`digest.txt`) in your current working directory. You can customize the output in two ways:

- Use `--output/-o <filename>` to write to a specific file.
- Use `--output/-o -` to output directly to `STDOUT` (useful for piping to other tools).

See more options and usage details with:

```bash
gitingest --help
```

## 🐍 Python package usage

```python
# Synchronous usage
from gitingest import ingest

summary, tree, content = ingest("path/to/directory")

# or from URL
summary, tree, content = ingest("https://github.com/coderamp-labs/gitingest")

# or from a specific subdirectory
summary, tree, content = ingest("https://github.com/coderamp-labs/gitingest/tree/main/src/gitingest/utils")
```

For private repositories, you can pass a token:

```python
# Using token parameter
summary, tree, content = ingest("https://github.com/username/private-repo", token="github_pat_...")

# Or set it as an environment variable
import os
os.environ["GITHUB_TOKEN"] = "github_pat_..."
summary, tree, content = ingest("https://github.com/username/private-repo")

# Include repository submodules
summary, tree, content = ingest("https://github.com/username/repo-with-submodules", include_submodules=True)
```

By default, this won't write a file but can be enabled with the `output` argument.

```python
# Asynchronous usage
from gitingest import ingest_async
import asyncio

result = asyncio.run(ingest_async("path/to/directory"))
```

### Jupyter notebook usage

```python
from gitingest import ingest_async

# Use await directly in Jupyter
summary, tree, content = await ingest_async("path/to/directory")

```

This is because Jupyter notebooks are asynchronous by default.

## 🐳 Self-host

### Run locally (without Docker)

```bash
pip install -e ".[server]"
cd src && python -m server
```

The app is served at `http://localhost:8000`.

### Notes for public deployments

- Set `ALLOWED_HOSTS` to your own domain; the default list only has the original project's domain and localhost.
- The pages load `posthog.js` (analytics of the original project) and can report to Sentry. Remove or replace the PostHog
  snippet (`src/static/js/posthog.js`) before publishing, and only enable Sentry with your own DSN.
- Anyone who can reach the service can make it clone repositories: use a request limit, an instance cap and billing alerts.
- Tokens typed in the form are used once for cloning and are not stored, but you become responsible for them if others use your instance.


### Using Docker

1. Build the image:

   ``` bash
   docker build -t gitingest .
   ```

2. Run the container:

   ``` bash
   docker run -d --name gitingest -p 8000:8000 gitingest
   ```

The application will be available at `http://localhost:8000`.

If you are hosting it on a domain, you can specify the allowed hostnames via env variable `ALLOWED_HOSTS`.

   ```bash
   # Default: "gitingest.com, *.gitingest.com, localhost, 127.0.0.1".
   ALLOWED_HOSTS="example.com, localhost, 127.0.0.1"
   ```

### Environment Variables

The application can be configured using the following environment variables:

- **ALLOWED_HOSTS**: Comma-separated list of allowed hostnames (default: "gitingest.com, *.gitingest.com, localhost, 127.0.0.1")
- **GITINGEST_METRICS_ENABLED**: Enable Prometheus metrics server (set to any value to enable)
- **GITINGEST_METRICS_HOST**: Host for the metrics server (default: "127.0.0.1")
- **GITINGEST_METRICS_PORT**: Port for the metrics server (default: "9090")
- **GITINGEST_SENTRY_ENABLED**: Enable Sentry error tracking (set to any value to enable)
- **GITINGEST_SENTRY_DSN**: Sentry DSN (required if Sentry is enabled)
- **GITINGEST_SENTRY_TRACES_SAMPLE_RATE**: Sampling rate for performance data (default: "1.0", range: 0.0-1.0)
- **GITINGEST_SENTRY_PROFILE_SESSION_SAMPLE_RATE**: Sampling rate for profile sessions (default: "1.0", range: 0.0-1.0)
- **GITINGEST_SENTRY_PROFILE_LIFECYCLE**: Profile lifecycle mode (default: "trace")
- **GITINGEST_SENTRY_SEND_DEFAULT_PII**: Send default personally identifiable information (default: "true")
- **S3_ALIAS_HOST**: Public URL/CDN for accessing S3 resources (default: "127.0.0.1:9000/gitingest-bucket")
- **S3_DIRECTORY_PREFIX**: Optional prefix for S3 file paths (if set, prefixes all S3 paths with this value)

### Using Docker Compose

The project includes a `compose.yml` file that allows you to easily run the application in both development and production environments.

#### Compose File Structure

The `compose.yml` file uses YAML anchoring with `&app-base` and `<<: *app-base` to define common configuration that is shared between services:

```yaml
# Common base configuration for all services
x-app-base: &app-base
  build:
    context: .
    dockerfile: Dockerfile
  ports:
    - "${APP_WEB_BIND:-8000}:8000"  # Main application port
    - "${GITINGEST_METRICS_HOST:-127.0.0.1}:${GITINGEST_METRICS_PORT:-9090}:9090"  # Metrics port
  # ... other common configurations
```

#### Services

The file defines three services:

1. **app**: Production service configuration
   - Uses the `prod` profile
   - Sets the Sentry environment to "production"
   - Configured for stable operation with `restart: unless-stopped`

2. **app-dev**: Development service configuration
   - Uses the `dev` profile
   - Enables debug mode
   - Mounts the source code for live development
   - Uses hot reloading for faster development

3. **minio**: S3-compatible object storage for development
   - Uses the `dev` profile (only available in development mode)
   - Provides S3-compatible storage for local development
   - Accessible via:
     - API: Port 9000 ([localhost:9000](http://localhost:9000))
     - Web Console: Port 9001 ([localhost:9001](http://localhost:9001))
   - Default admin credentials:
     - Username: `minioadmin`
     - Password: `minioadmin`
   - Configurable via environment variables:
     - `MINIO_ROOT_USER`: Custom admin username (default: minioadmin)
     - `MINIO_ROOT_PASSWORD`: Custom admin password (default: minioadmin)
   - Includes persistent storage via Docker volume
   - Auto-creates a bucket and application-specific credentials:
     - Bucket name: `gitingest-bucket` (configurable via `S3_BUCKET_NAME`)
     - Access key: `gitingest` (configurable via `S3_ACCESS_KEY`)
     - Secret key: `gitingest123` (configurable via `S3_SECRET_KEY`)
   - These credentials are automatically passed to the app-dev service via environment variables:
     - `S3_ENDPOINT`: URL of the MinIO server
     - `S3_ACCESS_KEY`: Access key for the S3 bucket
     - `S3_SECRET_KEY`: Secret key for the S3 bucket
     - `S3_BUCKET_NAME`: Name of the S3 bucket
     - `S3_REGION`: Region for the S3 bucket (default: us-east-1)
     - `S3_ALIAS_HOST`: Public URL/CDN for accessing S3 resources (default: "127.0.0.1:9000/gitingest-bucket")

#### Usage Examples

To run the application in development mode:

```bash
docker compose --profile dev up
```

To run the application in production mode:

```bash
docker compose --profile prod up -d
```

To build and run the application:

```bash
docker compose --profile prod build
docker compose --profile prod up -d
```

## 🤝 Contributing

This fork is mostly for personal and academic use. To contribute to the real project, report bugs unrelated to the changes above,
or use its Discord and browser extensions ([Chrome](https://chromewebstore.google.com/detail/adfjahbijlkjfoicpjkhjicpjpjfaood),
[Firefox](https://addons.mozilla.org/firefox/addon/gitingest)), go to the original repository:
<https://github.com/coderamp-labs/gitingest>. Development setup is in [CONTRIBUTING.md](./CONTRIBUTING.md).

## 🛠️ Stack

- [Tailwind CSS](https://tailwindcss.com) - Frontend
- [FastAPI](https://github.com/fastapi/fastapi) - Backend framework
- [Jinja2](https://jinja.palletsprojects.com) - HTML templating
- [tiktoken](https://github.com/openai/tiktoken) - Token estimation
- [posthog](https://github.com/PostHog/posthog) - Amazing analytics
- [Sentry](https://sentry.io) - Error tracking and performance monitoring

### Looking for a JavaScript/FileSystemNode package?

Check out the NPM alternative 📦 Repomix: <https://github.com/yamadashy/repomix>

## 🙏 Credits and license

Gitingest was created by [Romain Courtois](https://github.com/cyclotruc) and Filip Christiansen and is maintained by the
[coderamp-labs](https://github.com/coderamp-labs) community. This fork keeps the original [MIT License](./LICENSE); keep the
license and copyright notice when reusing the code.
