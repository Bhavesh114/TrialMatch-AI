/**
 * TrialMatch AI Screening Results Component
 *
 * Displays complete screening results with:
 * - Overall eligibility status (green/red/yellow)
 * - Missing data callout
 * - Per-criterion assessment cards
 * - Follow-up questions
 * - Export/Print buttons
 * - Legal disclaimer
 */

import React, { useState } from 'react';
import { useScreening } from '../context/ScreeningContext';

const ScreeningResults = ({ screeningResult }) => {
  const [expandedId, setExpandedId] = useState(null);

  if (!screeningResult) {
    return <div>No screening results available</div>;
  }

  // [IMPLEMENTATION]: Map status to colors and text
  const statusConfig = {
    likely_eligible: {
      color: 'bg-green-50 border-green-200',
      icon: '✓',
      textColor: 'text-green-900',
      bgColor: 'bg-green-100'
    },
    likely_ineligible: {
      color: 'bg-red-50 border-red-200',
      icon: '✗',
      textColor: 'text-red-900',
      bgColor: 'bg-red-100'
    },
    needs_review: {
      color: 'bg-yellow-50 border-yellow-200',
      icon: '?',
      textColor: 'text-yellow-900',
      bgColor: 'bg-yellow-100'
    }
  };

  const config = statusConfig[screeningResult.overall_status];

  return (
    <div className="w-full max-w-4xl mx-auto p-6 space-y-8">
      {/* Overall Status Banner */}
      <div className={`border rounded-lg p-6 ${config.color}`}>
        <div className="flex items-start gap-4">
          <div className={`flex-shrink-0 flex items-center justify-center h-12 w-12 rounded-lg ${config.bgColor}`}>
            <span className={`text-2xl font-bold ${config.textColor}`}>{config.icon}</span>
          </div>
          <div className="flex-1">
            <h2 className={`text-lg font-bold ${config.textColor}`}>
              {screeningResult.overall_status === 'likely_eligible'
                ? 'Patient Appears Eligible'
                : screeningResult.overall_status === 'likely_ineligible'
                ? 'Patient Does Not Meet Criteria'
                : 'Manual Review Recommended'}
            </h2>
            <p className={`text-sm ${config.textColor}`}>
              {screeningResult.overall_status === 'likely_eligible'
                ? 'Patient meets the stated eligibility criteria for this trial.'
                : screeningResult.overall_status === 'likely_ineligible'
                ? 'Patient fails to meet one or more eligibility criteria.'
                : 'Insufficient data or mixed results require clinical review.'}
            </p>
          </div>
        </div>
      </div>

      {/* Missing Data Alert */}
      {screeningResult.missing_data_summary?.length > 0 && (
        <div className="border border-amber-200 bg-amber-50 rounded-lg p-4">
          <h3 className="font-semibold text-amber-900 mb-2">Data Needed for Complete Assessment</h3>
          <ul className="text-sm text-amber-800 space-y-1">
            {screeningResult.missing_data_summary.map((item, idx) => (
              <li key={idx}>• {item}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Criteria Summary */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Meets', count: screeningResult.assessments.filter(a => a.status === 'meets').length, color: 'green' },
          { label: 'Does Not Meet', count: screeningResult.assessments.filter(a => a.status === 'does_not_meet').length, color: 'red' },
          { label: 'Insufficient Data', count: screeningResult.assessments.filter(a => a.status === 'insufficient_data').length, color: 'yellow' }
        ].map(({ label, count, color }) => (
          <div key={label} className={`p-4 bg-${color}-50 border border-${color}-200 rounded-lg text-center`}>
            <p className={`text-2xl font-bold text-${color}-900`}>{count}</p>
            <p className={`text-sm text-${color}-700`}>{label}</p>
          </div>
        ))}
      </div>

      {/* Criteria Assessment Cards */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Criterion-by-Criterion Assessment</h3>
        <div className="space-y-3">
          {screeningResult.assessments.map(assessment => (
            <div
              key={assessment.criterion_id}
              className="border rounded-lg overflow-hidden hover:shadow-md transition-shadow"
            >
              {/* Criterion Header */}
              <button
                onClick={() => setExpandedId(expandedId === assessment.criterion_id ? null : assessment.criterion_id)}
                className="w-full p-4 text-left hover:bg-gray-50 flex items-center justify-between"
              >
                <div className="flex items-center gap-3">
                  <span className="font-mono font-semibold text-gray-700">{assessment.criterion_id}</span>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${
                    assessment.status === 'meets'
                      ? 'bg-green-100 text-green-800'
                      : assessment.status === 'does_not_meet'
                      ? 'bg-red-100 text-red-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {assessment.status === 'meets' ? '✓ Meets'
                      : assessment.status === 'does_not_meet' ? '✗ Does Not Meet'
                      : '? Insufficient'}
                  </span>
                  <span className="text-xs px-2 py-1 bg-gray-100 text-gray-600 rounded">
                    {assessment.confidence} confidence
                  </span>
                </div>
                <span className="text-gray-400">{expandedId === assessment.criterion_id ? '▼' : '▶'}</span>
              </button>

              {/* Expanded Details */}
              {expandedId === assessment.criterion_id && (
                <div className="border-t bg-gray-50 p-4 space-y-3">
                  <div>
                    <p className="text-sm font-medium text-gray-700">Rationale</p>
                    <p className="text-sm text-gray-600 mt-1">{assessment.reasoning}</p>
                  </div>

                  {assessment.evidence_cited?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700">Evidence Cited</p>
                      <ul className="text-sm text-gray-600 mt-1 space-y-1">
                        {assessment.evidence_cited.map((evidence, idx) => (
                          <li key={idx}>• {evidence}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {assessment.missing_data?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium text-gray-700">Missing Data</p>
                      <ul className="text-sm text-gray-600 mt-1 space-y-1">
                        {assessment.missing_data.map((item, idx) => (
                          <li key={idx}>• {item}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Follow-up Questions */}
      {screeningResult.follow_up_questions?.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Recommended Follow-ups</h3>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 space-y-3">
            {screeningResult.follow_up_questions.map((question, idx) => (
              <div key={idx} className="flex gap-3">
                <span className="flex-shrink-0 font-semibold text-blue-700">{idx + 1}.</span>
                <p className="text-sm text-blue-900">{question}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Disclaimer Footer */}
      <div className="border-t-2 border-gray-200 pt-6">
        <p className="text-xs text-gray-500 italic">
          This automated screening report is for clinical decision support only.
          A qualified healthcare professional must review all findings and validate
          against the original protocol before making enrollment decisions.
        </p>
      </div>
    </div>
  );
};

export default ScreeningResults;
