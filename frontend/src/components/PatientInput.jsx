/**
 * TrialMatch AI Patient Input Component
 *
 * Two modes for entering patient data:
 * 1. Structured form with individual fields
 * 2. Free-text paste with expected format
 *
 * Features:
 * - Tab toggle between modes
 * - Form validation
 * - Add/remove tags for diagnoses, medications
 * - PHI warning reminder
 * - Submit button with validation
 */

import React, { useState } from 'react';
import { useScreening } from '../context/ScreeningContext';
import { screenPatient } from '../utils/api';

const PatientInput = ({ criteria }) => {
  const [mode, setMode] = useState('structured'); // 'structured' or 'freetext'
  const { editedCriteria, setScreeningResult, setLoading, setError } = useScreening();

  // [IMPLEMENTATION]: Structured form state
  const [formData, setFormData] = useState({
    patient_id: 'PT-',
    age: '',
    sex: '',
    diagnoses: [],
    medications: [],
    lab_values: {},
    comorbidities: [],
    surgical_history: [],
    allergies: [],
    free_text_notes: '',
  });

  // [IMPLEMENTATION]: Free-text state
  const [freeTextInput, setFreeTextInput] = useState('');

  // [IMPLEMENTATION]: Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!formData.patient_id.trim()) {
      setError('Patient ID is required');
      return;
    }

    setLoading(true);
    try {
      const result = await screenPatient(formData, editedCriteria);
      setScreeningResult(result);
    } catch (error) {
      setError(error.message);
    } finally {
      setLoading(false);
    }
  };

  // [IMPLEMENTATION]: Add item to array field
  const addArrayItem = (field, value) => {
    if (value.trim()) {
      setFormData(prev => ({
        ...prev,
        [field]: [...prev[field], value]
      }));
    }
  };

  const removeArrayItem = (field, index) => {
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].filter((_, i) => i !== index)
    }));
  };

  return (
    <div className="w-full max-w-2xl mx-auto p-6">
      {/* PHI Warning */}
      <div className="mb-6 p-4 bg-amber-50 border border-amber-200 rounded-lg">
        <p className="text-sm text-amber-900">
          <span className="font-semibold">⚠️ De-identification Required:</span> Only enter
          de-identified patient data. Do not include names, DOB, MRN, or other identifiers.
        </p>
      </div>

      {/* Mode Toggle */}
      <div className="flex gap-4 mb-6 border-b">
        <button
          onClick={() => setMode('structured')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            mode === 'structured'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Structured Form
        </button>
        <button
          onClick={() => setMode('freetext')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            mode === 'freetext'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          Paste Text
        </button>
      </div>

      {/* Structured Form Mode */}
      {mode === 'structured' && (
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Patient ID */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Patient ID (de-identified)
            </label>
            <input
              type="text"
              value={formData.patient_id}
              onChange={(e) => setFormData(prev => ({ ...prev, patient_id: e.target.value }))}
              placeholder="PT-00001"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {/* Age & Sex */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Age</label>
              <input
                type="number"
                value={formData.age}
                onChange={(e) => setFormData(prev => ({ ...prev, age: e.target.value }))}
                placeholder="45"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Sex</label>
              <select
                value={formData.sex}
                onChange={(e) => setFormData(prev => ({ ...prev, sex: e.target.value }))}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg"
              >
                <option value="">Select...</option>
                <option value="Male">Male</option>
                <option value="Female">Female</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          {/* Diagnoses */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Diagnoses</label>
            <div className="flex gap-2 mb-2">
              <input
                id="diagnosis-input"
                type="text"
                placeholder="Add diagnosis"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <button
                type="button"
                onClick={() => {
                  const input = document.getElementById('diagnosis-input');
                  addArrayItem('diagnoses', input.value);
                  input.value = '';
                }}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {formData.diagnoses.map((diag, idx) => (
                <span
                  key={idx}
                  className="inline-flex items-center gap-2 px-3 py-1 bg-blue-100 text-blue-800 rounded-full"
                >
                  {diag}
                  <button
                    type="button"
                    onClick={() => removeArrayItem('diagnoses', idx)}
                    className="text-blue-600 hover:text-blue-800 font-bold"
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Medications */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Medications</label>
            <div className="flex gap-2 mb-2">
              <input
                id="med-input"
                type="text"
                placeholder="e.g., metformin 500mg twice daily"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg"
              />
              <button
                type="button"
                onClick={() => {
                  const input = document.getElementById('med-input');
                  addArrayItem('medications', input.value);
                  input.value = '';
                }}
                className="px-4 py-2 bg-gray-200 rounded-lg hover:bg-gray-300"
              >
                Add
              </button>
            </div>
            <ul className="space-y-1">
              {formData.medications.map((med, idx) => (
                <li key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                  <span className="text-sm">{med}</span>
                  <button
                    type="button"
                    onClick={() => removeArrayItem('medications', idx)}
                    className="text-gray-400 hover:text-red-600"
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          </div>

          {/* Allergies & Notes */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Allergies</label>
            <input
              id="allergies-input"
              type="text"
              placeholder="Comma-separated"
              defaultValue={formData.allergies.join(', ')}
              onChange={(e) =>
                setFormData(prev => ({
                  ...prev,
                  allergies: e.target.value.split(',').map(a => a.trim()).filter(Boolean)
                }))
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes
            </label>
            <textarea
              value={formData.free_text_notes}
              onChange={(e) => setFormData(prev => ({ ...prev, free_text_notes: e.target.value }))}
              placeholder="Any relevant clinical notes"
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg"
            />
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg
                     hover:bg-blue-700 transition-colors"
          >
            Analyze Eligibility
          </button>
        </form>
      )}

      {/* Free-Text Mode */}
      {mode === 'freetext' && (
        <div className="space-y-4">
          <div className="p-3 bg-gray-50 rounded-lg text-sm text-gray-600">
            <p className="font-medium mb-2">Expected Format:</p>
            <pre className="whitespace-pre-wrap text-xs">
{`Patient ID: PT-00001
Age: 55
Sex: Male
Diagnoses: Type 2 Diabetes, Hypertension
Medications: metformin 500mg twice daily, lisinopril 10mg daily
Lab Values: HbA1c 7.2%, eGFR 92 mL/min/1.73m2
Allergies: Penicillin
Notes: Good medication adherence`}
            </pre>
          </div>

          <textarea
            value={freeTextInput}
            onChange={(e) => setFreeTextInput(e.target.value)}
            placeholder="Paste patient data here..."
            rows="8"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg font-mono text-sm"
          />

          <button
            onClick={() => {
              // [IMPLEMENTATION]: Parse free-text input
              // This would require a parser to extract fields from free text
              console.log('Parsing free text input');
            }}
            className="w-full px-6 py-3 bg-blue-600 text-white font-medium rounded-lg
                     hover:bg-blue-700"
          >
            Analyze Eligibility
          </button>
        </div>
      )}
    </div>
  );
};

export default PatientInput;
