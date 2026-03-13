import { useEffect, useRef } from 'react';
import { Text, StyleSheet, Pressable, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withTiming,
  withDelay,
  runOnJS,
} from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useAppStore } from '@/lib/store';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, lineHeight, shadow } from '@/lib/theme';

const VARIANT_CONFIG = {
  success: { bg: colors.success[600], icon: 'checkmark-circle' as const },
  error: { bg: colors.danger[500], icon: 'alert-circle' as const },
  warning: { bg: colors.warning[600], icon: 'warning' as const },
  info: { bg: colors.primary[600], icon: 'information-circle' as const },
} as const;

function ToastItem({
  id, message, variant,
}: {
  id: string;
  message: string;
  variant: keyof typeof VARIANT_CONFIG;
}) {
  const dismissToast = useAppStore((s) => s.dismissToast);
  const translateY = useSharedValue(-80);
  const opacity = useSharedValue(0);
  const dismissed = useRef(false);
  const config = VARIANT_CONFIG[variant];

  useEffect(() => {
    translateY.value = withTiming(0, { duration: 280 });
    opacity.value = withTiming(1, { duration: 280 });
    const timeout = setTimeout(() => {
      if (!dismissed.current) {
        dismissed.current = true;
        opacity.value = withTiming(0, { duration: 200 });
        translateY.value = withDelay(0, withTiming(-80, { duration: 200 }, () => { runOnJS(dismissToast)(id); }));
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
    translateY.value = withTiming(-80, { duration: 150 }, () => { runOnJS(dismissToast)(id); });
  };

  return (
    <Animated.View style={[styles.toast, shadow.lg, { backgroundColor: config.bg }, animStyle]}>
      <Pressable onPress={handlePress} style={styles.inner}>
        <Ionicons name={config.icon} size={20} color={colors.white} />
        <Text style={styles.message} numberOfLines={2}>{message}</Text>
      </Pressable>
    </Animated.View>
  );
}

export function Toast() {
  const toasts = useAppStore((s) => s.toasts);
  const insets = useSafeAreaInsets();
  if (toasts.length === 0) return null;
  return (
    <Animated.View style={[styles.container, { top: insets.top + spacing.sm }]} pointerEvents="box-none">
      {toasts.map((t) => (
        <ToastItem key={t.id} id={t.id} message={t.message} variant={t.variant} />
      ))}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: { position: 'absolute', left: spacing.lg, right: spacing.lg, zIndex: 9999 },
  toast: { borderRadius: borderRadius.md, marginBottom: spacing.sm },
  inner: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: spacing.lg,
    gap: spacing.md,
  },
  message: {
    color: colors.white,
    fontSize: fontSize.bodyMd,
    fontFamily,
    fontWeight: fontWeight.medium,
    flex: 1,
    lineHeight: lineHeight.bodyMd,
  },
});
