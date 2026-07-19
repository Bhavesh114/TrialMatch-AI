/**
 * TrialMatch AI Main Application Component
 *
 * Sets up routing and layout for multi-step screening workflow
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ScreeningProvider } from './context/ScreeningContext';
import Home from './pages/Home';
import Extract from './pages/Extract';
import Screen from './pages/Screen';
import Report from './pages/Report';

const App = () => {
  return (
    <Router>
      <ScreeningProvider>
        <div className="min-h-screen bg-gray-50">
          {/* Header Navigation */}
          <nav className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">TM</span>
                </div>
                <h1 className="text-xl font-bold text-gray-900">TrialMatch AI</h1>
              </div>
              <p className="text-sm text-gray-500">Clinical Trial Eligibility Screener</p>
            </div>
          </nav>

          {/* Routes */}
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/extract" element={<Extract />} />
            <Route path="/screen" element={<Screen />} />
            <Route path="/report" element={<Report />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </ScreeningProvider>
    </Router>
  );
};

export default App;
