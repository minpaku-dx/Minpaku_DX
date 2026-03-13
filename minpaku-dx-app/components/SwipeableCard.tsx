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
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { MessageCard } from '@/components/MessageCard';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

type Props = {
  message: MessageCardType;
  onPress: () => void;
  onSend: () => void;
  onSkip: () => void;
  disabled?: boolean;
};

const SWIPE_THRESHOLD = 0.35;

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
    .onStart(() => { isSwiping.current = true; })
    .onUpdate((e) => { translateX.value = e.translationX; })
    .onEnd((e) => {
      if (e.translationX > threshold) {
        translateX.value = withTiming(width, { duration: 200 }, () => {
          cardHeight.value = withTiming(0, { duration: 200 });
          runOnJS(fireApprove)();
        });
      } else if (e.translationX < -threshold) {
        translateX.value = withTiming(-width, { duration: 200 }, () => {
          cardHeight.value = withTiming(0, { duration: 200 });
          runOnJS(fireSkip)();
        });
      } else {
        translateX.value = withSpring(0, { damping: 20, stiffness: 200 });
      }
      isSwiping.current = false;
    });

  const cardStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }],
    height: cardHeight.value,
    overflow: 'hidden' as const,
  }));

  const approveStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateX.value, [0, threshold], [0, 1], Extrapolation.CLAMP),
  }));

  const skipStyle = useAnimatedStyle(() => ({
    opacity: interpolate(translateX.value, [-threshold, 0], [1, 0], Extrapolation.CLAMP),
  }));

  return (
    <View>
      <Animated.View style={[styles.bgLayer, styles.approveBg, approveStyle]}>
        <View style={styles.bgContent}>
          <Ionicons name="checkmark-circle" size={24} color={colors.white} />
          <Text style={styles.bgLabel}>{'\u9001\u4FE1'}</Text>
        </View>
      </Animated.View>
      <Animated.View style={[styles.bgLayer, styles.skipBg, skipStyle]}>
        <View style={[styles.bgContent, { justifyContent: 'flex-end' }]}>
          <Text style={styles.bgLabel}>{'\u30B9\u30AD\u30C3\u30D7'}</Text>
          <Ionicons name="arrow-forward-circle" size={24} color={colors.white} />
        </View>
      </Animated.View>

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
    bottom: spacing.md,
    left: spacing.lg,
    right: spacing.lg,
    borderRadius: borderRadius.lg,
    justifyContent: 'center',
  },
  approveBg: {
    backgroundColor: colors.success[500],
  },
  skipBg: {
    backgroundColor: colors.gray[400],
  },
  bgContent: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: spacing['2xl'],
    gap: spacing.sm,
  },
  bgLabel: {
    color: colors.white,
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
    fontFamily,
  },
});
