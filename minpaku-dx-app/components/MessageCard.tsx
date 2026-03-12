import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Badge } from '@/components/ui/Badge';
import { useTheme } from '@/hooks/useTheme';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

type Props = {
  message: MessageCardType;
  onPress: () => void;
};

export function MessageCard({ message, onPress }: Props) {
  const { theme } = useTheme();

  const isProactive = message.type === 'proactive';
  const borderColor = isProactive
    ? message.triggerType === 'pre_checkin'
      ? colors.checkin[500]
      : colors.checkout[500]
    : colors.warning[500];

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[
        styles.card,
        {
          backgroundColor: theme.card,
          borderLeftColor: borderColor,
          shadowColor: colors.gray[900],
        },
      ]}
    >
      {/* Header: property + time */}
      <View style={styles.headerRow}>
        <Text style={[styles.property, { color: theme.textSecondary }]} numberOfLines={1}>
          {message.propertyName}
        </Text>
        <Text style={[styles.time, { color: theme.textTertiary }]}>
          {message.time}
        </Text>
      </View>

      {/* Guest name */}
      <Text style={[styles.guestName, { color: theme.text }]} numberOfLines={1}>
        {message.guestName}
      </Text>

      {/* Badges row */}
      <View style={styles.badgeRow}>
        {isProactive && (
          <Badge
            label={message.triggerLabel ?? ''}
            variant={message.triggerType === 'pre_checkin' ? 'checkin' : 'checkout'}
          />
        )}
        {message.checkIn && (
          <Text style={[styles.dates, { color: theme.textSecondary }]}>
            IN {message.checkIn} → OUT {message.checkOut}
          </Text>
        )}
      </View>

      {/* Guest message preview */}
      {message.guestText ? (
        <Text style={[styles.preview, { color: theme.textSecondary }]} numberOfLines={2}>
          {message.guestText}
        </Text>
      ) : null}

      {/* AI draft preview */}
      {message.draft ? (
        <View style={[styles.draftPreview, { backgroundColor: theme.bg }]}>
          <Text style={[styles.draftText, { color: theme.textSecondary }]} numberOfLines={1}>
            🤖 {message.draft}
          </Text>
        </View>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: borderRadius.lg,
    borderLeftWidth: 3,
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 3,
    elevation: 2,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  property: {
    fontSize: fontSize.bodySm,
    flex: 1,
  },
  time: {
    fontSize: fontSize.caption,
    marginLeft: spacing.sm,
  },
  guestName: {
    fontSize: fontSize.headingMd,
    fontWeight: fontWeight.semibold,
    marginBottom: spacing.xs,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  dates: {
    fontSize: fontSize.bodySm,
  },
  preview: {
    fontSize: fontSize.bodyMd,
    marginBottom: spacing.sm,
  },
  draftPreview: {
    borderRadius: borderRadius.sm,
    padding: spacing.sm,
  },
  draftText: {
    fontSize: fontSize.bodySm,
  },
});
