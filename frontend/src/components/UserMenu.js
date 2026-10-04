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
      <button
        type="button"
        className="user-avatar"
        onClick={() => setShowDropdown(!showDropdown)}
        aria-haspopup="menu"
        aria-expanded={showDropdown}
        aria-label="Account menu"
      >
        {initial}
      </button>
      
      {showDropdown && (
        <div className="user-dropdown" role="menu">
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
            role="menuitem"
            style={{ color: 'var(--risk-high)' }}
            onClick={async () => {
              setShowDropdown(false);
              try {
                await logout();
              } catch (e) {
                notify({ type: 'error', title: 'Could not sign out', message: e.message });
              }
            }}
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
