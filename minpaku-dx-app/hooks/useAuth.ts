import { useEffect, useState } from 'react';
import { supabase, DEV_SKIP_AUTH } from '@/lib/supabase';
import type { Session } from '@supabase/supabase-js';

/**
 * Tracks Supabase Auth session state.
 * When DEV_SKIP_AUTH is true, pretends the user is always authenticated.
 */
export function useAuth() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (DEV_SKIP_AUTH) {
      setLoading(false);
      return;
    }

    // Get initial session
    supabase.auth.getSession().then(({ data: { session: s } }) => {
      setSession(s);
      setLoading(false);
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, s) => {
        setSession(s);
      },
    );

    return () => subscription.unsubscribe();
  }, []);

  const signIn = async (email: string, password: string) => {
    if (DEV_SKIP_AUTH) return;
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw error;
  };

  const signUp = async (email: string, password: string) => {
    if (DEV_SKIP_AUTH) return;
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) throw error;
  };

  const signOut = async () => {
    if (DEV_SKIP_AUTH) return;
    await supabase.auth.signOut();
  };

  return {
    session,
    user: session?.user ?? null,
    loading,
    isAuthenticated: DEV_SKIP_AUTH ? true : !!session,
    signIn,
    signUp,
    signOut,
  };
}
