import { View, Text, TouchableOpacity, Alert, StyleSheet, ScrollView } from 'react-native';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { useNotifications } from '@/hooks/useNotifications';
import { useAppStore } from '@/lib/store';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

type ThemeOption = 'system' | 'light' | 'dark';

const themeOptions: { label: string; value: ThemeOption }[] = [
  { label: 'システム', value: 'system' },
  { label: 'ライト', value: 'light' },
  { label: 'ダーク', value: 'dark' },
];

export default function SettingsScreen() {
  const { theme, isDark } = useTheme();
  const { user, signOut } = useAuth();
  const { unregister } = useNotifications();
  const themeMode = useAppStore((s) => s.themeMode);
  const setThemeMode = useAppStore((s) => s.setThemeMode);

  const handleLogout = () => {
    Alert.alert('ログアウト', '本当にログアウトしますか？', [
      { text: 'キャンセル', style: 'cancel' },
      {
        text: 'ログアウト',
        style: 'destructive',
        onPress: async () => {
          await unregister();
          signOut();
        },
      },
    ]);
  };

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: theme.bg }]}
      contentContainerStyle={styles.content}
    >
      {/* Account */}
      <Text style={[styles.sectionTitle, { color: theme.textSecondary }]}>
        アカウント
      </Text>
      <View style={[styles.card, { backgroundColor: theme.card }]}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>メール</Text>
        <Text style={[styles.value, { color: theme.text }]}>
          {user?.email ?? '—'}
        </Text>
      </View>

      {/* Theme */}
      <Text style={[styles.sectionTitle, { color: theme.textSecondary }]}>
        テーマ
      </Text>
      <View style={[styles.card, { backgroundColor: theme.card }]}>
        <View style={styles.themeRow}>
          {themeOptions.map((opt) => {
            const active = themeMode === opt.value;
            return (
              <TouchableOpacity
                key={opt.value}
                style={[
                  styles.themeBtn,
                  {
                    backgroundColor: active
                      ? colors.primary[500]
                      : isDark
                        ? colors.dark.elevated
                        : colors.gray[100],
                  },
                ]}
                onPress={() => setThemeMode(opt.value)}
              >
                <Text
                  style={[
                    styles.themeBtnText,
                    { color: active ? colors.white : theme.text },
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* About */}
      <Text style={[styles.sectionTitle, { color: theme.textSecondary }]}>
        アプリ情報
      </Text>
      <View style={[styles.card, { backgroundColor: theme.card }]}>
        <View style={styles.aboutRow}>
          <Text style={[styles.label, { color: theme.textSecondary }]}>バージョン</Text>
          <Text style={[styles.value, { color: theme.text }]}>1.0.0</Text>
        </View>
      </View>

      {/* Logout */}
      <TouchableOpacity
        style={[styles.logoutBtn, { backgroundColor: colors.danger[50] }]}
        onPress={handleLogout}
      >
        <Text style={styles.logoutText}>ログアウト</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    padding: spacing.lg,
    paddingBottom: spacing['3xl'],
  },
  sectionTitle: {
    fontSize: fontSize.bodySm,
    fontWeight: fontWeight.semibold,
    textTransform: 'uppercase',
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
    marginLeft: spacing.xs,
  },
  card: {
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
  },
  label: {
    fontSize: fontSize.bodySm,
    marginBottom: spacing.xs,
  },
  value: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
  },
  themeRow: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
  themeBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  themeBtnText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
  },
  aboutRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logoutBtn: {
    marginTop: spacing['2xl'],
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    alignItems: 'center',
  },
  logoutText: {
    color: colors.danger[500],
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
  },
});
