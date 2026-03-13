import { useEffect, useCallback } from 'react';
import { ActivityIndicator, View, StyleSheet, Platform, Text } from 'react-native';
import { Slot, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import * as Font from 'expo-font';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { useAppStore } from '@/lib/store';
import { Toast } from '@/components/Toast';
import { api } from '@/lib/api';
import { colors } from '@/lib/theme';
import { DEV_SKIP_AUTH } from '@/lib/supabase';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

/**
 * Load Noto Sans JP for Japanese typography.
 * On web: inject Google Fonts CSS. On native: use system fonts.
 */
function useJapaneseFont() {
  useEffect(() => {
    if (Platform.OS === 'web') {
      // Inject Google Fonts for web
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap';
      document.head.appendChild(link);

      // Apply font to body
      const style = document.createElement('style');
      style.textContent = `
        * { font-family: 'Noto Sans JP', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }
        body { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
      `;
      document.head.appendChild(style);
    }
  }, []);
}

function AuthGate() {
  const { isAuthenticated, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  const { theme, isDark } = useTheme();
  const onboarded = useAppStore((s) => s.onboarded);
  const setOnboarded = useAppStore((s) => s.setOnboarded);

  useJapaneseFont();

  useEffect(() => {
    if (loading) return;

    const inAuthGroup = segments[0] === '(auth)';
    const inOnboardingGroup = segments[0] === '(onboarding)';

    if (DEV_SKIP_AUTH) {
      if (!onboarded) setOnboarded(true);
      if (inAuthGroup || inOnboardingGroup) {
        router.replace('/(tabs)');
      }
      return;
    }

    if (!isAuthenticated && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (isAuthenticated && inAuthGroup) {
      if (!onboarded) {
        api.getMe().then((data) => {
          if (data.properties && data.properties.length > 0) {
            setOnboarded(true);
            router.replace('/(tabs)');
          } else {
            router.replace('/(onboarding)/beds24-token');
          }
        }).catch(() => {
          router.replace('/(tabs)');
        });
      } else {
        router.replace('/(tabs)');
      }
    } else if (isAuthenticated && !onboarded && !inOnboardingGroup) {
      api.getMe().then((data) => {
        if (data.properties && data.properties.length > 0) {
          setOnboarded(true);
        } else {
          router.replace('/(onboarding)/beds24-token');
        }
      }).catch(() => {
        setOnboarded(true);
      });
    }
  }, [isAuthenticated, loading, segments]);

  if (loading) {
    return (
      <View style={[styles.loading, { backgroundColor: theme.bg }]}>
        <ActivityIndicator size="large" color={colors.primary[500]} />
      </View>
    );
  }

  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Slot />
      <Toast />
    </>
  );
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={styles.flex}>
      <SafeAreaProvider>
        <QueryClientProvider client={queryClient}>
          <AuthGate />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
