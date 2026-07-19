/**
 * TrialMatch AI Criteria Review Component
 *
 * Displays extracted criteria in editable cards with:
 * - Criterion ID badge and type tag (inclusion/exclusion)
 * - Editable description
 * - Category and data points needed
 * - Delete and edit buttons
 * - Add new criterion button
 * - Save/confirm button to proceed
 */

import React, { useState } from 'react';
import { useScreening } from '../context/ScreeningContext';

const CriteriaReview = ({ onProceed }) => {
  const { editedCriteria, updateCriterion, deleteCriterion, addCriterion } = useScreening();
  const [editingId, setEditingId] = useState(null);
  const [editingText, setEditingText] = useState('');

  // [IMPLEMENTATION]: Handle edit mode
  const startEdit = (criterion) => {
    setEditingId(criterion.criterion_id);
    setEditingText(criterion.description);
  };

  const saveEdit = () => {
    if (editingId && editingText.trim()) {
      updateCriterion(editingId, { description: editingText });
    }
    setEditingId(null);
  };

  // [IMPLEMENTATION]: Count criteria by type
  const inclusionCount = editedCriteria.filter(c => c.type === 'inclusion').length;
  const exclusionCount = editedCriteria.filter(c => c.type === 'exclusion').length;

  return (
    <div className="w-full max-w-4xl mx-auto p-6">
      {/* Header with Summary */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Review Eligibility Criteria</h2>
        <p className="text-gray-600">
          {inclusionCount} inclusion • {exclusionCount} exclusion • {editedCriteria.length} total
        </p>
      </div>

      {/* Criteria Cards */}
      <div className="space-y-4 mb-8">
        {editedCriteria.map(criterion => (
          <div
            key={criterion.criterion_id}
            className="border rounded-lg p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-start justify-between mb-3">
              {/* ID Badge & Type Tag */}
              <div className="flex items-center gap-3">
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium
                              bg-gray-100 text-gray-800">
                  {criterion.criterion_id}
                </span>
                <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium
                  ${criterion.type === 'inclusion'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                  }`}>
                  {criterion.type === 'inclusion' ? 'Inclusion' : 'Exclusion'}
                </span>
              </div>

              {/* Delete Button */}
              <button
                onClick={() => {
                  if (confirm(`Delete criterion ${criterion.criterion_id}?`)) {
                    deleteCriterion(criterion.criterion_id);
                  }
                }}
                className="text-gray-400 hover:text-red-600 transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Description (Editable) */}
            {editingId === criterion.criterion_id ? (
              <div className="mb-3">
                <textarea
                  value={editingText}
                  onChange={(e) => setEditingText(e.target.value)}
                  className="w-full px-3 py-2 border rounded-md text-sm"
                  rows="2"
                />
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={saveEdit}
                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700"
                  >
                    Save
                  </button>
                  <button
                    onClick={() => setEditingId(null)}
                    className="px-3 py-1 bg-gray-300 text-gray-700 text-sm rounded hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="mb-3">
                <p className="text-gray-700 text-sm">{criterion.description}</p>
                <button
                  onClick={() => startEdit(criterion)}
                  className="text-blue-600 hover:text-blue-800 text-xs mt-2"
                >
                  Edit
                </button>
              </div>
            )}

            {/* Metadata */}
            <div className="text-xs text-gray-500 space-y-1">
              {criterion.category && (
                <p><span className="font-medium">Category:</span> {criterion.category}</p>
              )}
              {criterion.data_points_needed?.length > 0 && (
                <p>
                  <span className="font-medium">Data needed:</span>{' '}
                  {criterion.data_points_needed.map(dp => dp.name).join(', ')}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Add Criterion Button */}
      <div className="mb-8">
        <button
          onClick={() => {
            const description = prompt('Enter criterion description:');
            if (description) {
              addCriterion({
                type: confirm('Is this an inclusion criterion?') ? 'inclusion' : 'exclusion',
                description,
                category: 'other',
                data_points_needed: [],
              });
            }
          }}
          className="px-4 py-2 border-2 border-dashed border-blue-400 text-blue-600
                   rounded-lg hover:bg-blue-50 transition-colors"
        >
          + Add Custom Criterion
        </button>
      </div>

      {/* Proceed Button */}
      <div className="flex gap-4">
        <button
          onClick={onProceed}
          disabled={editedCriteria.length === 0}
          className="flex-1 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg
                   hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Proceed to Patient Screening →
        </button>
      </div>
    </div>
  );
};

export default CriteriaReview;
