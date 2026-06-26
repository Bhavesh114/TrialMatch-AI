/**
 * TrialMatch AI Extract Page
 *
 * Shows protocol preview and criteria review
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScreening } from '../context/ScreeningContext';
import CriteriaReview from '../components/CriteriaReview';

const Extract = () => {
  const navigate = useNavigate();
  const { extractedCriteria, editedCriteria } = useScreening();

  const handleProceed = () => {
    if (editedCriteria.length > 0) {
      navigate('/screen');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="mb-6 text-sm text-gray-600">
          <a href="/" className="text-blue-600 hover:text-blue-700">Home</a>
          <span className="mx-2">/</span>
          <span className="text-gray-900">Extract Criteria</span>
        </div>

        {/* Extraction Info */}
        {extractedCriteria && (
          <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-sm text-green-900">
              <span className="font-semibold">✓ Protocol parsed successfully</span>
              <br />
              Extracted {extractedCriteria.criteria?.length || 0} criteria
              ({extractedCriteria.inclusion_count || 0} inclusion, {extractedCriteria.exclusion_count || 0} exclusion)
              {extractedCriteria.extraction_confidence && (
                <> | Confidence: {(extractedCriteria.extraction_confidence * 100).toFixed(0)}%</>
              )}
            </p>
          </div>
        )}

        {/* Warnings */}
        {extractedCriteria?.warnings?.length > 0 && (
          <div className="mb-6 space-y-2">
            {extractedCriteria.warnings.map((warning, idx) => (
              <div
                key={idx}
                className={`p-4 rounded-lg border ${
                  warning.severity === 'error'
                    ? 'bg-red-50 border-red-200 text-red-900'
                    : warning.severity === 'warning'
                    ? 'bg-yellow-50 border-yellow-200 text-yellow-900'
                    : 'bg-blue-50 border-blue-200 text-blue-900'
                }`}
              >
                <p className="text-sm">
                  <span className="font-semibold">{warning.code}:</span> {warning.message}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* Criteria Review */}
        <CriteriaReview onProceed={handleProceed} />
      </div>
    </div>
  );
};

export default Extract;
