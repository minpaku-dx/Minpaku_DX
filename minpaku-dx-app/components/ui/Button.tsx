import {
  TouchableOpacity,
  Text,
  ActivityIndicator,
  StyleSheet,
  type ViewStyle,
  type TextStyle,
} from 'react-native';
import { colors, borderRadius, fontSize, fontWeight, spacing } from '@/lib/theme';
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
};

export function Button({
  title,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  style,
  flex,
}: Props) {
  const { theme, isDark } = useTheme();

  const variantStyles: Record<Variant, { bg: string; text: string }> = {
    primary: { bg: colors.primary[500], text: colors.white },
    secondary: { bg: isDark ? colors.dark.elevated : colors.gray[100], text: theme.text },
    danger: { bg: colors.danger[50], text: colors.danger[500] },
    ghost: { bg: 'transparent', text: colors.primary[500] },
  };

  const v = variantStyles[variant];
  const isDisabled = disabled || loading;

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.8}
      style={[
        styles.base,
        { backgroundColor: v.bg, opacity: isDisabled ? 0.5 : 1 },
        flex !== undefined && { flex },
        style,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={v.text} size="small" />
      ) : (
        <Text style={[styles.text, { color: v.text }]}>{title}</Text>
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
    paddingHorizontal: spacing.lg,
  },
  text: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
  },
});
