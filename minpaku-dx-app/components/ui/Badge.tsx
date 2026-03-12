import { View, Text, StyleSheet } from 'react-native';
import { colors, borderRadius, fontSize, fontWeight, spacing } from '@/lib/theme';

type BadgeVariant = 'pending' | 'sent' | 'skipped' | 'checkin' | 'checkout' | 'count';

type Props = {
  label: string;
  variant?: BadgeVariant;
};

const variantColors: Record<BadgeVariant, { bg: string; text: string }> = {
  pending: { bg: colors.warning[50], text: colors.warning[500] },
  sent: { bg: colors.success[50], text: colors.success[500] },
  skipped: { bg: colors.gray[100], text: colors.skip[400] },
  checkin: { bg: colors.checkin[50], text: colors.checkin[500] },
  checkout: { bg: colors.checkout[50], text: colors.checkout[500] },
  count: { bg: colors.danger[500], text: colors.white },
};

export function Badge({ label, variant = 'pending' }: Props) {
  const c = variantColors[variant];

  return (
    <View style={[styles.badge, { backgroundColor: c.bg }]}>
      <Text style={[styles.text, { color: c.text }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    borderRadius: borderRadius.full,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.semibold,
  },
});
