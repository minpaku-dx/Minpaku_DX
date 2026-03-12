import { View, StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';
import { spacing, borderRadius } from '@/lib/theme';

function SkeletonCard() {
  const { theme } = useTheme();
  const opacity = useSharedValue(0.4);

  useEffect(() => {
    opacity.value = withRepeat(withTiming(1.0, { duration: 800 }), -1, true);
  }, []);

  const pulse = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return (
    <View style={[styles.card, { backgroundColor: theme.card }]}>
      <Animated.View style={pulse}>
        {/* Header row */}
        <View style={styles.headerRow}>
          <View style={[styles.bar, styles.barShort, { backgroundColor: theme.border }]} />
          <View style={[styles.bar, styles.barTiny, { backgroundColor: theme.border }]} />
        </View>
        {/* Guest name */}
        <View style={[styles.bar, styles.barMedium, { backgroundColor: theme.border }]} />
        {/* Badge row */}
        <View style={styles.badgeRow}>
          <View style={[styles.badge, { backgroundColor: theme.border }]} />
          <View style={[styles.badge, styles.badgeWide, { backgroundColor: theme.border }]} />
        </View>
        {/* Preview lines */}
        <View style={[styles.bar, styles.barFull, { backgroundColor: theme.border }]} />
        <View style={[styles.bar, styles.barLong, { backgroundColor: theme.border }]} />
        {/* Draft preview */}
        <View style={[styles.draftBox, { backgroundColor: theme.bg }]} />
      </Animated.View>
    </View>
  );
}

export function SkeletonList() {
  return (
    <View style={styles.list}>
      <SkeletonCard />
      <SkeletonCard />
      <SkeletonCard />
    </View>
  );
}

const styles = StyleSheet.create({
  list: {
    paddingTop: spacing.md,
  },
  card: {
    borderRadius: borderRadius.lg,
    borderLeftWidth: 3,
    borderLeftColor: 'transparent',
    padding: spacing.lg,
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: spacing.sm,
  },
  bar: {
    height: 12,
    borderRadius: 6,
  },
  barTiny: { width: 40 },
  barShort: { width: 100 },
  barMedium: { width: 140, height: 16, borderRadius: 8, marginBottom: spacing.sm },
  barFull: { width: '100%', marginBottom: spacing.xs },
  barLong: { width: '75%', marginBottom: spacing.sm },
  badgeRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginBottom: spacing.sm,
  },
  badge: {
    width: 60,
    height: 20,
    borderRadius: 10,
  },
  badgeWide: { width: 120 },
  draftBox: {
    height: 32,
    borderRadius: borderRadius.sm,
  },
});
