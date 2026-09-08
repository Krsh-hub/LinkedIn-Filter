"""FastAPI web application for LinkedIn Network Analyzer.

Provides a REST API for uploading LinkedIn Connections CSV files,
running the analysis pipeline, and downloading generated reports.

Endpoints:
    POST /analyze       — Upload CSV, run pipeline, get KPI summary + download token
    GET  /download/{id} — Download the generated ZIP archive
    GET  /              — Serve the single-page frontend
"""

from __future__ import annotations

import base64
import hashlib
import logging
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from src.csv_loader import HEADER_CANDIDATE_KEYWORDS
from web.pipeline import run_pipeline

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
DOWNLOAD_TOKEN_TTL_SECONDS = 300  # 5 minutes
ALLOWED_EXTENSIONS = {".csv"}

logger = logging.getLogger("linkedin_analyzer")

# ---------------------------------------------------------------------------
# In-memory download cache
# ---------------------------------------------------------------------------
# Keyed by token string → {"zip_bytes": bytes, "created_at": float}
_download_cache: Dict[str, Dict[str, Any]] = {}


def _prune_expired_tokens() -> None:
    """Remove expired download tokens from cache."""
    now = time.time()
    expired = [
        token for token, entry in _download_cache.items()
        if now - entry["created_at"] > DOWNLOAD_TOKEN_TTL_SECONDS
    ]
    for token in expired:
        del _download_cache[token]


# ---------------------------------------------------------------------------
# App initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="LinkedIn Network Analyzer",
    description="Upload your LinkedIn Connections.csv to analyze and classify your professional network.",
    version="1.0.0",
)

# CORS — permissive for local dev; tighten for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_csv_headers(content: bytes) -> None:
    """Check that the uploaded file looks like a LinkedIn connections export.

    Decodes the first ~4 KB and checks for at least 2 of the known LinkedIn
    header keywords. Raises HTTPException(422) if not matched.
    """
    # Decode first chunk — try utf-8-sig first, then latin1 as fallback
    head_bytes = content[:4096]
    text = ""
    for enc in ("utf-8-sig", "utf-8", "latin1"):
        try:
            text = head_bytes.decode(enc).lower()
            break
        except (UnicodeDecodeError, ValueError):
            continue

    if not text:
        raise HTTPException(
            status_code=422,
            detail="Could not decode the file. Please ensure it is a valid CSV file.",
        )

    matches = sum(1 for kw in HEADER_CANDIDATE_KEYWORDS if kw in text)
    if matches < 2:
        raise HTTPException(
            status_code=422,
            detail=(
                "This file does not appear to be a LinkedIn Connections export. "
                "Expected headers like 'First Name', 'Company', 'Position', 'Email Address', etc. "
                "Please export your connections from LinkedIn: "
                "Settings & Privacy → Data Privacy → Get a copy of your data → Connections."
            ),
        )


def _validate_upload(file: UploadFile, content: bytes) -> None:
    """Run all upload validations."""
    # 1. Check extension
    filename = file.filename or ""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{suffix}'. Please upload a .csv file.",
        )

    # 2. Check content type (lenient — browsers vary)
    content_type = (file.content_type or "").lower()
    csv_types = {"text/csv", "application/vnd.ms-excel", "application/csv", "text/plain"}
    if content_type and content_type not in csv_types and "csv" not in content_type:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid content type '{content_type}'. Please upload a CSV file.",
        )

    # 3. Check file size
    if len(content) > MAX_FILE_SIZE_BYTES:
        size_mb = len(content) / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum allowed size is 10 MB.",
        )

    # 4. Check empty file
    if len(content) == 0:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # 5. Validate LinkedIn headers
    _validate_csv_headers(content)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(..., description="LinkedIn Connections CSV file"),
    role: Optional[str] = Form(None, description="Filter by role: founder, cto, ceo, director, entrepreneur, c-suite, senior"),
    company: Optional[str] = Form(None, description="Exact company name filter (case-insensitive)"),
    company_contains: Optional[str] = Form(None, description="Company name substring filter"),
    search: Optional[str] = Form(None, description="Search across name, company, and position"),
    location: Optional[str] = Form(None, description="Location filter"),
) -> JSONResponse:
    """Upload a LinkedIn Connections CSV and receive analysis results.

    Returns a JSON response containing KPI summary metrics and a download
    token for retrieving the generated ZIP archive of reports.
    """
    # Read file content
    content = await file.read()

    # Validate
    _validate_upload(file, content)

    # Validate role if provided
    valid_roles = {"founder", "cto", "ceo", "director", "entrepreneur", "c-suite", "senior"}
    if role and role.strip().lower() not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role filter '{role}'. Valid options: {', '.join(sorted(valid_roles))}",
        )

    # Run pipeline
    try:
        zip_bytes, summary = run_pipeline(
            csv_bytes=content,
            filename=file.filename or "Connections.csv",
            role_filter=role.strip().lower() if role else None,
            company_filter=company.strip() if company else None,
            company_contains=company_contains.strip() if company_contains else None,
            search_query=search.strip() if search else None,
            location_filter=location.strip() if location else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during pipeline processing")
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing your file. Please try again.",
        )

    # Prune expired tokens before adding new one
    _prune_expired_tokens()

    # Store ZIP in cache with a unique download token
    token = uuid.uuid4().hex[:16]
    _download_cache[token] = {
        "zip_bytes": zip_bytes,
        "created_at": time.time(),
        "filename": "linkedin_network_analysis.zip",
    }

    # Also persist to /tmp/{token}.zip as fallback for serverless environments
    try:
        tmp_cache_file = Path(tempfile.gettempdir()) / f"lna_{token}.zip"
        tmp_cache_file.write_bytes(zip_bytes)
    except Exception:
        pass

    return JSONResponse(
        content={
            "status": "success",
            "summary": summary,
            "download_token": token,
            "download_url": f"/download/{token}",
            "zip_base64": base64.b64encode(zip_bytes).decode("ascii"),
            "token_expires_in_seconds": DOWNLOAD_TOKEN_TTL_SECONDS,
        }
    )


@app.get("/download/{token}")
async def download(token: str) -> Response:
    """Download the generated ZIP archive using a one-time download token."""
    _prune_expired_tokens()

    entry = _download_cache.get(token)
    zip_bytes = None
    filename = "linkedin_network_analysis.zip"

    if entry:
        zip_bytes = entry["zip_bytes"]
        filename = entry.get("filename", filename)
    else:
        # Fallback check in system temp dir
        tmp_cache_file = Path(tempfile.gettempdir()) / f"lna_{token}.zip"
        if tmp_cache_file.exists():
            try:
                zip_bytes = tmp_cache_file.read_bytes()
            except Exception:
                pass

    if not zip_bytes:
        raise HTTPException(
            status_code=404,
            detail="Download link expired or not found. Please re-upload your CSV.",
        )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(zip_bytes)),
        },
    )


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> Dict[str, str]:
    """Simple health check endpoint for deployment monitoring."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Static file serving — must be mounted LAST
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.exists():
    # Serve index.html at root
    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def serve_index() -> HTMLResponse:
        index_path = _static_dir / "index.html"
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")
