"""
TrialMatch AI Configuration Module

Centralized settings for the FastAPI application. All configuration is loaded
from environment variables with sensible defaults. Validation occurs on startup
to catch configuration errors early.
"""

import os
import logging
from typing import Optional
from enum import Enum


logger = logging.getLogger(__name__)


class LogLevel(str, Enum):
    """Available logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AppConfig:
    """
    Application configuration class. Loads all settings from environment variables
    with fallback defaults. Validates critical settings on initialization.

    Environment variables:
    - ANTHROPIC_API_KEY: Required. API key for Anthropic Claude API
    - AWS_BUCKET_NAME: S3 bucket for temporary PDF storage
    - MAX_PDF_SIZE_MB: Max allowed PDF file size (default: 50)
    - CLAUDE_MODEL: Claude model identifier (default: "claude-3-5-sonnet-20241022")
    - MAX_TOKENS_EXTRACTION: Max tokens for extraction requests (default: 4000)
    - MAX_TOKENS_SCREENING: Max tokens for screening requests (default: 3000)
    - ALLOWED_ORIGINS: CORS origins, comma-separated (default: "http://localhost:3000,http://localhost:5173")
    - PDF_TEMP_TTL_HOURS: Temp file retention hours (default: 24)
    - LOG_LEVEL: Logging level (default: "INFO")
    - RAILWAY_ENV: Detection for Railway deployment (auto-set)
    """

    def __init__(self):
        """Initialize and validate all configuration settings"""

        # ========== ANTHROPIC API SETTINGS ==========
        self.ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
        if not self.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required. "
                "Set it before starting the application."
            )

        # ========== PDF & FILE STORAGE SETTINGS ==========
        self.AWS_BUCKET_NAME = os.getenv(
            "AWS_BUCKET_NAME",
            "trialmatch-pdfs-temp"
        )

        self.MAX_PDF_SIZE_MB = int(
            os.getenv("MAX_PDF_SIZE_MB", "50")
        )
        if self.MAX_PDF_SIZE_MB < 1 or self.MAX_PDF_SIZE_MB > 500:
            raise ValueError(
                f"MAX_PDF_SIZE_MB must be between 1 and 500, got {self.MAX_PDF_SIZE_MB}"
            )

        self.PDF_TEMP_TTL_HOURS = int(
            os.getenv("PDF_TEMP_TTL_HOURS", "24")
        )
        if self.PDF_TEMP_TTL_HOURS < 1:
            raise ValueError("PDF_TEMP_TTL_HOURS must be at least 1")

        # ========== LLM SETTINGS ==========
        self.CLAUDE_MODEL = os.getenv(
            "CLAUDE_MODEL",
            "claude-3-5-sonnet-20241022"
        )

        self.MAX_TOKENS_EXTRACTION = int(
            os.getenv("MAX_TOKENS_EXTRACTION", "4000")
        )
        if self.MAX_TOKENS_EXTRACTION < 1000 or self.MAX_TOKENS_EXTRACTION > 10000:
            raise ValueError(
                f"MAX_TOKENS_EXTRACTION must be between 1000 and 10000, got {self.MAX_TOKENS_EXTRACTION}"
            )

        self.MAX_TOKENS_SCREENING = int(
            os.getenv("MAX_TOKENS_SCREENING", "3000")
        )
        if self.MAX_TOKENS_SCREENING < 1000 or self.MAX_TOKENS_SCREENING > 10000:
            raise ValueError(
                f"MAX_TOKENS_SCREENING must be between 1000 and 10000, got {self.MAX_TOKENS_SCREENING}"
            )

        # ========== API & CORS SETTINGS ==========
        self.ALLOWED_ORIGINS = [
            origin.strip()
            for origin in os.getenv(
                "ALLOWED_ORIGINS",
                "http://localhost:3000,http://localhost:5173"
            ).split(",")
        ]

        # ========== LOGGING SETTINGS ==========
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        try:
            self.LOG_LEVEL = LogLevel[log_level_str]
        except KeyError:
            raise ValueError(
                f"Invalid LOG_LEVEL '{log_level_str}'. "
                f"Must be one of: {', '.join([e.value for e in LogLevel])}"
            )

        # ========== ENVIRONMENT DETECTION ==========
        self.RAILWAY_ENV = os.getenv("RAILWAY_ENV", "local")
        self.IS_PRODUCTION = self.RAILWAY_ENV == "production"

        # ========== FEATURE FLAGS & DEFAULTS ==========
        self.ENABLE_CRITERIA_CACHING = os.getenv("ENABLE_CRITERIA_CACHING", "true").lower() == "true"
        self.CACHE_EXPIRY_MINUTES = int(
            os.getenv("CACHE_EXPIRY_MINUTES", "1440")  # 24 hours
        )
        self.MAX_RETRY_ATTEMPTS = int(
            os.getenv("MAX_RETRY_ATTEMPTS", "3")
        )
        self.INITIAL_RETRY_DELAY_SECONDS = int(
            os.getenv("INITIAL_RETRY_DELAY_SECONDS", "1")
        )
        self.ENABLE_OCR_FALLBACK = os.getenv("ENABLE_OCR_FALLBACK", "true").lower() == "true"

        # ========== TESSERACT SETTINGS ==========
        self.TESSERACT_PATH = os.getenv("TESSERACT_PATH", "/usr/bin/tesseract")

        logger.info(
            f"AppConfig initialized. Environment: {self.RAILWAY_ENV}. "
            f"Claude model: {self.CLAUDE_MODEL}"
        )

    def get_log_level(self) -> int:
        """Convert LogLevel enum to Python logging level"""
        return getattr(logging, self.LOG_LEVEL.value)

    def get_max_pdf_size_bytes(self) -> int:
        """Convert MAX_PDF_SIZE_MB to bytes"""
        return self.MAX_PDF_SIZE_MB * 1024 * 1024

    def validate_pdf_file_size(self, file_size_bytes: int) -> bool:
        """Check if file size is within limits"""
        return file_size_bytes <= self.get_max_pdf_size_bytes()

    def __repr__(self) -> str:
        """Safe representation that doesn't expose API key"""
        return (
            f"AppConfig(model={self.CLAUDE_MODEL}, "
            f"max_pdf_mb={self.MAX_PDF_SIZE_MB}, "
            f"environment={self.RAILWAY_ENV})"
        )


# [IMPLEMENTATION]: Create singleton instance when module is imported
# This instance is reused throughout the application
try:
    config = AppConfig()
except ValueError as e:
    logger.critical(f"Configuration error: {e}")
    raise
