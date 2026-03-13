import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/hooks/useTheme';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, lineHeight } from '@/lib/theme';
import type { ThreadMessage } from '@/lib/api';

type Props = {
  message: ThreadMessage;
  isLatest?: boolean;
};

export function ChatBubble({ message, isLatest = false }: Props) {
  const { theme, isDark } = useTheme();
  const isGuest = message.source === 'guest';
  const isAI = !isGuest && message.aiGenerated === true;

  const bubbleBg = isGuest
    ? isDark ? colors.dark.elevated : colors.gray[100]
    : isAI
      ? isDark ? 'rgba(20, 184, 166, 0.12)' : colors.ai[50]
      : isDark ? 'rgba(99, 102, 241, 0.12)' : colors.primary[50];

  const textColor = isGuest
    ? theme.text
    : isDark ? colors.gray[200] : colors.gray[800];

  // Japanese time format: HH:MM
  const timeStr = message.time?.slice(11, 16) ?? '';

  return (
    <View style={[styles.row, isGuest ? styles.rowLeft : styles.rowRight]}>
      {/* Sender */}
      <View style={[styles.senderRow, isGuest ? styles.senderLeft : styles.senderRight]}>
        {isAI && (
          <View style={[styles.aiTag, { backgroundColor: isDark ? 'rgba(20,184,166,0.15)' : colors.ai[50] }]}>
            <Ionicons name="sparkles" size={9} color={colors.ai[500]} />
            <Text style={[styles.aiTagText, { fontFamily }]}>AI</Text>
          </View>
        )}
        {!isGuest && !isAI && (
          <Text style={[styles.senderLabel, { color: theme.textTertiary, fontFamily }]}>
            {'\u30AA\u30FC\u30CA\u30FC'}
          </Text>
        )}
        {isGuest && (
          <View style={styles.guestSender}>
            {isLatest && <View style={[styles.unreadDot, { backgroundColor: colors.primary[500] }]} />}
            <Text style={[styles.senderLabel, { color: theme.textTertiary, fontFamily }]}>
              {'\u30B2\u30B9\u30C8'}
            </Text>
          </View>
        )}
      </View>

      <View
        style={[
          styles.bubble,
          { backgroundColor: bubbleBg },
          isGuest ? styles.bubbleLeft : styles.bubbleRight,
          isAI && { borderWidth: StyleSheet.hairlineWidth, borderColor: 'rgba(20,184,166,0.15)' },
        ]}
      >
        <Text style={[styles.message, { color: textColor, fontFamily }]}>
          {message.message}
        </Text>
      </View>

      <Text style={[styles.time, { color: theme.textTertiary }, isGuest ? styles.timeLeft : styles.timeRight]}>
        {timeStr}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    marginBottom: spacing.xl,
    paddingHorizontal: spacing.lg,
  },
  rowLeft: { alignItems: 'flex-start' },
  rowRight: { alignItems: 'flex-end' },
  senderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: spacing.xs,
    gap: spacing.xs,
  },
  senderLeft: { marginLeft: spacing.xs },
  senderRight: { marginRight: spacing.xs },
  senderLabel: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.medium,
  },
  guestSender: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  unreadDot: {
    width: 5,
    height: 5,
    borderRadius: 3,
  },
  aiTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: borderRadius.xs,
  },
  aiTagText: {
    fontSize: 9,
    fontWeight: fontWeight.bold,
    color: colors.ai[600],
    letterSpacing: 0.5,
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: borderRadius.xl,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  bubbleLeft: { borderTopLeftRadius: borderRadius.xs },
  bubbleRight: { borderTopRightRadius: borderRadius.xs },
  message: {
    fontSize: fontSize.bodyMd,
    lineHeight: lineHeight.bodyMd,
  },
  time: {
    fontSize: fontSize.xs,
    marginTop: 3,
  },
  timeLeft: { marginLeft: spacing.xs },
  timeRight: { marginRight: spacing.xs },
});
