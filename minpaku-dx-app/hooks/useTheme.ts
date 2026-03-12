import { useColorScheme } from 'react-native';
import { lightTheme, darkTheme, type Theme } from '@/lib/theme';
import { useAppStore } from '@/lib/store';

/**
 * Returns the current theme based on user preference and system setting.
 */
export function useTheme(): { theme: Theme; isDark: boolean } {
  const systemScheme = useColorScheme();
  const themeMode = useAppStore((s) => s.themeMode);

  const isDark =
    themeMode === 'dark' || (themeMode === 'system' && systemScheme === 'dark');

  return {
    theme: isDark ? darkTheme : lightTheme,
    isDark,
  };
}
