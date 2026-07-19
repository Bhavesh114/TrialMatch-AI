/**
 * TrialMatch AI Report Page
 *
 * Displays screening results and report export
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScreening } from '../context/ScreeningContext';
import ScreeningResults from '../components/ScreeningResults';
import { exportReport, downloadPDF } from '../utils/api';

const Report = () => {
  const navigate = useNavigate();
  const { screeningResult, patientSummary, trialInfo, resetSession, isLoading, setLoading, setError } = useScreening();
  const [reportGenerating, setReportGenerating] = React.useState(false);

  if (!screeningResult) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">No screening results available.</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Start New Screening
          </button>
        </div>
      </div>
    );
  }

  const handleExportPDF = async () => {
    setReportGenerating(true);
    try {
      const blob = await exportReport(screeningResult, patientSummary, trialInfo);
      downloadPDF(blob, `TrialMatch_Report_${screeningResult.screening_id}.pdf`);
    } catch (error) {
      setError(error.message);
    } finally {
      setReportGenerating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="mb-6 text-sm text-gray-600">
          <a href="/" className="text-blue-600 hover:text-blue-700">Home</a>
          <span className="mx-2">/</span>
          <span className="text-gray-900">Screening Report</span>
        </div>

        {/* Action Buttons */}
        <div className="mb-6 flex flex-wrap gap-3">
          <button
            onClick={handleExportPDF}
            disabled={reportGenerating}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700
                     disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {reportGenerating ? 'Generating PDF...' : '📥 Download PDF Report'}
          </button>

          <button
            onClick={() => window.print()}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg
                     hover:bg-gray-50"
          >
            🖨️ Print
          </button>

          <button
            onClick={() => {
              resetSession();
              navigate('/');
            }}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg
                     hover:bg-gray-50"
          >
            ↻ New Screening
          </button>
        </div>

        {/* Results */}
        <ScreeningResults screeningResult={screeningResult} />

        {/* Report Footer */}
        <div className="mt-12 pt-6 border-t border-gray-200 text-center text-xs text-gray-500">
          <p>Report ID: {screeningResult.screening_id}</p>
          <p>Generated: {new Date(screeningResult.assessed_at).toLocaleString()}</p>
        </div>
      </div>
    </div>
  );
};

export default Report;
