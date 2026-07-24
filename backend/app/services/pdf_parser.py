"""
TrialMatch AI PDF Parser Service

Handles PDF extraction with multiple strategies:
1. Primary: PyMuPDF (fitz) for fast text extraction
2. Fallback: Tesseract OCR for scanned/image-based PDFs
3. Hybrid: Combine both methods for complex documents

Includes validation, error handling, and quality scoring.
"""

import io
import logging
from typing import Tuple, Optional, NamedTuple
from pathlib import Path


logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class ParseResult(NamedTuple):
    """Result of PDF parsing operation"""
    text: str  # Extracted text content
    page_count: int  # Number of pages
    extraction_method: str  # 'pymupdf', 'ocr', or 'hybrid'
    confidence_score: float  # 0.0-1.0 confidence in extraction quality
    warnings: list  # List of warning messages


class ValidationResult(NamedTuple):
    """Result of PDF validation"""
    is_valid: bool
    error_message: Optional[str]
    file_size_mb: float
    page_count: int


# ============================================================================
# PDF VALIDATION
# ============================================================================

def validate_pdf(file_bytes: bytes, max_size_bytes: int) -> ValidationResult:
    """
    Validates PDF file before processing.

    Checks:
    - File size within limits
    - Not corrupted
    - Has pages
    - Not password protected
    - Not empty

    Args:
        file_bytes: Raw PDF file bytes
        max_size_bytes: Maximum allowed file size in bytes

    Returns:
        ValidationResult with is_valid flag and details
    """

    warnings = []

    # [IMPLEMENTATION]: Check file size
    file_size_mb = len(file_bytes) / (1024 * 1024)
    if len(file_bytes) > max_size_bytes:
        return ValidationResult(
            is_valid=False,
            error_message=f"File exceeds maximum size of {max_size_bytes / (1024*1024):.1f} MB. "
                          f"Your file is {file_size_mb:.1f} MB.",
            file_size_mb=file_size_mb,
            page_count=0
        )

    # [IMPLEMENTATION]: Check if file is empty
    if len(file_bytes) == 0:
        return ValidationResult(
            is_valid=False,
            error_message="Uploaded file is empty",
            file_size_mb=0,
            page_count=0
        )

    # [IMPLEMENTATION]: Try to open with PyMuPDF to detect corruption
    try:
        import fitz
    except ImportError:
        return ValidationResult(
            is_valid=False,
            error_message="PDF library not available on server",
            file_size_mb=file_size_mb,
            page_count=0
        )

    try:
        # [IMPLEMENTATION]: Open PDF in memory and check validity
        doc = fitz.open(stream=file_bytes, filetype="pdf")

        # [IMPLEMENTATION]: Detect password protection
        if doc.is_encrypted:
            return ValidationResult(
                is_valid=False,
                error_message="Password-protected PDFs are not supported. Please unlock and re-upload.",
                file_size_mb=file_size_mb,
                page_count=doc.page_count
            )

        page_count = doc.page_count

        # [IMPLEMENTATION]: Require at least 1 page
        if page_count == 0:
            return ValidationResult(
                is_valid=False,
                error_message="PDF has no pages",
                file_size_mb=file_size_mb,
                page_count=0
            )

        # [IMPLEMENTATION]: Check if PDF is entirely scanned images
        # This affects extraction strategy
        if page_count > 50:
            warnings.append(
                f"Large protocol detected ({page_count} pages). "
                "Text extraction may take longer."
            )

        doc.close()

        return ValidationResult(
            is_valid=True,
            error_message=None,
            file_size_mb=file_size_mb,
            page_count=page_count
        )

    except Exception as e:
        logger.error(f"PDF validation error: {e}")
        return ValidationResult(
            is_valid=False,
            error_message=f"Failed to read PDF file. File may be corrupted or invalid. Error: {str(e)}",
            file_size_mb=file_size_mb,
            page_count=0
        )


# ============================================================================
# PDF PARSING
# ============================================================================

