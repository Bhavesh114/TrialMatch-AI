/**
 * TrialMatch AI API Client Utilities
 *
 * Handles all backend API communication with:
 * - Multipart file uploads (PDF)
 * - JSON POST requests (screening, reporting)
 * - Error handling and retry logic
 * - Type-safe data transformations
 */

import axios from 'axios';

// [IMPLEMENTATION]: Get API base URL from environment
// In development: http://localhost:8000
// In production: https://api.trialmatch.ai (or Railway URL)
const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// ============================================================================
// API ERROR HANDLING
// ============================================================================

class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * Handle API response errors
 *
 * Converts HTTP errors and API responses into ApiError instances
 * with user-friendly messages
 */
const handleApiError = (error) => {
  // [IMPLEMENTATION]: Check if error has response (HTTP error)
  if (error.response) {
    const { status, data } = error.response;

    // [IMPLEMENTATION]: Extract error message from various formats
    let message = data.detail || data.message || error.message;
    if (Array.isArray(data.detail)) {
      message = data.detail[0].msg || message;
    }

    // [IMPLEMENTATION]: Map common status codes to user-friendly messages
    if (status === 400) {
      message = `Invalid request: ${message}`;
    } else if (status === 413) {
      message = 'File is too large. Maximum size is 50 MB.';
    } else if (status === 422) {
      message = `Validation error: ${message}`;
    } else if (status === 429) {
      message = 'Too many requests. Please wait a moment and try again.';
    } else if (status === 500) {
      message = 'Server error. Please try again later.';
    }

    return new ApiError(message, status, data);
  }

  // [IMPLEMENTATION]: Check if error is network/timeout
  if (error.code === 'ECONNABORTED') {
    return new ApiError(
      'Request timeout. Please check your connection and try again.',
      'TIMEOUT',
      null
    );
  }

  if (error.message === 'Network Error') {
    return new ApiError(
      'Network error. Please check your connection.',
      'NETWORK',
      null
    );
  }

  // [IMPLEMENTATION]: Unknown error
  return new ApiError(
    error.message || 'An unknown error occurred',
    'UNKNOWN',
    null
  );
};

// ============================================================================
// RETRY LOGIC UTILITY
// ============================================================================

/**
 * Retry a failed API call with exponential backoff
 *
 * Strategy:
 * - Retry on network errors, timeouts, and 5xx errors
 * - Don't retry on 4xx client errors
 * - Use exponential backoff: 1s, 2s, 4s
 *
 * @param {Function} fn - Async function to retry
 * @param {number} maxAttempts - Maximum number of attempts
 * @param {number} initialDelay - Initial delay in milliseconds
 * @returns {Promise} Result of successful call
 */
export const withRetry = async (fn, maxAttempts = 3, initialDelay = 1000) => {
  let lastError;

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;

      // [IMPLEMENTATION]: Don't retry on client errors
      if (error.status && error.status >= 400 && error.status < 500) {
        throw error;
      }

      // [IMPLEMENTATION]: Don't retry on last attempt
      if (attempt === maxAttempts) {
        break;
      }

      // [IMPLEMENTATION]: Calculate exponential backoff delay
      const delay = initialDelay * Math.pow(2, attempt - 1);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }

  throw lastError;
};

// ============================================================================
// API ENDPOINTS
// ============================================================================

/**
 * Extract eligibility criteria from a protocol PDF
 *
 * @param {File} pdfFile - PDF file from input
 * @param {string} trialName - Optional trial name
 * @returns {Promise<CriteriaExtractionResult>}
 */
