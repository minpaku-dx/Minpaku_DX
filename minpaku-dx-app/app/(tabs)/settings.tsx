import { View, Text, TouchableOpacity, Alert, StyleSheet, ScrollView, Switch, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { useNotifications } from '@/hooks/useNotifications';
import { useSettings, useUpdateSettings } from '@/hooks/useSettings';
import { useAppStore } from '@/lib/store';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

type ThemeOption = 'system' | 'light' | 'dark';
type ToneOption = 'friendly' | 'formal' | 'casual';

const themeOptions: { label: string; value: ThemeOption }[] = [
  { label: 'システム', value: 'system' },
  { label: 'ライト', value: 'light' },
  { label: 'ダーク', value: 'dark' },
];

const toneOptions: { label: string; value: ToneOption }[] = [
  { label: 'フレンドリー', value: 'friendly' },
  { label: 'フォーマル', value: 'formal' },
  { label: 'カジュアル', value: 'casual' },
];

export default function SettingsScreen() {
  const { theme, isDark } = useTheme();
  const { user, signOut } = useAuth();
  const { unregister } = useNotifications();
  const themeMode = useAppStore((s) => s.themeMode);
  const setThemeMode = useAppStore((s) => s.setThemeMode);
  const router = useRouter();

  const { data: settings } = useSettings();
  const updateSettings = useUpdateSettings();

  const handleToggle = (key: string, value: boolean) => {
    updateSettings.mutate({ [key]: value });
  };

  const handleToneChange = (tone: ToneOption) => {
    updateSettings.mutate({ ai_tone: tone });
  };

  const handleSignatureChange = (text: string) => {
    updateSettings.mutate({ ai_signature: text });
  };

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

      {/* Notifications */}
      <Text style={[styles.sectionTitle, { color: theme.textSecondary }]}>
        通知設定
      </Text>
      <View style={[styles.card, { backgroundColor: theme.card }]}>
        <View style={styles.switchRow}>
          <Text style={[styles.switchLabel, { color: theme.text }]}>新着メッセージ</Text>
          <Switch
            value={settings?.notify_new_message ?? true}
            onValueChange={(v) => handleToggle('notify_new_message', v)}
            trackColor={{ true: colors.primary[500], false: colors.gray[300] }}
          />
        </View>
        <View style={[styles.divider, { backgroundColor: theme.divider }]} />
        <View style={styles.switchRow}>
          <Text style={[styles.switchLabel, { color: theme.text }]}>プロアクティブ</Text>
          <Switch
            value={settings?.notify_proactive ?? true}
            onValueChange={(v) => handleToggle('notify_proactive', v)}
            trackColor={{ true: colors.primary[500], false: colors.gray[300] }}
          />
        </View>
        <View style={[styles.divider, { backgroundColor: theme.divider }]} />
        <View style={styles.switchRow}>
          <Text style={[styles.switchLabel, { color: theme.text }]}>リマインダー</Text>
          <Switch
            value={settings?.notify_reminder ?? true}
            onValueChange={(v) => handleToggle('notify_reminder', v)}
            trackColor={{ true: colors.primary[500], false: colors.gray[300] }}
          />
        </View>
      </View>

      {/* Beds24 Connection */}
      <Text style={[styles.sectionTitle, { color: theme.textSecondary }]}>
        Beds24接続
      </Text>
      <View style={[styles.card, { backgroundColor: theme.card }]}>
        <View style={styles.aboutRow}>
          <Text style={[styles.switchLabel, { color: theme.text }]}>接続ステータス</Text>
          <Text style={[styles.value, { color: colors.success[500] }]}>接続済み</Text>
        </View>
        <View style={[styles.divider, { backgroundColor: theme.divider }]} />
        <TouchableOpacity
          style={styles.linkRow}
          onPress={() => router.push('/(onboarding)/beds24-token')}
        >
          <Text style={[styles.linkText, { color: colors.primary[500] }]}>
            再接続する
          </Text>
        </TouchableOpacity>
      </View>

      {/* AI Settings */}
      <Text style={[styles.sectionTitle, { color: theme.textSecondary }]}>
        AI設定
      </Text>
      <View style={[styles.card, { backgroundColor: theme.card }]}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>トーン</Text>
        <View style={styles.toneRow}>
          {toneOptions.map((opt) => {
            const active = (settings?.ai_tone ?? 'friendly') === opt.value;
            return (
              <TouchableOpacity
                key={opt.value}
                style={[
                  styles.toneBtn,
                  {
                    backgroundColor: active
                      ? colors.primary[500]
                      : isDark
                        ? colors.dark.elevated
                        : colors.gray[100],
                  },
                ]}
                onPress={() => handleToneChange(opt.value)}
              >
                <Text
                  style={[
                    styles.toneBtnText,
                    { color: active ? colors.white : theme.text },
                  ]}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
        <View style={[styles.divider, { backgroundColor: theme.divider, marginTop: spacing.md }]} />
        <Text style={[styles.label, { color: theme.textSecondary, marginTop: spacing.md }]}>署名</Text>
        <TextInput
          style={[
            styles.textInput,
            {
              color: theme.text,
              backgroundColor: isDark ? colors.dark.elevated : colors.gray[100],
              borderColor: theme.border,
            },
          ]}
          value={settings?.ai_signature ?? '民泊スタッフ一同'}
          onEndEditing={(e) => handleSignatureChange(e.nativeEvent.text)}
          placeholder="署名を入力"
          placeholderTextColor={theme.textTertiary}
        />
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
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  switchLabel: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
  },
  divider: {
    height: 1,
    marginVertical: spacing.sm,
  },
  linkRow: {
    paddingVertical: spacing.sm,
  },
  linkText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
  },
  toneRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    marginTop: spacing.xs,
  },
  toneBtn: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  toneBtnText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
  },
  textInput: {
    fontSize: fontSize.bodyMd,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    borderWidth: 1,
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
