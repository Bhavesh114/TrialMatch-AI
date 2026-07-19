/**
 * TrialMatch AI Screen Page
 *
 * Patient input and screening execution
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScreening } from '../context/ScreeningContext';
import PatientInput from '../components/PatientInput';

const Screen = () => {
  const navigate = useNavigate();
  const { editedCriteria, isLoading, error, clearError } = useScreening();

  if (!editedCriteria || editedCriteria.length === 0) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 flex items-center justify-center">
        <div className="text-center">
          <p className="text-gray-600 mb-4">No criteria loaded. Please start from the beginning.</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Breadcrumb */}
        <div className="mb-6 text-sm text-gray-600">
          <a href="/" className="text-blue-600 hover:text-blue-700">Home</a>
          <span className="mx-2">/</span>
          <a href="/extract" className="text-blue-600 hover:text-blue-700">Extract</a>
          <span className="mx-2">/</span>
          <span className="text-gray-900">Screen Patient</span>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start justify-between">
            <p className="text-sm text-red-900">{error}</p>
            <button
              onClick={clearError}
              className="text-red-400 hover:text-red-600"
            >
              ✕
            </button>
          </div>
        )}

        {/* Loading Indicator */}
        {isLoading && (
          <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-3">
              <div className="animate-spin h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full" />
              <p className="text-sm text-blue-900">
                Analyzing {editedCriteria.length} criteria...
              </p>
            </div>
          </div>
        )}

        {/* Criteria Summary Sidebar */}
        <div className="mb-6 grid md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            {/* Patient Input Form */}
            <PatientInput criteria={editedCriteria} />
          </div>

          <div className="md:col-span-1">
            {/* Criteria Summary */}
            <div className="bg-white border border-gray-200 rounded-lg p-6 sticky top-4">
              <h3 className="font-semibold text-gray-900 mb-4">Criteria Summary</h3>

              <div className="space-y-3">
                <div>
                  <p className="text-xs text-gray-500">Total Criteria</p>
                  <p className="text-2xl font-bold text-gray-900">{editedCriteria.length}</p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <div className="p-3 bg-green-50 rounded">
                    <p className="text-xs text-gray-500">Inclusion</p>
                    <p className="text-lg font-semibold text-green-900">
                      {editedCriteria.filter(c => c.type === 'inclusion').length}
                    </p>
                  </div>
                  <div className="p-3 bg-red-50 rounded">
                    <p className="text-xs text-gray-500">Exclusion</p>
                    <p className="text-lg font-semibold text-red-900">
                      {editedCriteria.filter(c => c.type === 'exclusion').length}
                    </p>
                  </div>
                </div>

                <div className="pt-3 border-t">
                  <p className="text-xs text-gray-500 mb-2">Criteria IDs</p>
                  <div className="flex flex-wrap gap-1">
                    {editedCriteria.map(c => (
                      <span
                        key={c.criterion_id}
                        className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                      >
                        {c.criterion_id}
                      </span>
                    ))}
                  </div>
                </div>
              </div>

              <a
                href="/extract"
                className="mt-6 block text-center px-4 py-2 border border-gray-300 text-gray-700
                         rounded-lg hover:bg-gray-50 text-sm"
              >
                ← Edit Criteria
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Screen;
