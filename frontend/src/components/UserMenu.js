'use client';
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '@/lib/auth';
import { useToast } from '@/components/Toast';
import AuthModal from './AuthModal';

export default function UserMenu() {
  const { user, logout } = useAuth();
  const [showDropdown, setShowDropdown] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const menuRef = useRef(null);
  const hideTimerRef = useRef(null);
  const { notify } = useToast();

  // Close on outside click
  useEffect(() => {
    if (!showDropdown) return;
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showDropdown]);

  // Cleanup hide timer on unmount
  useEffect(() => {
    return () => {
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
    };
  }, []);

  function handleMouseLeave() {
    hideTimerRef.current = setTimeout(() => setShowDropdown(false), 300);
  }

  function handleMouseEnter() {
    if (hideTimerRef.current) {
      clearTimeout(hideTimerRef.current);
      hideTimerRef.current = null;
    }
  }

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
    <div className="user-menu" ref={menuRef} onMouseLeave={handleMouseLeave} onMouseEnter={handleMouseEnter}>
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
          
          <button
            className="user-dropdown-item"
            onClick={() => notify({ type: 'info', title: 'Saved Basins', message: 'Coming soon.' })}
          >
            Saved Basins
          </button>
          <button
            className="user-dropdown-item"
            onClick={() => notify({ type: 'info', title: 'Preferences', message: 'Coming soon.' })}
          >
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
