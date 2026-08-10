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
          <p className="onboarding-subtitle">Multi-Hazard Early Warning & Early Action</p>
        </div>

        <div className="onboarding-body">
          <p>
            Tell Tayari where you are and it checks nine hazards against live data — flooding,
            earthquakes, tsunami, volcanic activity, storms, heat, wildfire, drought and
            landslides — then explains what to do about the ones that matter.
          </p>
          <p>
            Sign in to receive alerts and keep your places and advisory history across devices,
            or continue as a guest.
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
