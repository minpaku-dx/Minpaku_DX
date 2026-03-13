import { View, StyleSheet } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from 'react-native-reanimated';
import { useEffect } from 'react';
import { useTheme } from '@/hooks/useTheme';
import { spacing, borderRadius, shadow } from '@/lib/theme';

function SkeletonCard() {
  const { theme } = useTheme();
  const opacity = useSharedValue(0.3);

  useEffect(() => {
    opacity.value = withRepeat(withTiming(0.6, { duration: 1000 }), -1, true);
  }, []);

  const pulse = useAnimatedStyle(() => ({ opacity: opacity.value }));

  return (
    <View style={[styles.card, shadow.sm, { backgroundColor: theme.card, borderColor: theme.border }]}>
      <Animated.View style={pulse}>
        {/* Top row: avatar + name + time */}
        <View style={styles.topRow}>
          <View style={[styles.avatar, { backgroundColor: theme.border }]} />
          <View style={styles.nameBlock}>
            <View style={[styles.bar, styles.barName, { backgroundColor: theme.border }]} />
            <View style={[styles.bar, styles.barProperty, { backgroundColor: theme.border }]} />
          </View>
          <View style={[styles.bar, styles.barTime, { backgroundColor: theme.border }]} />
        </View>
        {/* Badge */}
        <View style={[styles.badge, { backgroundColor: theme.border }]} />
        {/* Text */}
        <View style={[styles.bar, styles.barFull, { backgroundColor: theme.border }]} />
        <View style={[styles.bar, styles.barMedium, { backgroundColor: theme.border }]} />
        {/* Draft box */}
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
    marginHorizontal: spacing.lg,
    marginBottom: spacing.md,
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
    width: 38,
    height: 38,
    borderRadius: 19,
  },
  nameBlock: {
    flex: 1,
    gap: spacing.xs,
  },
  bar: {
    borderRadius: 4,
  },
  barName: { width: 100, height: 14 },
  barProperty: { width: 70, height: 10 },
  barTime: { width: 36, height: 10 },
  barFull: { width: '100%', height: 12 },
  barMedium: { width: '60%', height: 12 },
  badge: {
    width: 56,
    height: 20,
    borderRadius: borderRadius.xs,
  },
  draftBox: {
    height: 52,
    borderRadius: borderRadius.md,
  },
});
