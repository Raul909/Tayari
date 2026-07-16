'use client';
import { useState } from 'react';
import { useAuth } from '@/lib/auth';
import AuthModal from './AuthModal';

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showModal, setShowModal] = useState(false);

  if (!user) {
    return (
      <>
        <button className="btn btn-ghost btn-sm" onClick={() => setShowModal(true)}>
          Sign in
        </button>
        {showModal && <AuthModal onClose={() => setShowModal(false)} />}
      </>
    );
  }

  const initial = (user.user_metadata?.display_name || user.email || '?').charAt(0).toUpperCase();

  return (
    <div className="user-menu" onMouseLeave={() => setShowDropdown(false)}>
      <div 
        className="user-avatar" 
        onClick={() => setShowDropdown(!showDropdown)}
      >
        {initial}
      </div>
      
      {showDropdown && (
        <div className="user-dropdown">
          <div style={{ padding: '8px 16px', borderBottom: '1px solid var(--border-color)', marginBottom: '4px' }}>
            <div style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-primary)' }}>
              {user.user_metadata?.display_name || 'User'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {user.email}
            </div>
          </div>
          
          <button className="user-dropdown-item" onClick={() => alert('Saved basins (Coming soon)')}>
            Saved Basins
          </button>
          <button className="user-dropdown-item" onClick={() => alert('Preferences (Coming soon)')}>
            Preferences
          </button>
          <button 
            className="user-dropdown-item" 
            style={{ color: 'var(--risk-high)', marginTop: '4px', borderTop: '1px solid var(--border-color)', paddingTop: '8px' }}
            onClick={logout}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
