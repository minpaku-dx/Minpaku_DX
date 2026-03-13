/**
 * Design System — "静寂な自信" (Quiet Confidence)
 * Japanese-first typography, premium information density.
 */

import { Platform } from 'react-native';

// Japanese-optimized font stack
export const fontFamily = Platform.select({
  web: '"Noto Sans JP", "Inter", -apple-system, BlinkMacSystemFont, sans-serif',
  ios: 'System',
  android: 'Roboto',
  default: 'System',
});

export const colors = {
  // Primary — 藍色 (deep indigo, a traditional Japanese color)
  primary: {
    50: '#EEF2FF',
    100: '#E0E7FF',
    200: '#C7D2FE',
    400: '#818CF8',
    500: '#6366F1',
    600: '#4F46E5',
    700: '#4338CA',
  },

  // Semantic
  success: {
    50: '#F0FDF4',
    100: '#DCFCE7',
    500: '#22C55E',
    600: '#16A34A',
  },
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    500: '#F59E0B',
    600: '#D97706',
  },
  danger: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    500: '#EF4444',
    600: '#DC2626',
  },

  // AI — 翡翠 (jade/teal)
  ai: {
    50: '#F0FDFA',
    100: '#CCFBF1',
    500: '#14B8A6',
    600: '#0D9488',
  },

  // Proactive
  checkin: { 50: '#F0FDF4', 500: '#22C55E' },
  checkout: { 50: '#FAF5FF', 500: '#A855F7' },

  // Neutral — 墨色 (sumi-iro, ink-based)
  gray: {
    50: '#FAFAFA',
    100: '#F5F5F5',
    200: '#E5E5E5',
    300: '#D4D4D4',
    400: '#A3A3A3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
    950: '#0A0A0A',
  },
  white: '#FFFFFF',

  // Dark
  dark: {
    bg: '#0A0A0A',
    card: '#171717',
    elevated: '#262626',
    text: '#FAFAFA',
    textSecondary: '#A3A3A3',
    border: '#262626',
  },
} as const;

// Japanese text needs more generous spacing
export const spacing = {
  '2xs': 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  '3xl': 32,
  '4xl': 48,
} as const;

export const borderRadius = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 14,
  xl: 18,
  '2xl': 24,
  full: 999,
} as const;

// Japanese characters are denser; slightly smaller sizes work
export const fontSize = {
  xs: 10,
  caption: 11,
  captionMd: 12,
  bodySm: 13,
  bodyMd: 14,
  bodyLg: 15,
  headingSm: 16,
  headingMd: 18,
  headingLg: 20,
  headingXl: 24,
  display: 28,
} as const;

// Japanese needs taller line height (1.7–1.8x) for readability
export const lineHeight = {
  caption: 16,
  bodySm: 20,
  bodyMd: 22,
  bodyLg: 24,
  headingSm: 24,
  headingMd: 28,
  headingLg: 32,
  headingXl: 36,
} as const;

export const fontWeight = {
  normal: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
};

export const shadow = {
  sm: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.04,
    shadowRadius: 2,
    elevation: 1,
  },
  md: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
  },
  lg: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
  },
} as const;

export const lightTheme = {
  bg: '#FAFAFA',
  card: colors.white,
  cardBorder: colors.gray[200],
  text: colors.gray[900],
  textSecondary: colors.gray[600],
  textTertiary: colors.gray[400],
  border: colors.gray[200],
  divider: colors.gray[100],
  tabBar: colors.white,
  tabBarBorder: colors.gray[200],
  tabActive: colors.gray[900],
  tabInactive: colors.gray[400],
  headerBg: 'rgba(250, 250, 250, 0.95)',
  inputBg: colors.gray[50],
};

export const darkTheme = {
  bg: colors.dark.bg,
  card: colors.dark.card,
  cardBorder: colors.dark.border,
  text: colors.dark.text,
  textSecondary: colors.dark.textSecondary,
  textTertiary: '#525252',
  border: colors.dark.border,
  divider: 'rgba(255,255,255,0.06)',
  tabBar: colors.dark.card,
  tabBarBorder: colors.dark.border,
  tabActive: colors.dark.text,
  tabInactive: '#525252',
  headerBg: 'rgba(10, 10, 10, 0.95)',
  inputBg: colors.dark.elevated,
};

export type Theme = {
  bg: string;
  card: string;
  cardBorder: string;
  text: string;
  textSecondary: string;
  textTertiary: string;
  border: string;
  divider: string;
  tabBar: string;
  tabBarBorder: string;
  tabActive: string;
  tabInactive: string;
  headerBg: string;
  inputBg: string;
};
