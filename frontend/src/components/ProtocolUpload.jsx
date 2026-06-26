/**
 * TrialMatch AI Protocol Upload Component
 *
 * Drag-and-drop PDF upload area with validation and progress indication
 *
 * Features:
 * - Drag-and-drop file input
 * - File type validation (PDF only)
 * - File size validation
 * - Upload progress indicator
 * - PHI warning reminder
 * - Error display with retry
 */

import React, { useState, useRef } from 'react';
import { useScreening } from '../context/ScreeningContext';
import { extractCriteria } from '../utils/api';

const ProtocolUpload = ({ onUploadSuccess }) => {
  // [IMPLEMENTATION]: Local state for upload UI
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [selectedFile, setSelectedFile] = useState(null);
  const { setProtocolFile, setLoading, setError, isLoading } = useScreening();
  const fileInputRef = useRef(null);

  // [IMPLEMENTATION]: Handle file selection from input or drag-drop
  const handleFileSelect = async (file) => {
    // Validate file type
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please upload a PDF file');
      return;
    }

    // Validate file size (50 MB max)
    const maxSize = 50 * 1024 * 1024;
    if (file.size > maxSize) {
      setError(
        `File is too large (${(file.size / 1024 / 1024).toFixed(1)} MB). ` +
        'Maximum size is 50 MB.'
      );
      return;
    }

    setSelectedFile(file);
    setProtocolFile(file);

    // [IMPLEMENTATION]: Start extraction process
    await handleExtraction(file);
  };

  // [IMPLEMENTATION]: Send file to backend for extraction
  const handleExtraction = async (file) => {
    setLoading(true);
    setUploadProgress(0);
    setError(null);

    try {
      // [IMPLEMENTATION]: Simulate progress (API doesn't return progress events easily)
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 90) return prev;
          return prev + Math.random() * 30;
        });
      }, 500);

      // [IMPLEMENTATION]: Call extraction API
      const result = await extractCriteria(file, null);

      clearInterval(progressInterval);
      setUploadProgress(100);

      // [IMPLEMENTATION]: Notify parent component of success
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (error) {
      setError(error.message || 'Failed to extract criteria from PDF');
    } finally {
      setLoading(false);
      setTimeout(() => setUploadProgress(0), 1000);
    }
  };

  // [IMPLEMENTATION]: Handle drag-and-drop events
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6">
      {/* PHI Warning Banner */}
      <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-900">
          <span className="font-semibold">⚠️ Important:</span> This tool processes
          de-identified data only. Do not enter patient names, dates of birth, MRN,
          or other personally identifiable information.
        </p>
      </div>

      {/* Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-8 transition-colors ${
          isDragging
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 bg-gray-50 hover:border-blue-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        {/* Upload Icon & Text */}
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            stroke="currentColor"
            fill="none"
            viewBox="0 0 48 48"
          >
            <path
              d="M28 8H12a4 4 0 00-4 4v20a4 4 0 004 4h24a4 4 0 004-4V20m-8-12l-4-4m0 0l-4 4m4-4v12"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>

          <h3 className="mt-2 text-sm font-medium text-gray-900">
            Upload Trial Protocol
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Drag and drop your PDF here, or click to select
          </p>

          {/* Hidden File Input */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf"
            onChange={(e) => {
              if (e.target.files[0]) {
                handleFileSelect(e.target.files[0]);
              }
            }}
            className="hidden"
          />

          {/* Select Button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={isLoading}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Processing...' : 'Select PDF'}
          </button>
        </div>

        {/* Progress Bar */}
        {uploadProgress > 0 && uploadProgress < 100 && (
          <div className="mt-4">
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div
                className="bg-blue-600 h-2 rounded-full transition-all"
                style={{ width: `${uploadProgress}%` }}
              />
            </div>
            <p className="text-xs text-gray-500 mt-2">
              Extracting criteria... {Math.round(uploadProgress)}%
            </p>
          </div>
        )}
      </div>

      {/* Selected File Info */}
      {selectedFile && (
        <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
          <p className="text-sm text-green-800">
            <span className="font-semibold">✓ Selected:</span> {selectedFile.name}
            ({(selectedFile.size / 1024 / 1024).toFixed(1)} MB)
          </p>
        </div>
      )}

      {/* File Size Help Text */}
      <p className="mt-4 text-xs text-gray-500">
        Supported format: PDF (max 50 MB). Scanned PDFs will use OCR extraction.
      </p>
    </div>
  );
};

export default ProtocolUpload;
