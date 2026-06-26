"""
TrialMatch AI Extract Router

FastAPI endpoint for Protocol PDF upload and criteria extraction.

POST /api/extract-criteria
- Accepts: multipart/form-data with PDF file
- Returns: CriteriaExtractionResult JSON
- Handles: file validation, PDF parsing, criteria extraction
"""

import logging
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import config
from ..models.criteria import CriteriaExtractionResult
from ..services.pdf_parser import PDFParser, validate_pdf
from ..services.criteria_extractor import CriteriaExtractor


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["extraction"])

# [IMPLEMENTATION]: Initialize services
pdf_parser = PDFParser(
    tesseract_path=config.TESSERACT_PATH,
    enable_ocr=config.ENABLE_OCR_FALLBACK
)
criteria_extractor = CriteriaExtractor()


# ============================================================================
# EXTRACTION ENDPOINT
# ============================================================================

@router.post(
    "/extract-criteria",
    response_model=CriteriaExtractionResult,
    status_code=status.HTTP_200_OK,
    summary="Extract Trial Criteria from PDF",
    description="Upload a clinical trial protocol PDF and extract structured eligibility criteria"
)
async def extract_criteria(
    file: UploadFile = File(..., description="PDF file of clinical trial protocol"),
    trial_name: Optional[str] = Form(None, description="Optional trial name for reference")
) -> CriteriaExtractionResult:
    """
    Extract eligibility criteria from a clinical trial protocol PDF.

    Workflow:
    1. Validate PDF file (size, format, integrity)
    2. Parse PDF to extract text (PyMuPDF primary, OCR fallback)
    3. Send protocol text to Claude for criteria extraction
    4. Parse and validate extracted criteria
    5. Return structured criteria result

    Args:
        file: PDF file upload
        trial_name: Optional trial name

    Returns:
        CriteriaExtractionResult with extracted criteria

    Raises:
        400: Invalid file format or validation error
        413: File too large
        422: Validation error
        500: Extraction or parsing error
    """

    logger.info(f"Received extract-criteria request. File: {file.filename}")

    # [IMPLEMENTATION]: Check file type
    if not file.filename.lower().endswith('.pdf'):
        logger.warning(f"Invalid file type: {file.filename}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF. Please upload a .pdf file."
        )

    # [IMPLEMENTATION]: Read file bytes
    try:
        file_bytes = await file.read()
    except Exception as e:
        logger.error(f"Failed to read uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to read file: {str(e)}"
        )

    # [IMPLEMENTATION]: Validate PDF
    validation_result = validate_pdf(file_bytes, config.get_max_pdf_size_bytes())
    if not validation_result.is_valid:
        logger.warning(f"PDF validation failed: {validation_result.error_message}")
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            if "exceeds maximum size" in validation_result.error_message
            else status.HTTP_400_BAD_REQUEST,
            detail=validation_result.error_message
        )

    logger.info(
        f"PDF validated. Pages: {validation_result.page_count}, "
        f"Size: {validation_result.file_size_mb:.2f} MB"
    )

    # [IMPLEMENTATION]: Parse PDF to extract text
    try:
        parse_result = pdf_parser.parse_pdf(file_bytes)
        logger.info(
            f"PDF parsed. Method: {parse_result.extraction_method}, "
            f"Text length: {len(parse_result.text)}, "
            f"Confidence: {parse_result.confidence_score:.2f}"
        )
    except ValueError as e:
        logger.error(f"PDF parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not extract text from PDF: {str(e)}"
        )

    # [IMPLEMENTATION]: Extract criteria using Claude
    try:
        extraction_result = criteria_extractor.extract_criteria(
            protocol_text=parse_result.text,
            protocol_id=None,  # Will be generated from hash
            trial_name=trial_name
        )

        # [IMPLEMENTATION]: Add PDF parsing info to result
        extraction_result.extraction_method = parse_result.extraction_method
        extraction_result.page_count = parse_result.page_count

        # [IMPLEMENTATION]: Add OCR warning if detected
        if "OCR" in parse_result.extraction_method.upper():
            from ..models.criteria import ExtractionWarning
            extraction_result.warnings.append(
                ExtractionWarning(
                    severity="info",
                    code="OCR_USED",
                    message="Scanned PDF detected. Text extraction quality may be lower."
                )
            )

        logger.info(
            f"Extraction successful. Criteria: {len(extraction_result.criteria)}, "
            f"Confidence: {extraction_result.extraction_confidence:.2f}"
        )

        return extraction_result

    except ValueError as e:
        logger.error(f"Criteria extraction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to extract criteria: {str(e)}"
        )
    except Exception as e:
        logger.exception(f"Unexpected error during extraction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during criteria extraction. Please try again."
        )


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for extraction service.

    Returns:
        {"status": "healthy"}
    """
    return {"status": "healthy", "service": "extraction"}
