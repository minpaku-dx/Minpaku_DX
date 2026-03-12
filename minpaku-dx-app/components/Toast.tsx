import { useEffect, useRef } from 'react';
import { Text, StyleSheet, Pressable } from 'react-native';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withDelay,
  runOnJS,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAppStore } from '@/lib/store';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

const VARIANT_CONFIG = {
  success: { bg: colors.success[600], emoji: '\u2705' },
  error: { bg: colors.danger[500], emoji: '\u274C' },
  warning: { bg: colors.warning[500], emoji: '\u26A0\uFE0F' },
  info: { bg: colors.primary[500], emoji: '\u2139\uFE0F' },
} as const;

function ToastItem({
  id,
  message,
  variant,
}: {
  id: string;
  message: string;
  variant: keyof typeof VARIANT_CONFIG;
}) {
  const dismissToast = useAppStore((s) => s.dismissToast);
  const translateY = useSharedValue(-100);
  const opacity = useSharedValue(0);
  const dismissed = useRef(false);

  const config = VARIANT_CONFIG[variant];

  useEffect(() => {
    translateY.value = withTiming(0, { duration: 250 });
    opacity.value = withTiming(1, { duration: 250 });

    // Auto-dismiss after 3s
    const timeout = setTimeout(() => {
      if (!dismissed.current) {
        dismissed.current = true;
        opacity.value = withTiming(0, { duration: 200 });
        translateY.value = withDelay(
          0,
          withTiming(-100, { duration: 200 }, () => {
            runOnJS(dismissToast)(id);
          }),
        );
      }
    }, 3000);

    return () => clearTimeout(timeout);
  }, []);

  const animStyle = useAnimatedStyle(() => ({
    transform: [{ translateY: translateY.value }],
    opacity: opacity.value,
  }));

  const handlePress = () => {
    if (dismissed.current) return;
    dismissed.current = true;
    opacity.value = withTiming(0, { duration: 150 });
    translateY.value = withTiming(-100, { duration: 150 }, () => {
      runOnJS(dismissToast)(id);
    });
  };

  return (
    <Animated.View style={[styles.toast, { backgroundColor: config.bg }, animStyle]}>
      <Pressable onPress={handlePress} style={styles.inner}>
        <Text style={styles.emoji}>{config.emoji}</Text>
        <Text style={styles.message} numberOfLines={2}>
          {message}
        </Text>
      </Pressable>
    </Animated.View>
  );
}

export function Toast() {
  const toasts = useAppStore((s) => s.toasts);
  const insets = useSafeAreaInsets();

  if (toasts.length === 0) return null;

  return (
    <Animated.View
      style={[styles.container, { top: insets.top + spacing.sm }]}
      pointerEvents="box-none"
    >
      {toasts.map((t) => (
        <ToastItem key={t.id} id={t.id} message={t.message} variant={t.variant} />
      ))}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    left: spacing.lg,
    right: spacing.lg,
    zIndex: 9999,
  },
  toast: {
    borderRadius: borderRadius.md,
    marginBottom: spacing.sm,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.md,
    paddingHorizontal: spacing.lg,
  },
  emoji: {
    fontSize: fontSize.bodyLg,
    marginRight: spacing.sm,
  },
  message: {
    color: colors.white,
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
    flex: 1,
  },
});
