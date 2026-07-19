"""
TrialMatch AI Screening Context

React Context for managing application-wide screening state.

State includes:
- Protocol file and extracted criteria
- Patient summary data
- Screening results
- Current navigation step
- Loading and error states

Provides hooks and actions for components to read/modify state.
Session data is cleared when browser closes (no persistence).
"""

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

// [IMPLEMENTATION]: Create context with default values
const ScreeningContext = createContext(null);

// ============================================================================
// SCREENING PROVIDER COMPONENT
// ============================================================================

export const ScreeningProvider = ({ children }) => {
  /**
   * Main state management for screening application
   *
   * State structure:
   * {
   *   protocolFile: File | null,
   *   extractedCriteria: CriteriaExtractionResult | null,
   *   editedCriteria: CriterionModel[],
   *   patientSummary: PatientSummary | null,
   *   screeningResult: ScreeningResult | null,
   *   currentStep: 'home' | 'extract' | 'screen' | 'report',
   *   isLoading: boolean,
   *   error: string | null,
   *   trialInfo: {} - metadata about current trial
   * }
   */

  // [IMPLEMENTATION]: Protocol & Criteria State
  const [protocolFile, setProtocolFile] = useState(null);
  const [extractedCriteria, setExtractedCriteria] = useState(null);
  const [editedCriteria, setEditedCriteria] = useState([]);

  // [IMPLEMENTATION]: Patient & Screening State
  const [patientSummary, setPatientSummary] = useState(null);
  const [screeningResult, setScreeningResult] = useState(null);

  // [IMPLEMENTATION]: Navigation & UI State
  const [currentStep, setCurrentStep] = useState('home');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // [IMPLEMENTATION]: Trial metadata
  const [trialInfo, setTrialInfo] = useState({});

  // ========================================================================
  // CRITERIA MANAGEMENT ACTIONS
  // ========================================================================

  /**
   * Update extracted criteria from API response
   * Also initializes editedCriteria for user modifications
   */
  const handleSetExtractedCriteria = useCallback((criteria) => {
    setExtractedCriteria(criteria);
    // [IMPLEMENTATION]: Initialize editable copy
    setEditedCriteria(criteria.criteria || []);
    // [IMPLEMENTATION]: Store trial info if present
    if (criteria.trial_name) {
      setTrialInfo(prev => ({ ...prev, trial_name: criteria.trial_name }));
    }
  }, []);

  /**
   * Update a single criterion by ID
   * Used when user edits criterion description or properties
   */
  const updateCriterion = useCallback((criterionId, updates) => {
    setEditedCriteria(prev =>
      prev.map(criterion =>
        criterion.criterion_id === criterionId
          ? { ...criterion, ...updates }
          : criterion
      )
    );
  }, []);

  /**
   * Delete a criterion from the list
   * Updates both extracted and edited criteria
   */
  const deleteCriterion = useCallback((criterionId) => {
    setEditedCriteria(prev =>
      prev.filter(criterion => criterion.criterion_id !== criterionId)
    );
  }, []);

  /**
   * Add a new user-defined criterion
   * User can manually add criteria not extracted from protocol
   */
  const addCriterion = useCallback((newCriterion) => {
    // [IMPLEMENTATION]: Generate new ID based on type and count
    const inclusionCount = editedCriteria.filter(c => c.type === 'inclusion').length;
    const exclusionCount = editedCriteria.filter(c => c.type === 'exclusion').length;

    const newId = newCriterion.type === 'inclusion'
      ? `I${inclusionCount + 1}`
      : `E${exclusionCount + 1}`;

    const criterion = {
      criterion_id: newId,
      ...newCriterion,
      confidence: 1.0,
      notes: 'User-added criterion'
    };

    setEditedCriteria(prev => [...prev, criterion]);
  }, [editedCriteria]);

  // ========================================================================
  // PATIENT & SCREENING ACTIONS
  // ========================================================================

  /**
   * Set patient summary from form input
   * Triggers when user submits patient data
   */
  const handleSetPatientSummary = useCallback((summary) => {
    setPatientSummary(summary);
  }, []);

  /**
   * Set screening results after API call
   * Triggers when screening completes
   */
  const handleSetScreeningResult = useCallback((result) => {
    setScreeningResult(result);
  }, []);

  // ========================================================================
  // NAVIGATION & UI ACTIONS
  // ========================================================================

  /**
   * Navigate to a specific step in the workflow
   * Validates state before allowing navigation
   */
  const navigateToStep = useCallback((step) => {
    // [IMPLEMENTATION]: Validate step prerequisites
    if (step === 'extract' && !protocolFile) {
      setError('Please upload a protocol PDF first');
      return;
    }
    if (step === 'screen' && editedCriteria.length === 0) {
      setError('Please extract or add criteria first');
      return;
    }
    if (step === 'report' && !screeningResult) {
      setError('Please complete screening first');
      return;
    }

    setCurrentStep(step);
    setError(null);  // [IMPLEMENTATION]: Clear error on successful navigation
  }, [protocolFile, editedCriteria, screeningResult]);

  const setLoading = useCallback((isLoading) => {
    setIsLoading(isLoading);
  }, []);

  const setErrorMessage = useCallback((message) => {
    setError(message);
  }, []);

  // ========================================================================
  // SESSION MANAGEMENT
  // ========================================================================

  /**
   * Reset entire session for new screening
   * Called when user clicks "Start New Screening"
   */
  const resetSession = useCallback(() => {
    setProtocolFile(null);
    setExtractedCriteria(null);
    setEditedCriteria([]);
    setPatientSummary(null);
    setScreeningResult(null);
    setCurrentStep('home');
    setError(null);
    setTrialInfo({});
  }, []);

  /**
   * Clear error message
   * Called when user dismisses error notification
   */
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  // ========================================================================
  // SESSION CLEANUP ON UNMOUNT
  // ========================================================================

  useEffect(() => {
    // [IMPLEMENTATION]: Cleanup on component unmount
    // This ensures session data is cleared when user closes browser
    return () => {
      // Session data stored in state is automatically cleared
      // No persistence mechanisms are used
    };
  }, []);

  // ========================================================================
  // CONTEXT VALUE OBJECT
  // ========================================================================

  const value = {
    // State
    protocolFile,
    extractedCriteria,
    editedCriteria,
    patientSummary,
    screeningResult,
    currentStep,
    isLoading,
    error,
    trialInfo,

    // Criteria actions
    setProtocolFile,
    setExtractedCriteria: handleSetExtractedCriteria,
    updateCriterion,
    deleteCriterion,
    addCriterion,

    // Patient & screening actions
    setPatientSummary: handleSetPatientSummary,
    setScreeningResult: handleSetScreeningResult,

    // Navigation actions
    navigateToStep,
    setLoading,
    setError: setErrorMessage,
    clearError,
    resetSession,
  };

  return (
    <ScreeningContext.Provider value={value}>
      {children}
    </ScreeningContext.Provider>
  );
};

// ============================================================================
// CUSTOM HOOK FOR USING SCREENING CONTEXT
// ============================================================================

/**
 * Hook to use ScreeningContext in components
 *
 * Usage:
 * const { extractedCriteria, setPatientSummary, error } = useScreening();
 */
export const useScreening = () => {
  const context = useContext(ScreeningContext);

  if (!context) {
    throw new Error(
      'useScreening must be used within a ScreeningProvider. ' +
      'Wrap your component tree with <ScreeningProvider>'
    );
  }

  return context;
};

export default ScreeningContext;
