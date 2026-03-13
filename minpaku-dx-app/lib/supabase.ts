import { createClient } from '@supabase/supabase-js';
import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const SUPABASE_URL = process.env.EXPO_PUBLIC_SUPABASE_URL ?? '';
const SUPABASE_ANON_KEY = process.env.EXPO_PUBLIC_SUPABASE_ANON_KEY ?? '';

// DEV_SKIP_AUTH: skip Supabase when credentials are not configured
export const DEV_SKIP_AUTH = !SUPABASE_URL;

/**
 * SecureStore adapter for Supabase Auth session persistence.
 * Falls back to no-op on web (uses localStorage automatically).
 */
const secureStoreAdapter =
  Platform.OS !== 'web'
    ? {
        getItem: (key: string) => SecureStore.getItemAsync(key),
        setItem: (key: string, value: string) =>
          SecureStore.setItemAsync(key, value),
        removeItem: (key: string) => SecureStore.deleteItemAsync(key),
      }
    : undefined;

export const supabase = DEV_SKIP_AUTH
  ? (null as unknown as ReturnType<typeof createClient>)
  : createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
      auth: {
        storage: secureStoreAdapter,
        autoRefreshToken: true,
        persistSession: true,
        detectSessionInUrl: false,
      },
    });
