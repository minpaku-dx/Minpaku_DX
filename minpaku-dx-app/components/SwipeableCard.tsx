import { useRef } from 'react';
import { Text, StyleSheet, View, useWindowDimensions } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
  runOnJS,
  interpolate,
  Extrapolation,
} from 'react-native-reanimated';
import * as Haptics from 'expo-haptics';
import { MessageCard } from '@/components/MessageCard';
import { colors, spacing, borderRadius } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

type Props = {
  message: MessageCardType;
  onPress: () => void;
  onSend: () => void;
  onSkip: () => void;
  disabled?: boolean;
};

const SWIPE_THRESHOLD = 0.4; // 40% of screen width

export function SwipeableCard({ message, onPress, onSend, onSkip, disabled }: Props) {
  const { width } = useWindowDimensions();
  const threshold = width * SWIPE_THRESHOLD;

  const translateX = useSharedValue(0);
  const cardHeight = useSharedValue<number | undefined>(undefined);
  const isSwiping = useRef(false);

  const fireApprove = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    onSend();
  };

  const fireSkip = () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    onSkip();
  };

  const pan = Gesture.Pan()
    .activeOffsetX([-15, 15])
    .failOffsetY([-10, 10])
    .enabled(!disabled)
    .onStart(() => {
      isSwiping.current = true;
    })
    .onUpdate((e) => {
      translateX.value = e.translationX;
    })
    .onEnd((e) => {
      if (e.translationX > threshold) {
        // Approve — slide off right
        translateX.value = withTiming(width, { duration: 200 }, () => {
          cardHeight.value = withTiming(0, { duration: 200 });
          runOnJS(fireApprove)();
        });
      } else if (e.translationX < -threshold) {
        // Skip — slide off left
        translateX.value = withTiming(-width, { duration: 200 }, () => {
          cardHeight.value = withTiming(0, { duration: 200 });
          runOnJS(fireSkip)();
        });
      } else {
        // Spring back
        translateX.value = withSpring(0, { damping: 20, stiffness: 200 });
      }
      isSwiping.current = false;
    });

  const cardStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    height: cardHeight.value,
    overflow: 'hidden' as const,
  }));

  // Right swipe background (approve — green)
  const approveStyle = useAnimatedStyle(() => ({
    opacity: interpolate(
      translateX.value,
      [0, threshold],
      [0, 1],
      Extrapolation.CLAMP,
    ),
  }));

  // Left swipe background (skip — gray)
  const skipStyle = useAnimatedStyle(() => ({
    opacity: interpolate(
      translateX.value,
      [-threshold, 0],
      [1, 0],
      Extrapolation.CLAMP,
    ),
  }));

  return (
    <View>
      {/* Background layers */}
      <Animated.View style={[styles.bgLayer, styles.approveBg, approveStyle]}>
        <Text style={styles.bgIcon}>✓</Text>
        <Text style={styles.bgLabel}>送信</Text>
      </Animated.View>
      <Animated.View style={[styles.bgLayer, styles.skipBg, skipStyle]}>
        <Text style={styles.bgLabel}>スキップ</Text>
        <Text style={styles.bgIcon}>→</Text>
      </Animated.View>

      {/* Swipeable card */}
      <GestureDetector gesture={pan}>
        <Animated.View style={cardStyle}>
          <MessageCard message={message} onPress={onPress} />
        </Animated.View>
      </GestureDetector>
    </View>
  );
}

const styles = StyleSheet.create({
  bgLayer: {
    position: 'absolute',
    top: 0,
    bottom: 0,
    left: spacing.lg,
    right: spacing.lg,
    borderRadius: borderRadius.lg,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing.xl,
  },
  approveBg: {
    backgroundColor: colors.success[500],
    justifyContent: 'flex-start',
  },
  skipBg: {
    backgroundColor: colors.skip[400],
    justifyContent: 'flex-end',
  },
  bgIcon: {
    color: colors.white,
    fontSize: 24,
    fontWeight: '700',
  },
  bgLabel: {
    color: colors.white,
    fontSize: 16,
    fontWeight: '600',
    marginHorizontal: spacing.sm,
  },
});
