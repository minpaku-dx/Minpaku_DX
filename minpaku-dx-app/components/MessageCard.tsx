import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Badge } from '@/components/ui/Badge';
import { useTheme } from '@/hooks/useTheme';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, shadow, lineHeight } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

type Props = {
  message: MessageCardType;
  onPress: () => void;
};

function formatRelativeTime(timeStr: string): string {
  if (!timeStr) return '';
  try {
    const date = new Date(timeStr);
    const now = new Date();
    const diffMin = Math.floor((now.getTime() - date.getTime()) / 60000);
    if (diffMin < 1) return '\u305F\u3060\u4ECA';
    if (diffMin < 60) return `${diffMin}\u5206\u524D`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}\u6642\u9593\u524D`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay === 1) return '\u6628\u65E5';
    if (diffDay < 7) return `${diffDay}\u65E5\u524D`;
    // Japanese date format: M/D
    return `${date.getMonth() + 1}/${date.getDate()}`;
  } catch {
    return timeStr;
  }
}

function formatDateJP(dateStr: string): string {
  if (!dateStr) return '';
  // "2026-03-15" → "3/15"
  const parts = dateStr.split('-');
  if (parts.length < 3) return dateStr;
  return `${parseInt(parts[1])}/${parseInt(parts[2])}`;
}

export function MessageCard({ message, onPress }: Props) {
  const { theme, isDark } = useTheme();
  const isProactive = message.type === 'proactive';

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.55}
      style={[
        styles.card,
        shadow.sm,
        {
          backgroundColor: theme.card,
          borderColor: isDark ? theme.cardBorder : colors.gray[200],
        },
      ]}
    >
      {/* Row 1: Avatar + Name + Time */}
      <View style={styles.topRow}>
        <View style={[
          styles.avatar,
          { backgroundColor: isProactive ? colors.primary[50] : colors.gray[100] },
        ]}>
          <Text style={[
            styles.avatarText,
            { color: isProactive ? colors.primary[600] : colors.gray[600] },
          ]}>
            {message.guestName.charAt(0).toUpperCase()}
          </Text>
        </View>

        <View style={styles.nameBlock}>
          <Text style={[styles.guestName, { color: theme.text, fontFamily }]} numberOfLines={1}>
            {message.guestName}
          </Text>
          <Text style={[styles.property, { color: theme.textTertiary, fontFamily }]} numberOfLines={1}>
            {message.propertyName}
          </Text>
        </View>

        <Text style={[styles.time, { color: theme.textTertiary, fontFamily }]}>
          {formatRelativeTime(message.time)}
        </Text>
      </View>

      {/* Row 2: Badges + Dates */}
      <View style={styles.metaRow}>
        {isProactive ? (
          <Badge
            label={message.triggerLabel ?? '\u5148\u56DE\u308A'}
            variant={message.triggerType === 'pre_checkin' ? 'checkin' : 'checkout'}
          />
        ) : (
          <Badge label={'\u8FD4\u4FE1\u5F85\u3061'} variant="pending" />
        )}
        {message.checkIn && (
          <View style={styles.dateChip}>
            <Text style={[styles.dateText, { color: theme.textTertiary, fontFamily }]}>
              {formatDateJP(message.checkIn)}\uFF5E{formatDateJP(message.checkOut)}
            </Text>
          </View>
        )}
      </View>

      {/* Row 3: Guest message */}
      {message.guestText ? (
        <Text style={[styles.guestText, { color: theme.textSecondary, fontFamily }]} numberOfLines={2}>
          {message.guestText}
        </Text>
      ) : null}

      {/* Row 4: AI Draft */}
      {message.draft ? (
        <View style={[styles.draftBox, {
          backgroundColor: isDark ? 'rgba(20,184,166,0.06)' : 'rgba(20,184,166,0.04)',
          borderColor: isDark ? 'rgba(20,184,166,0.12)' : 'rgba(20,184,166,0.1)',
        }]}>
          <View style={styles.draftHeader}>
            <View style={styles.draftLabelRow}>
              <Ionicons name="sparkles" size={11} color={colors.ai[500]} />
              <Text style={[styles.draftLabel, { fontFamily }]}>AI\u4E0B\u66F8\u304D</Text>
            </View>
            <Ionicons name="chevron-forward" size={14} color={theme.textTertiary} />
          </View>
          <Text style={[styles.draftText, { color: theme.textSecondary, fontFamily }]} numberOfLines={2}>
            {message.draft}
          </Text>
        </View>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: borderRadius.lg,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    padding: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.md,
  },
  topRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.bold,
  },
  nameBlock: {
    flex: 1,
    gap: 1,
  },
  guestName: {
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.semibold,
  },
  property: {
    fontSize: fontSize.caption,
  },
  time: {
    fontSize: fontSize.caption,
    alignSelf: 'flex-start',
    marginTop: 2,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  dateChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
  },
  dateText: {
    fontSize: fontSize.caption,
  },
  guestText: {
    fontSize: fontSize.bodyMd,
    lineHeight: lineHeight.bodyMd,
  },
  draftBox: {
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    gap: spacing.xs,
    borderWidth: StyleSheet.hairlineWidth,
  },
  draftHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  draftLabelRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  draftLabel: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.bold,
    color: colors.ai[600],
    letterSpacing: 0.3,
  },
  draftText: {
    fontSize: fontSize.bodySm,
    lineHeight: lineHeight.bodySm,
  },
});
