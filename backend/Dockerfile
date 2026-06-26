# TrialMatch AI Backend - Multi-stage Docker Build

# ============================================================================
# STAGE 1: Builder - Install system dependencies and Python packages
# ============================================================================

FROM python:3.11-slim as builder

# [IMPLEMENTATION]: Update package manager and install system dependencies
# Tesseract OCR: for scanned PDF text extraction
# Poppler: for PDF to image conversion (required by pdf2image)
# Other build tools: for compiling Python packages

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpoppler-cpp-dev \
    poppler-utils \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# [IMPLEMENTATION]: Create virtual environment for Python packages
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# [IMPLEMENTATION]: Copy requirements and install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ============================================================================
# STAGE 2: Runtime - Minimal image with only production dependencies
# ============================================================================

FROM python:3.11-slim

# [IMPLEMENTATION]: Install only runtime dependencies (not build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libpoppler-cpp0 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# [IMPLEMENTATION]: Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# [IMPLEMENTATION]: Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# [IMPLEMENTATION]: Create non-root user for security
RUN useradd -m -u 1000 appuser

# [IMPLEMENTATION]: Set working directory
WORKDIR /app

# [IMPLEMENTATION]: Copy application code
COPY backend/ /app/

# [IMPLEMENTATION]: Change ownership to non-root user
RUN chown -R appuser:appuser /app

# [IMPLEMENTATION]: Switch to non-root user
USER appuser

# [IMPLEMENTATION]: Expose port (Railway typically uses 8000)
EXPOSE 8000

# [IMPLEMENTATION]: Health check (optional but recommended)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# [IMPLEMENTATION]: Run FastAPI application with uvicorn
# Railway injects PORT environment variable automatically
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
