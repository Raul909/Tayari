'use client';
import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { getSupabase, hasPersistedSession } from '@/lib/supabase';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isGuest, setGuest] = useState(false);
  const unsubRef = useRef(null);

  // Subscribe to auth-state changes exactly once — whenever Supabase first loads,
  // be that at boot (restoring a session) or on the first sign-in.
  const wireAuth = useCallback((supabase) => {
    if (unsubRef.current) return;
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null);
      if (session?.user) setGuest(false);
      setLoading(false);
    });
    unsubRef.current = () => subscription.unsubscribe();
  }, []);

  useEffect(() => {
    // No persisted token → the visitor is definitely logged out. Resolve
    // immediately and never touch the Supabase SDK, keeping it off the initial
    // load for the guest / first-time path.
    if (!hasPersistedSession()) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setLoading(false);
      return;
    }

    // A token exists: load Supabase to restore / validate the session.
    let active = true;
    getSupabase().then((supabase) => {
      if (!active) return;
      wireAuth(supabase);
      supabase.auth.getSession().then(({ data: { session } }) => {
        if (!active) return;
        setUser(session?.user ?? null);
        setLoading(false);
      });
    });

    return () => {
      active = false;
    };
  }, [wireAuth]);

  // Unsubscribe on unmount.
  useEffect(
    () => () => {
      if (unsubRef.current) {
        unsubRef.current();
        unsubRef.current = null;
      }
    },
    []
  );

  // Warm the SDK ahead of an auth action (e.g. when the modal opens) so the
  // eventual sign-in isn't blocked on a cold import.
  const prefetch = useCallback(() => {
    getSupabase();
  }, []);

  const login = useCallback(
    async (email, password) => {
      const supabase = await getSupabase();
      wireAuth(supabase);
      const { data, error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) throw error;
      setUser(data.user ?? data.session?.user ?? null);
      setGuest(false);
      return data;
    },
    [wireAuth]
  );

  const register = useCallback(
    async (email, password, displayName) => {
      const supabase = await getSupabase();
      wireAuth(supabase);
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: { display_name: displayName },
        },
      });
      if (error) throw error;
      setGuest(false);
      return data;
    },
    [wireAuth]
  );

  const logout = useCallback(async () => {
    const supabase = await getSupabase();
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    setUser(null);
    setGuest(false);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, loading, isGuest, setGuest, login, register, logout, prefetch }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
