'use client';
import { useState, useEffect } from 'react';
import { useAuth } from '@/lib/auth';

export default function AuthModal({ onClose }) {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const { login, register, prefetch } = useAuth();

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
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, password, displayName);
      }
      onClose();
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
            className={`auth-tab ${isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(true)}
          >
            Sign In
          </button>
          <button 
            className={`auth-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(false)}
          >
            Create Account
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          {error && <div className="auth-error">{error}</div>}
          
          {!isLogin && (
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
          </div>

          <button 
            type="submit" 
            className="btn btn-primary" 
            style={{ width: '100%', marginTop: '10px' }}
            disabled={loading}
          >
            {loading ? 'Please wait...' : (isLogin ? 'Sign In' : 'Create Account')}
          </button>
        </form>
      </div>
    </div>
  );
}
