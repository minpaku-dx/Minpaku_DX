/**
 * Design System — "Calm Professional"
 * Colors, typography, spacing, and shared constants.
 */

export const colors = {
  // Primary
  primary: {
    50: '#EFF6FF',
    100: '#DBEAFE',
    500: '#2563EB',
    600: '#1D4ED8',
    700: '#1E40AF',
  },

  // Semantic
  success: {
    50: '#ECFDF5',
    500: '#059669',
    600: '#047857',
  },
  warning: {
    50: '#FFFBEB',
    200: '#FDE68A',
    500: '#D97706',
  },
  danger: {
    50: '#FEF2F2',
    500: '#DC2626',
  },
  skip: {
    400: '#9CA3AF',
  },

  // Proactive
  checkin: {
    50: '#ECFDF5',
    500: '#059669',
  },
  checkout: {
    50: '#F5F3FF',
    500: '#7C3AED',
  },

  // Neutral
  gray: {
    50: '#F9FAFB',
    100: '#F3F4F6',
    200: '#E5E7EB',
    300: '#D1D5DB',
    400: '#9CA3AF',
    500: '#6B7280',
    700: '#374151',
    900: '#111827',
  },
  white: '#FFFFFF',

  // Dark mode
  dark: {
    bg: '#0F172A',
    card: '#1E293B',
    elevated: '#334155',
    text: '#F1F5F9',
    textSecondary: '#94A3B8',
    border: '#334155',
  },
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  '2xl': 32,
  '3xl': 48,
} as const;

export const borderRadius = {
  sm: 8,
  md: 12,
  lg: 16,
  full: 999,
} as const;

export const fontSize = {
  caption: 11,
  bodySm: 13,
  bodyMd: 15,
  bodyLg: 17,
  headingMd: 17,
  headingLg: 20,
  headingXl: 24,
} as const;

export const lineHeight = {
  caption: 16,
  bodySm: 18,
  bodyMd: 22,
  bodyLg: 24,
  headingMd: 24,
  headingLg: 28,
  headingXl: 32,
} as const;

export const fontWeight = {
  normal: '400' as const,
  medium: '500' as const,
  semibold: '600' as const,
  bold: '700' as const,
};

/** Light theme values */
export const lightTheme = {
  bg: colors.gray[50],
  card: colors.white,
  cardBorder: colors.gray[200],
  text: colors.gray[900],
  textSecondary: colors.gray[500],
  textTertiary: colors.gray[400],
  border: colors.gray[300],
  divider: colors.gray[200],
  tabBar: colors.white,
  tabBarBorder: colors.gray[200],
  tabActive: colors.primary[500],
  tabInactive: colors.gray[400],
  headerBg: 'rgba(249, 250, 251, 0.85)',
};

/** Dark theme values */
export const darkTheme = {
  bg: colors.dark.bg,
  card: colors.dark.card,
  cardBorder: colors.dark.border,
  text: colors.dark.text,
  textSecondary: colors.dark.textSecondary,
  textTertiary: '#64748B',
  border: colors.dark.border,
  divider: colors.dark.border,
  tabBar: colors.dark.card,
  tabBarBorder: colors.dark.border,
  tabActive: colors.primary[500],
  tabInactive: '#64748B',
  headerBg: 'rgba(15, 23, 42, 0.85)',
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
};
