import { View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/hooks/useTheme';
import { spacing, fontSize, fontWeight, fontFamily, lineHeight, colors } from '@/lib/theme';
import type { ReactNode } from 'react';

type Props = {
  icon?: string;
  ionicon?: keyof typeof Ionicons.glyphMap;
  illustration?: ReactNode;
  title: string;
  subtitle?: string;
};

export function EmptyState({ icon, ionicon = 'mail-open-outline', illustration, title, subtitle }: Props) {
  const { theme, isDark } = useTheme();

  return (
    <View style={styles.container}>
      {illustration ? (
        <View style={styles.illustrationWrap}>{illustration}</View>
      ) : (
        <View style={[styles.iconCircle, { backgroundColor: isDark ? colors.dark.elevated : colors.gray[100] }]}>
          {icon ? (
            <Text style={styles.emoji}>{icon}</Text>
          ) : (
            <Ionicons name={ionicon} size={28} color={theme.textTertiary} />
          )}
        </View>
      )}
      <Text style={[styles.title, { color: theme.text, fontFamily }]}>{title}</Text>
      {subtitle && (
        <Text style={[styles.subtitle, { color: theme.textTertiary, fontFamily }]}>
          {subtitle}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: spacing['3xl'],
    paddingTop: spacing['4xl'],
  },
  illustrationWrap: {
    marginBottom: spacing['2xl'],
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: spacing['2xl'],
  },
  emoji: {
    fontSize: 28,
  },
  title: {
    fontSize: fontSize.headingSm,
    fontWeight: fontWeight.semibold,
    textAlign: 'center',
    marginBottom: spacing.sm,
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: fontSize.bodyMd,
    textAlign: 'center',
    lineHeight: lineHeight.bodyMd,
  },
});
