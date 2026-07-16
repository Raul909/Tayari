'use client';
import { useState } from 'react';
import AuthModal from './AuthModal';

export default function OnboardingSplash({ onGuestContinue }) {
  const [showAuth, setShowAuth] = useState(false);

  return (
    <div className="onboarding-splash">
      <div className="onboarding-content">
        <button className="onboarding-close" aria-label="Close" onClick={onGuestContinue}>
          &times;
        </button>
        <div className="onboarding-header">
          <h1 className="onboarding-title">Welcome to Tayari</h1>
          <p className="onboarding-subtitle">Flood Early Warning & Early Action System</p>
        </div>
        
        <div className="onboarding-body">
          <p>
            Tayari provides community-driven flood advisories and impact assessments for river basins.
          </p>
          <p>
            Sign in to receive personalized alerts and keep a persistent memory of your flood advisory inquiries across devices.
          </p>
        </div>

        <div className="onboarding-actions">
          <button 
            className="btn btn-primary btn-lg" 
            style={{ width: '100%' }}
            onClick={() => setShowAuth(true)}
          >
            Sign In / Create Account
          </button>
          <button 
            className="btn btn-ghost btn-lg" 
            style={{ width: '100%' }}
            onClick={onGuestContinue}
          >
            Continue as Guest
          </button>
        </div>
      </div>
      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}
