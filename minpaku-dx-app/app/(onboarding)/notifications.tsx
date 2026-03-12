import { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@/hooks/useTheme';
import { useNotifications } from '@/hooks/useNotifications';
import { useAppStore } from '@/lib/store';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

export default function NotificationsScreen() {
  const { theme } = useTheme();
  const router = useRouter();
  const { requestPermission } = useNotifications();
  const setOnboarded = useAppStore((s) => s.setOnboarded);
  const showToast = useAppStore((s) => s.showToast);

  const [permissionGranted, setPermissionGranted] = useState<boolean | null>(null);

  const handleRequestPermission = async () => {
    try {
      await requestPermission();
      setPermissionGranted(true);
      showToast('通知を有効にしました', 'success');
    } catch {
      setPermissionGranted(false);
    }
  };

  const handleComplete = () => {
    setOnboarded(true);
    router.replace('/(tabs)');
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <View style={styles.content}>
        <Text style={[styles.heading, { color: theme.text }]}>
          プッシュ通知
        </Text>
        <Text style={[styles.description, { color: theme.textSecondary }]}>
          ゲストからのメッセージをリアルタイムで受け取るために、プッシュ通知を有効にしてください。
        </Text>

        {permissionGranted === null ? (
          <TouchableOpacity
            style={styles.permissionButton}
            onPress={handleRequestPermission}
          >
            <Text style={styles.permissionButtonText}>通知を有効にする</Text>
          </TouchableOpacity>
        ) : permissionGranted ? (
          <View style={[styles.statusCard, { backgroundColor: colors.success[50] }]}>
            <Text style={[styles.statusText, { color: colors.success[500] }]}>
              通知が有効になりました
            </Text>
          </View>
        ) : (
          <View style={[styles.statusCard, { backgroundColor: colors.warning[50] }]}>
            <Text style={[styles.statusText, { color: colors.warning[500] }]}>
              通知が無効です。設定アプリから後で有効にできます。
            </Text>
          </View>
        )}
      </View>

      <View style={styles.footer}>
        <TouchableOpacity style={styles.button} onPress={handleComplete}>
          <Text style={styles.buttonText}>完了</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: spacing.xl,
    justifyContent: 'center',
  },
  heading: {
    fontSize: fontSize.headingXl,
    fontWeight: fontWeight.bold,
    marginBottom: spacing.md,
  },
  description: {
    fontSize: fontSize.bodyMd,
    lineHeight: 22,
    marginBottom: spacing['2xl'],
  },
  permissionButton: {
    backgroundColor: colors.primary[500],
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    alignItems: 'center',
  },
  permissionButtonText: {
    color: colors.white,
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
  },
  statusCard: {
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    alignItems: 'center',
  },
  statusText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
    textAlign: 'center',
  },
  footer: {
    padding: spacing.xl,
  },
  button: {
    backgroundColor: colors.primary[500],
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    alignItems: 'center',
  },
  buttonText: {
    color: colors.white,
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
  },
});
