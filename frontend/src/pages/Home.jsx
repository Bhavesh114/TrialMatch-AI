/**
 * TrialMatch AI Home Page
 *
 * Landing page with value proposition and protocol upload
 */

import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useScreening } from '../context/ScreeningContext';
import ProtocolUpload from '../components/ProtocolUpload';

const Home = () => {
  const navigate = useNavigate();
  const { setExtractedCriteria } = useScreening();

  const handleUploadSuccess = (criteria) => {
    setExtractedCriteria(criteria);
    navigate('/extract');
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white">
      {/* Hero Section */}
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-6">
          Clinical Trial Eligibility Screening
        </h1>
        <p className="text-lg text-gray-600 mb-4">
          Automatically extract criteria from trial protocols and screen patients
          for eligibility in seconds, not hours.
        </p>
        <p className="text-gray-500">
          Powered by AI. Designed for clinicians. Built for accuracy.
        </p>
      </div>

      {/* How It Works */}
      <div className="max-w-4xl mx-auto px-4 py-12">
        <h2 className="text-2xl font-bold text-gray-900 text-center mb-12">How It Works</h2>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {[
            {
              step: '1',
              title: 'Upload Protocol',
              description: 'Upload a clinical trial protocol PDF to get started'
            },
            {
              step: '2',
              title: 'Review Criteria',
              description: 'AI automatically extracts eligibility criteria for your review'
            },
            {
              step: '3',
              title: 'Screen Patients',
              description: 'Input de-identified patient data to get immediate eligibility assessment'
            }
          ].map(({ step, title, description }) => (
            <div key={step} className="text-center">
              <div className="w-16 h-16 bg-blue-600 text-white rounded-full flex items-center
                            justify-center text-2xl font-bold mx-auto mb-4">
                {step}
              </div>
              <h3 className="font-semibold text-gray-900 mb-2">{title}</h3>
              <p className="text-sm text-gray-600">{description}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Protocol Upload */}
      <div className="max-w-4xl mx-auto px-4 py-12">
        <ProtocolUpload onUploadSuccess={handleUploadSuccess} />
      </div>

      {/* Demo Section */}
      <div className="max-w-4xl mx-auto px-4 py-12 text-center">
        <p className="text-sm text-gray-600 mb-4">Want to see it in action?</p>
        <button
          onClick={() => {
            // [IMPLEMENTATION]: Load demo data
            navigate('/extract');
          }}
          className="px-6 py-2 border-2 border-blue-600 text-blue-600 rounded-lg
                   hover:bg-blue-50 transition-colors"
        >
          Try Demo
        </button>
      </div>

      {/* Features Section */}
      <div className="bg-gray-50 border-t border-gray-200 py-12 mt-12">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-2xl font-bold text-gray-900 text-center mb-8">Key Features</h2>
          <div className="grid md:grid-cols-2 gap-8">
            {[
              { icon: '📄', title: 'PDF Protocol Parsing', desc: 'Handles digital and scanned PDFs with OCR' },
              { icon: '🤖', title: 'AI-Powered Extraction', desc: 'Claude AI extracts structured criteria' },
              { icon: '✓', title: 'Detailed Assessment', desc: 'Per-criterion eligibility with evidence cited' },
              { icon: '⚙️', title: 'Editable Criteria', desc: 'Review and modify extracted criteria' },
              { icon: '🔒', title: 'De-Identification Only', desc: 'Process de-identified data only' },
              { icon: '📊', title: 'PDF Reports', desc: 'Generate professional reports for clinicians' }
            ].map(({ icon, title, desc }) => (
              <div key={title} className="flex gap-4">
                <span className="text-2xl">{icon}</span>
                <div>
                  <h3 className="font-semibold text-gray-900">{title}</h3>
                  <p className="text-sm text-gray-600">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Important Notice */}
      <div className="bg-amber-50 border-t border-amber-200 py-8">
        <div className="max-w-4xl mx-auto px-4">
          <p className="text-sm text-amber-900">
            <span className="font-semibold">⚠️ Important:</span> TrialMatch AI is a decision-support
            tool. All findings must be reviewed by a qualified healthcare professional before making
            trial enrollment decisions. The original protocol is the authoritative source.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Home;