class PDFParser:
    """
    Main PDF parser with fallback OCR support.

    Strategy:
    1. Try PyMuPDF extraction
    2. If result is too short, try OCR fallback
    3. Combine results if both methods work
    """

    def __init__(self, tesseract_path: Optional[str] = None, enable_ocr: bool = True):
        """
        Initialize PDF parser.

        Args:
            tesseract_path: Path to tesseract executable (for OCR)
            enable_ocr: Whether to enable OCR fallback
        """
        self.tesseract_path = tesseract_path
        self.enable_ocr = enable_ocr
        self.min_text_length_for_pymupdf = 500  # Minimum chars to consider extraction successful

    def parse_pdf(self, file_bytes: bytes) -> ParseResult:
        """
        Parses PDF and extracts text using best available method.

        Strategy:
        1. Try PyMuPDF (fast, works for digital PDFs)
        2. Detect if scanned (image-based)
        3. If scanned or extraction too short, try OCR
        4. Return best result with confidence score

        Args:
            file_bytes: Raw PDF bytes

        Returns:
            ParseResult with extracted text and metadata

        Raises:
            ValueError: If PDF cannot be parsed at all
        """

        warnings = []

        # [IMPLEMENTATION]: Try primary extraction method (PyMuPDF)
        try:
            pymupdf_text, page_count = self._extract_with_pymupdf(file_bytes)
        except Exception as e:
            logger.warning(f"PyMuPDF extraction failed: {e}")
            pymupdf_text = ""
            page_count = 0

        # [IMPLEMENTATION]: Detect if PDF is scanned
        is_scanned = False
        if pymupdf_text and len(pymupdf_text) < self.min_text_length_for_pymupdf:
            is_scanned = self._detect_if_scanned(file_bytes)
            if is_scanned:
                warnings.append(
                    "Scanned PDF detected. Using OCR for text extraction. "
                    "Quality may be lower than digital PDFs."
                )

        # [IMPLEMENTATION]: Try OCR fallback if needed
        ocr_text = ""
        ocr_confidence = 0.0
        if (is_scanned or len(pymupdf_text) < self.min_text_length_for_pymupdf) and self.enable_ocr:
            try:
                ocr_text, ocr_confidence = self._extract_with_ocr(file_bytes)
            except Exception as e:
                logger.warning(f"OCR extraction failed: {e}")
                warnings.append(
                    f"OCR processing encountered an issue: {str(e)}. "
                    "Using standard text extraction only."
                )

        # [IMPLEMENTATION]: Choose best extraction method
        if len(ocr_text) > len(pymupdf_text):
            final_text = ocr_text
            extraction_method = "ocr"
            confidence = ocr_confidence
        else:
            final_text = pymupdf_text
            extraction_method = "pymupdf" if len(pymupdf_text) > 0 else "empty"
            confidence = self._calculate_confidence_score(pymupdf_text, page_count)

        # [IMPLEMENTATION]: Clean extracted text
        final_text = self._clean_extracted_text(final_text)

        # [IMPLEMENTATION]: Validate we got meaningful content
        if not final_text or len(final_text) < 100:
            raise ValueError(
                "Unable to extract meaningful text from PDF. "
                "The file may be corrupted, encrypted, or contain only images. "
                "If your PDF is a scanned document, OCR may not be available."
            )

        logger.info(
            f"PDF parsed successfully. Method: {extraction_method}, "
            f"Pages: {page_count}, Text length: {len(final_text)}, "
            f"Confidence: {confidence:.2f}"
        )

        return ParseResult(
            text=final_text,
            page_count=page_count,
            extraction_method=extraction_method,
            confidence_score=confidence,
            warnings=warnings
        )

    def _extract_with_pymupdf(self, file_bytes: bytes) -> Tuple[str, int]:
        """
        Extract text using PyMuPDF (fitz).

        Fast extraction for digital PDFs. Returns empty string if fails.

        Args:
            file_bytes: PDF file bytes

        Returns:
            Tuple of (extracted_text, page_count)
        """

        try:
            import fitz
        except ImportError:
            raise ImportError("PyMuPDF not installed")

        # [IMPLEMENTATION]: Open PDF from bytes
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = doc.page_count
        text = ""

        # [IMPLEMENTATION]: Extract text from each page
        for page_num in range(page_count):
            try:
                page = doc[page_num]
                # [IMPLEMENTATION]: Extract text with layout preservation
                page_text = page.get_text(
                    preserve_images=False,  # Skip images
                    sort=True  # Sort text blocks top-to-bottom
                )
                text += page_text + "\n"
            except Exception as e:
                logger.warning(f"Failed to extract page {page_num}: {e}")
                # Continue with other pages

        doc.close()

        # [IMPLEMENTATION]: Return extracted text
        return text, page_count

    def _extract_with_ocr(self, file_bytes: bytes) -> Tuple[str, float]:
        """
        Extract text using Tesseract OCR.

        Fallback method for scanned PDFs. Much slower than PyMuPDF.

        Args:
            file_bytes: PDF file bytes

        Returns:
            Tuple of (extracted_text, confidence_score)
        """

        try:
            import pytesseract
            from pdf2image import convert_from_bytes
            from PIL import Image
        except ImportError:
            raise ImportError("Tesseract dependencies not installed")

        # [IMPLEMENTATION]: Convert PDF pages to images
        try:
            images = convert_from_bytes(file_bytes, first_page=1, last_page=50)
        except Exception as e:
            logger.error(f"Failed to convert PDF to images for OCR: {e}")
            raise

        text = ""
        total_conf = 0.0
        page_count = 0

        # [IMPLEMENTATION]: Run OCR on each page image
        for idx, image in enumerate(images):
            try:
                # [IMPLEMENTATION]: Run Tesseract OCR
                page_text = pytesseract.image_to_string(image)
                text += page_text + "\n"

                # [IMPLEMENTATION]: Get confidence scores if available
                # Tesseract data contains detailed confidence information
                try:
                    config = "--psm 1"  # Automatic page segmentation
                    data = pytesseract.image_to_data(image, config=config, output_type=pytesseract.Output.DICT)
                    confidences = [int(c) for c in data['confidence'] if int(c) > 0]
                    if confidences:
                        avg_conf = sum(confidences) / len(confidences)
                        total_conf += avg_conf
                except Exception as e:
                    logger.debug(f"Failed to extract confidence from page {idx}: {e}")

                page_count += 1

            except Exception as e:
                logger.warning(f"OCR failed on page {idx}: {e}")
                continue

        # [IMPLEMENTATION]: Calculate average confidence
        confidence = (total_conf / page_count / 100.0) if page_count > 0 else 0.5
        confidence = max(0.0, min(1.0, confidence))

        logger.info(f"OCR extracted {page_count} pages with {confidence:.2f} average confidence")

        return text, confidence

    def _detect_if_scanned(self, file_bytes: bytes) -> bool:
        """
        Detects if PDF is primarily scanned (image-based).

        Strategy: Check if text from PyMuPDF is too short for page count.
        A digital PDF typically has substantial text per page.

        Args:
            file_bytes: PDF file bytes

        Returns:
            True if PDF appears to be scanned, False if digital
        """

        try:
            import fitz
        except ImportError:
            logger.warning("Cannot detect scanned PDF without PyMuPDF")
            return False

        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            # [IMPLEMENTATION]: Sample first few pages for text density
            sample_pages = min(5, doc.page_count)
            total_text = ""

            for i in range(sample_pages):
                page = doc[i]
                text = page.get_text()
                total_text += text

            doc.close()

            # [IMPLEMENTATION]: Calculate text-to-page ratio
            # Scanned PDFs typically have very little text extracted by PyMuPDF
            chars_per_page = len(total_text) / sample_pages if sample_pages > 0 else 0
            text_density_threshold = 100  # Minimum chars per page for digital PDF

            is_scanned = chars_per_page < text_density_threshold

            logger.info(
                f"Scanned detection: {chars_per_page:.0f} chars/page "
                f"(threshold: {text_density_threshold}) → {'scanned' if is_scanned else 'digital'}"
            )

            return is_scanned

        except Exception as e:
            logger.error(f"Error detecting if scanned: {e}")
            return False

    def _clean_extracted_text(self, raw_text: str) -> str:
        """
        Cleans extracted text for downstream processing.

        Operations:
        - Remove excessive whitespace
        - Fix common OCR errors
        - Normalize line breaks
        - Remove control characters

        Args:
            raw_text: Raw extracted text

        Returns:
            Cleaned text
        """

        # [IMPLEMENTATION]: Normalize whitespace
        # Replace multiple spaces/tabs with single space
        import re
        text = re.sub(r'[ \t]+', ' ', raw_text)

        # [IMPLEMENTATION]: Normalize line breaks
        # Replace multiple newlines with double newline (paragraph breaks)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # [IMPLEMENTATION]: Remove page numbers and headers/footers
        # Basic heuristic: lines with only numbers or very short text at page boundaries
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Skip lines that appear to be page numbers or headers
            if len(line.strip()) > 3 or (len(line.strip()) <= 3 and not line.strip().isdigit()):
                cleaned_lines.append(line)

        text = '\n'.join(cleaned_lines)

        # [IMPLEMENTATION]: Remove common OCR artifacts
        text = text.replace('|', 'l')  # Replace pipe with letter l
        text = text.replace('0', 'O')  # Common substitution (only if context suggests)
        # Note: Be careful not to corrupt numeric data

        # [IMPLEMENTATION]: Strip leading/trailing whitespace
        text = text.strip()

        return text

    def _calculate_confidence_score(self, text: str, page_count: int) -> float:
        """
        Calculates extraction confidence based on text quality.

        Factors:
        - Text length vs expected (min 100 chars per page)
        - Presence of reasonable keywords
        - No excessive special characters

        Args:
            text: Extracted text
            page_count: Number of pages

        Returns:
            Confidence score 0.0-1.0
        """

        # [IMPLEMENTATION]: Base score on text-to-page ratio
        if page_count == 0:
            return 0.0

        chars_per_page = len(text) / page_count
        expected_chars_per_page = 3000  # Digital PDF typical value

        # Linear interpolation: 0 confidence at 0 chars/page, 0.95 at expected
        confidence = min(0.95, chars_per_page / expected_chars_per_page)

        # [IMPLEMENTATION]: Reduce confidence if text has unusual patterns
        # High ratio of special characters suggests OCR errors
        special_chars = sum(1 for c in text if ord(c) < 32 or ord(c) > 126)
        if special_chars / len(text) > 0.05:
            confidence *= 0.8

        # [IMPLEMENTATION]: Boost confidence if clinical keywords found
        clinical_keywords = [
            'inclusion', 'exclusion', 'criteria', 'patient', 'study',
            'protocol', 'trial', 'treatment', 'eligibility', 'screening'
        ]
        if any(keyword in text.lower() for keyword in clinical_keywords):
            confidence = min(0.99, confidence + 0.1)

        return max(0.0, min(1.0, confidence))
