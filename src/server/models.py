"""Pydantic models for the query form."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from gitingest.utils.compat_func import removesuffix
from server.server_config import MAX_FILE_SIZE_KB

# needed for type checking (pydantic)
if TYPE_CHECKING:
    from server.form_types import IntForm, OptStrForm, StrForm


class PatternType(str, Enum):
    """Enumeration for pattern types used in file filtering."""

    INCLUDE = "include"
    EXCLUDE = "exclude"


class IngestRequest(BaseModel):
    """Request model for the /api/ingest endpoint.

    Attributes
    ----------
    input_text : str
        The Git repository URL or slug to ingest.
    max_file_size : int
        Maximum file size slider position (0-500) for filtering files.
    include_pattern : str
        Glob patterns of files to include (comma/space separated).
    exclude_pattern : str
        Glob patterns of files to exclude (comma/space separated). May be combined with ``include_pattern``.
    pattern_type : PatternType | None
        Deprecated. Together with ``pattern``, kept for backward compatibility.
    pattern : str
        Deprecated. Applied to ``include_pattern`` or ``exclude_pattern`` according to ``pattern_type``.
    token : str | None
        GitHub personal access token (PAT) for accessing private repositories.

    """

    input_text: str = Field(..., description="Git repository URL or slug to ingest")
    max_file_size: int = Field(..., ge=1, le=MAX_FILE_SIZE_KB, description="File size in KB")
    include_pattern: str = Field(default="", description="Glob patterns of files to include")
    exclude_pattern: str = Field(default="", description="Glob patterns of files to exclude")
    pattern_type: Optional[PatternType] = Field(  # noqa: UP007 (pydantic)
        default=None,
        description="Deprecated: use include_pattern/exclude_pattern",
    )
    pattern: str = Field(default="", description="Deprecated: use include_pattern/exclude_pattern")
    token: str | None = Field(default=None, description="GitHub PAT for private repositories")

    @field_validator("input_text")
    @classmethod
    def validate_input_text(cls, v: str) -> str:
        """Validate that ``input_text`` is not empty."""
        if not v.strip():
            err = "input_text cannot be empty"
            raise ValueError(err)
        return removesuffix(v.strip(), ".git")

    @field_validator("include_pattern", "exclude_pattern", "pattern")
    @classmethod
    def validate_pattern(cls, v: str) -> str:
        """Strip whitespace from pattern fields."""
        return v.strip()

    @model_validator(mode="after")
    def merge_legacy_pattern(self) -> IngestRequest:
        """Fold the deprecated ``pattern_type``/``pattern`` pair into the new fields."""
        if self.pattern:
            if self.pattern_type == PatternType.INCLUDE:
                self.include_pattern = f"{self.include_pattern},{self.pattern}" if self.include_pattern else self.pattern
            else:
                self.exclude_pattern = f"{self.exclude_pattern},{self.pattern}" if self.exclude_pattern else self.pattern
            self.pattern = ""
        return self


class IngestSuccessResponse(BaseModel):
    """Success response model for the /api/ingest endpoint.

    Attributes
    ----------
    repo_url : str
        The original repository URL that was processed.
    short_repo_url : str
        Short form of repository URL (user/repo).
    summary : str
        Summary of the ingestion process including token estimates.
    digest_url : str
        URL to download the full digest content (either S3 URL or local download endpoint).
    tree : str
        File tree structure of the repository.
    content : str
        Processed content from the repository files.
    default_max_file_size : int
        The file size slider position used.
    include_pattern : str
        The include pattern used for filtering.
    exclude_pattern : str
        The exclude pattern used for filtering.

    """

    repo_url: str = Field(..., description="Original repository URL")
    short_repo_url: str = Field(..., description="Short repository URL (user/repo)")
    summary: str = Field(..., description="Ingestion summary with token estimates")
    digest_url: str = Field(..., description="URL to download the full digest content")
    tree: str = Field(..., description="File tree structure")
    content: str = Field(..., description="Processed file content")
    default_max_file_size: int = Field(..., description="File size slider position used")
    include_pattern: str = Field(default="", description="Include pattern used")
    exclude_pattern: str = Field(default="", description="Exclude pattern used")


class IngestErrorResponse(BaseModel):
    """Error response model for the /api/ingest endpoint.

    Attributes
    ----------
    error : str
        Error message describing what went wrong.

    """

    error: str = Field(..., description="Error message")


# Union type for API responses
IngestResponse = Union[IngestSuccessResponse, IngestErrorResponse]


class S3Metadata(BaseModel):
    """Model for S3 metadata structure.

    Attributes
    ----------
    summary : str
        Summary of the ingestion process including token estimates.
    tree : str
        File tree structure of the repository.
    content : str
        Processed content from the repository files.

    """

    summary: str = Field(..., description="Ingestion summary with token estimates")
    tree: str = Field(..., description="File tree structure")
    content: str = Field(..., description="Processed file content")


class QueryForm(BaseModel):
    """Form data for the query.

    Attributes
    ----------
    input_text : str
        Text or URL supplied in the form.
    max_file_size : int
        The maximum allowed file size for the input, specified by the user.
    include_pattern : str
        Glob patterns of files to include.
    exclude_pattern : str
        Glob patterns of files to exclude.
    token : str | None
        GitHub personal access token (PAT) for accessing private repositories.

    """

    input_text: str
    max_file_size: int
    include_pattern: str = ""
    exclude_pattern: str = ""
    token: str | None = None

    @classmethod
    def as_form(
        cls,
        input_text: StrForm,
        max_file_size: IntForm,
        include_pattern: OptStrForm,
        exclude_pattern: OptStrForm,
        token: OptStrForm,
    ) -> QueryForm:
        """Create a QueryForm from FastAPI form parameters.

        Parameters
        ----------
        input_text : StrForm
            The input text provided by the user.
        max_file_size : IntForm
            The maximum allowed file size for the input.
        include_pattern : OptStrForm
            Glob patterns of files to include.
        exclude_pattern : OptStrForm
            Glob patterns of files to exclude.
        token : OptStrForm
            GitHub personal access token (PAT) for accessing private repositories.

        Returns
        -------
        QueryForm
            The QueryForm instance.

        """
        return cls(
            input_text=input_text,
            max_file_size=max_file_size,
            include_pattern=include_pattern or "",
            exclude_pattern=exclude_pattern or "",
            token=token,
        )
