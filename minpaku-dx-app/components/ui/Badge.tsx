import { View, Text, StyleSheet } from 'react-native';
import { colors, borderRadius, fontSize, fontWeight, fontFamily, spacing } from '@/lib/theme';

type BadgeVariant = 'pending' | 'sent' | 'skipped' | 'checkin' | 'checkout' | 'count' | 'reply' | 'proactive' | 'ai';

type Props = {
  label: string;
  variant?: BadgeVariant;
};

const variantColors: Record<BadgeVariant, { bg: string; text: string }> = {
  pending: { bg: colors.warning[100], text: colors.warning[600] },
  sent: { bg: colors.success[100], text: colors.success[600] },
  skipped: { bg: colors.gray[100], text: colors.gray[500] },
  checkin: { bg: colors.success[50], text: colors.success[600] },
  checkout: { bg: colors.checkout[50], text: colors.checkout[500] },
  count: { bg: colors.danger[500], text: colors.white },
  reply: { bg: colors.warning[100], text: colors.warning[600] },
  proactive: { bg: colors.primary[50], text: colors.primary[600] },
  ai: { bg: colors.ai[50], text: colors.ai[600] },
};

export function Badge({ label, variant = 'pending' }: Props) {
  const c = variantColors[variant];

  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.text, { color: c.text, fontFamily }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: borderRadius.xs,
    paddingHorizontal: spacing.sm,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.semibold,
    letterSpacing: 0.2,
  },
});
