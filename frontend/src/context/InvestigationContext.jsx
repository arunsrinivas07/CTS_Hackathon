import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { investigationsAPI, claimsAPI } from '../services/api';

export const InvestigationContext = createContext();

export const useInvestigation = () => {
  const context = useContext(InvestigationContext);
  if (!context) {
    throw new Error('useInvestigation must be used within an InvestigationProvider');
  }
  return context;
};

export const InvestigationProvider = ({ children }) => {
  const [activeClaimId, setActiveClaimId] = useState(null);
  const [activeInvestigationId, setActiveInvestigationId] = useState(null);
  const [claimData, setClaimData] = useState(null);
  const [investigationData, setInvestigationData] = useState(null);
  const [traceData, setTraceData] = useState(null);
  const [findingsData, setFindingsData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  // Called by CaseDetail when it loads a new claim — keeps context in sync
  const setActiveClaim = useCallback((claimNumber, claimObj) => {
    // If switching to a different claim, clear investigation context
    if (claimNumber !== activeClaimId) {
      setActiveInvestigationId(null);
      setInvestigationData(null);
      setTraceData(null);
      setFindingsData(null);
    }
    setActiveClaimId(claimNumber);
    if (claimObj) setClaimData(claimObj);
  }, [activeClaimId]);

  // Called when an investigation is started or loaded
  const setActiveInvestigation = useCallback((investigationId, stateObj) => {
    setActiveInvestigationId(investigationId);
    if (stateObj) setInvestigationData(stateObj);
  }, []);

  const loadInvestigation = useCallback(async (investigationId) => {
    if (!investigationId) return;
    setIsLoading(true);
    setError(null);
    try {
      const data = await investigationsAPI.getAgenticState(investigationId);
      setInvestigationData(data);
      setActiveInvestigationId(investigationId);

      const trace = await investigationsAPI.getTrace(investigationId).catch(() => null);
      setTraceData(trace);
    } catch (err) {
      console.error('Failed to load investigation', err);
      setError(err.message || 'Failed to load investigation');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const startInvestigation = async (data) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await investigationsAPI.start(data);
      setActiveInvestigationId(response.investigation_id);
      setInvestigationData(response);
      return response;
    } catch (err) {
      setError(err.message || 'Failed to start investigation');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const refreshInvestigation = async (investigationId) => {
    const invId = investigationId || activeInvestigationId;
    if (!invId) return;
    try {
      const data = await investigationsAPI.getAgenticState(invId);
      setInvestigationData(data);
      const trace = await investigationsAPI.getTrace(invId).catch(() => null);
      setTraceData(trace);
    } catch (err) {
      console.error('Failed to refresh investigation', err);
    }
  };

  const value = {
    activeClaimId,
    activeInvestigationId,
    claimData,
    setClaimData,
    investigationData,
    traceData,
    findingsData,
    isLoading,
    error,
    setActiveClaim,
    setActiveInvestigation,
    loadInvestigation,
    startInvestigation,
    refreshInvestigation,
  };

  return (
    <InvestigationContext.Provider value={value}>
      {children}
    </InvestigationContext.Provider>
  );
};
