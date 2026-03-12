import { useEffect } from 'react';
import { ActivityIndicator, View, StyleSheet } from 'react-native';
import { Slot, useRouter, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { useAppStore } from '@/lib/store';
import { Toast } from '@/components/Toast';
import { api } from '@/lib/api';
import { colors } from '@/lib/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 2,
    },
  },
});

function AuthGate() {
  const { isAuthenticated, loading } = useAuth();
  const segments = useSegments();
  const router = useRouter();
  const { theme, isDark } = useTheme();
  const onboarded = useAppStore((s) => s.onboarded);
  const setOnboarded = useAppStore((s) => s.setOnboarded);

  useEffect(() => {
    if (loading) return;

    const inAuthGroup = segments[0] === '(auth)';
    const inOnboardingGroup = segments[0] === '(onboarding)';

    if (!isAuthenticated && !inAuthGroup) {
      router.replace('/(auth)/login');
    } else if (isAuthenticated && inAuthGroup) {
      // Check if user has properties (onboarding complete)
      if (!onboarded) {
        api.getMe().then((data) => {
          if (data.properties && data.properties.length > 0) {
            setOnboarded(true);
            router.replace('/(tabs)');
          } else {
            router.replace('/(onboarding)/beds24-token');
          }
        }).catch(() => {
          // If API fails, proceed to tabs
          router.replace('/(tabs)');
        });
      } else {
        router.replace('/(tabs)');
      }
    } else if (isAuthenticated && !onboarded && !inOnboardingGroup) {
      // Check properties on first load
      api.getMe().then((data) => {
        if (data.properties && data.properties.length > 0) {
          setOnboarded(true);
        } else {
          router.replace('/(onboarding)/beds24-token');
        }
      }).catch(() => {
        setOnboarded(true); // Assume onboarded if API fails
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
