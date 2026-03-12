import { View, Text, StyleSheet } from 'react-native';
import { useTheme } from '@/hooks/useTheme';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';
import type { ThreadMessage } from '@/lib/api';

type Props = {
  message: ThreadMessage;
  isLatest?: boolean;
};

export function ChatBubble({ message, isLatest = false }: Props) {
  const { theme, isDark } = useTheme();
  const isGuest = message.source === 'guest';

  const bubbleBg = isGuest
    ? isDark
      ? colors.dark.elevated
      : colors.gray[100]
    : isDark
      ? colors.primary[700]
      : colors.primary[50];

  const textColor = isGuest ? theme.text : isDark ? colors.white : colors.gray[900];

  const timeStr = message.time?.slice(0, 16).replace('T', ' ') ?? '';

  return (
    <View style={[styles.row, isGuest ? styles.rowLeft : styles.rowRight]}>
      <View
        style={[
          styles.bubble,
          { backgroundColor: bubbleBg },
          isGuest ? styles.bubbleLeft : styles.bubbleRight,
        ]}
      >
        <Text style={[styles.sender, { color: theme.textSecondary }]}>
          {isGuest ? 'ゲスト' : 'ホスト'}
          {isLatest && isGuest && ' 🔴'}
        </Text>
        <Text style={[styles.message, { color: textColor }]}>
          {message.message}
        </Text>
      </View>
      <Text
        style={[
          styles.time,
          { color: theme.textTertiary },
          isGuest ? styles.timeLeft : styles.timeRight,
        ]}
      >
        {timeStr}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    marginBottom: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  rowLeft: {
    alignItems: 'flex-start',
  },
  rowRight: {
    alignItems: 'flex-end',
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: borderRadius.lg,
    padding: spacing.md,
  },
  bubbleLeft: {
    borderTopLeftRadius: spacing.xs,
  },
  bubbleRight: {
    borderTopRightRadius: spacing.xs,
  },
  sender: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.semibold,
    marginBottom: spacing.xs,
  },
  message: {
    fontSize: fontSize.bodyMd,
    lineHeight: 22,
  },
  time: {
    fontSize: fontSize.caption,
    marginTop: spacing.xs,
  },
  timeLeft: {
    marginLeft: spacing.xs,
  },
  timeRight: {
    marginRight: spacing.xs,
  },
});
