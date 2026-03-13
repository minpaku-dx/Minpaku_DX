import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  type ViewStyle,
} from 'react-native';
import { colors, borderRadius, fontSize, fontWeight, fontFamily, spacing } from '@/lib/theme';
import { useTheme } from '@/hooks/useTheme';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';

type Props = {
  title: string;
  onPress: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
  flex?: number;
  compact?: boolean;
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  style,
  flex,
  compact = false,
}: Props) {
  const { theme, isDark } = useTheme();

  const variantStyles: Record<Variant, { bg: string; text: string; border?: string }> = {
    primary: { bg: colors.primary[500], text: colors.white },
    secondary: {
      bg: isDark ? colors.dark.elevated : colors.gray[100],
      text: theme.textSecondary,
      border: isDark ? colors.dark.border : colors.gray[200],
    },
    danger: { bg: colors.danger[50], text: colors.danger[500] },
    ghost: { bg: 'transparent', text: colors.primary[500] },
  };

  const v = variantStyles[variant];
  const isDisabled = disabled || loading;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.7}
      style={[
        styles.base,
        compact && styles.compact,
        {
          backgroundColor: v.bg,
          opacity: isDisabled ? 0.45 : 1,
          borderColor: v.border ?? 'transparent',
          borderWidth: v.border ? StyleSheet.hairlineWidth : 0,
        },
        flex !== undefined && { flex },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.text} size="small" />
      ) : (
        <Text style={[styles.text, { color: v.text, fontFamily }]}>{title}</Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  base: {
    height: 48,
    borderRadius: borderRadius.md,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  compact: {
    height: 40,
    paddingHorizontal: spacing.lg,
  },
  text: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
    letterSpacing: 0.1,
  },
});