export const extractCriteria = async (pdfFile, trialName = null) => {
  try {
    // [IMPLEMENTATION]: Build multipart form data
    const formData = new FormData();
    formData.append('file', pdfFile);
    if (trialName) {
      formData.append('trial_name', trialName);
    }

    // [IMPLEMENTATION]: POST with multipart content-type
    // axios automatically sets Content-Type: multipart/form-data
    const response = await withRetry(
      () =>
        axios.post(`${BASE_URL}/extract-criteria`, formData, {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 120000, // 2 minute timeout for large PDFs
        }),
      3,
      2000
    );

    // [IMPLEMENTATION]: Validate response structure
    if (!response.data || !response.data.criteria) {
      throw new ApiError(
        'Invalid response format from server',
        'INVALID_RESPONSE',
        response.data
      );
    }

    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Screen a patient against trial criteria
 *
 * @param {PatientSummary} patientSummary - Patient data
 * @param {CriterionModel[]} criteria - Criteria to evaluate
 * @param {string} protocolId - Optional protocol identifier
 * @returns {Promise<ScreeningResult>}
 */
export const screenPatient = async (patientSummary, criteria, protocolId = null) => {
  try {
    // [IMPLEMENTATION]: Build request payload
    const payload = {
      patient_summary: patientSummary,
      criteria: criteria,
      protocol_id: protocolId,
    };

    // [IMPLEMENTATION]: POST JSON request
    const response = await withRetry(
      () =>
        axios.post(`${BASE_URL}/screen-patient`, payload, {
          headers: {
            'Content-Type': 'application/json',
          },
          timeout: 90000, // 90 second timeout
        }),
      3,
      2000
    );

    // [IMPLEMENTATION]: Validate response
    if (!response.data || !response.data.overall_status) {
      throw new ApiError(
        'Invalid screening response from server',
        'INVALID_RESPONSE',
        response.data
      );
    }

    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Validate patient data without screening
 *
 * Useful for catching errors early before expensive screening call
 *
 * @param {PatientSummary} patientSummary - Patient data to validate
 * @returns {Promise<{valid: boolean, errors: string[]}>}
 */
export const validatePatient = async (patientSummary) => {
  try {
    const response = await axios.post(
      `${BASE_URL}/validate-patient`,
      patientSummary,
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 10000,
      }
    );

    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Export screening results as PDF
 *
 * @param {ScreeningResult} screeningResult - Screening results
 * @param {PatientSummary} patientSummary - Patient data
 * @param {Object} trialInfo - Trial metadata
 * @returns {Promise<Blob>} PDF file blob
 */
export const exportReport = async (screeningResult, patientSummary, trialInfo) => {
  try {
    // [IMPLEMENTATION]: Build request payload
    const payload = {
      screening_result: screeningResult,
      patient_summary: patientSummary,
      trial_info: trialInfo,
    };

    // [IMPLEMENTATION]: POST and get blob response
    const response = await withRetry(
      () =>
        axios.post(`${BASE_URL}/export-report`, payload, {
          headers: { 'Content-Type': 'application/json' },
          responseType: 'blob', // Important: expect binary PDF data
          timeout: 60000, // 60 second timeout
        }),
      3,
      1000
    );

    // [IMPLEMENTATION]: Return blob for download
    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Preview report data without generating PDF
 *
 * Returns JSON preview of report content
 *
 * @param {ScreeningResult} screeningResult
 * @param {PatientSummary} patientSummary
 * @param {Object} trialInfo
 * @returns {Promise<Object>} Report preview data
 */
export const previewReport = async (screeningResult, patientSummary, trialInfo) => {
  try {
    const payload = {
      screening_result: screeningResult,
      patient_summary: patientSummary,
      trial_info: trialInfo,
    };

    const response = await axios.post(
      `${BASE_URL}/preview-report`,
      payload,
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 30000,
      }
    );

    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Health check endpoint
 *
 * Used to verify backend connectivity
 *
 * @returns {Promise<Object>} Health status
 */
export const healthCheck = async () => {
  try {
    const response = await axios.get(`${BASE_URL}/health`, {
      timeout: 5000,
    });

    return response.data;
  } catch (error) {
    throw handleApiError(error);
  }
};

/**
 * Download PDF blob to user's device
 *
 * Helper function to trigger browser download of PDF
 *
 * @param {Blob} blob - PDF blob from exportReport
 * @param {string} filename - Filename for download
 */
export const downloadPDF = (blob, filename = 'TrialMatch_Report.pdf') => {
  // [IMPLEMENTATION]: Create blob URL
  const url = window.URL.createObjectURL(blob);

  // [IMPLEMENTATION]: Create temporary link and trigger download
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();

  // [IMPLEMENTATION]: Cleanup
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

export { ApiError, handleApiError };
