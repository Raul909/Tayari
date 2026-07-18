'use client';
import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';

export default function AuthModal({ onClose }) {
  const [view, setView] = useState('login'); // 'login', 'register', 'forgot_password', 'reset_sent'
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, register, prefetch, resetPasswordForEmail } = useAuth();

  // Warm the (lazily-loaded) Supabase SDK while the user is still typing, so
  // submitting doesn't wait on a cold import.
  useEffect(() => {
    prefetch?.();
  }, [prefetch]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      if (view === 'login') {
        await login(email, password);
        onClose();
      } else if (view === 'register') {
        await register(email, password, displayName);
        onClose();
      } else if (view === 'forgot_password') {
        await resetPasswordForEmail(email);
        setView('reset_sent');
      }
    } catch (err) {
      setError(err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={e => e.stopPropagation()}>
        <div className="auth-tabs">
          <button 
            className={`auth-tab ${view === 'login' ? 'active' : ''}`}
            onClick={() => setView('login')}
          >
            Sign In
          </button>
          <button 
            className={`auth-tab ${view === 'register' ? 'active' : ''}`}
            onClick={() => setView('register')}
          >
            Create Account
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          
          {view === 'reset_sent' ? (
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <h3 style={{ marginBottom: '10px', color: 'var(--color-primary)' }}>Check Your Email</h3>
              <p style={{ color: 'var(--color-text-muted)' }}>
                We've sent a password reset link to <strong>{email}</strong>.
              </p>
              <button 
                type="button" 
                className="btn btn-secondary" 
                style={{ width: '100%', marginTop: '20px' }}
                onClick={() => setView('login')}
              >
                Back to Sign In
              </button>
            </div>
          ) : (
            <>
              {view === 'register' && (
                <div className="form-group">
                  <label className="form-label">Display Name</label>
                  <input 
                    className="form-input" 
                    type="text" 
                    value={displayName} 
                    onChange={e => setDisplayName(e.target.value)} 
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label">Email</label>
                <input 
                  className="form-input" 
                  type="email" 
                  value={email} 
                  onChange={e => setEmail(e.target.value)} 
                  required 
                />
              </div>

              {view !== 'forgot_password' && (
                <div className="form-group">
                  <label className="form-label">Password</label>
                  <input 
                    className="form-input" 
                    type="password" 
                    value={password} 
                    onChange={e => setPassword(e.target.value)} 
                    required 
                    minLength={6}
                  />
                  {view === 'login' && (
                    <div style={{ textAlign: 'right', marginTop: '8px' }}>
                      <button 
                        type="button"
                        onClick={() => setView('forgot_password')}
                        style={{ 
                          background: 'none', border: 'none', padding: 0, 
                          color: 'var(--color-primary)', cursor: 'pointer', fontSize: '0.85rem' 
                        }}
                      >
                        Forgot Password?
                      </button>
                    </div>
                  )}
                </div>
              )}

              {view === 'forgot_password' && (
                 <div style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', marginBottom: '15px' }}>
                   Enter your email address and we'll send you a link to reset your password.
                 </div>
              )}

              <button 
                type="submit" 
                className="btn btn-primary" 
                style={{ width: '100%', marginTop: '10px' }}
                disabled={loading}
              >
                {loading ? 'Please wait...' : (
                  view === 'login' ? 'Sign In' : 
                  view === 'register' ? 'Create Account' : 
                  'Send Reset Link'
                )}
              </button>

              {view === 'forgot_password' && (
                <button 
                  type="button" 
                  className="btn btn-secondary" 
                  style={{ width: '100%', marginTop: '10px' }}
                  onClick={() => setView('login')}
                  disabled={loading}
                >
                  Back to Sign In
                </button>
              )}
            </>
          )}
        </form>
      </div>
    </div>
  );
}
