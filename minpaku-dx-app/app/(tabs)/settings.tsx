import { View, Text, TouchableOpacity, Alert, StyleSheet, ScrollView, Switch, TextInput } from 'react-native';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { useNotifications } from '@/hooks/useNotifications';
import { useSettings, useUpdateSettings } from '@/hooks/useSettings';
import { useAppStore } from '@/lib/store';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, shadow } from '@/lib/theme';

type ThemeOption = 'system' | 'light' | 'dark';
type ToneOption = 'friendly' | 'formal' | 'casual';

const themeOptions: { label: string; value: ThemeOption; icon: keyof typeof Ionicons.glyphMap }[] = [
  { label: '\u81EA\u52D5', value: 'system', icon: 'phone-portrait-outline' },
  { label: '\u30E9\u30A4\u30C8', value: 'light', icon: 'sunny-outline' },
  { label: '\u30C0\u30FC\u30AF', value: 'dark', icon: 'moon-outline' },
];

const toneOptions: { label: string; value: ToneOption }[] = [
  { label: '\u30D5\u30EC\u30F3\u30C9\u30EA\u30FC', value: 'friendly' },
  { label: '\u30D5\u30A9\u30FC\u30DE\u30EB', value: 'formal' },
  { label: '\u30AB\u30B8\u30E5\u30A2\u30EB', value: 'casual' },
];

function SectionHeader({ title }: { title: string }) {
  const { theme } = useTheme();
  return <Text style={[styles.sectionTitle, { color: theme.textTertiary, fontFamily }]}>{title}</Text>;
}

function Divider() {
  const { theme } = useTheme();
  return <View style={[styles.divider, { backgroundColor: theme.divider }]} />;
}

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T }[];
  value: T;
  onChange: (v: T) => void;
}) {
  const { theme, isDark } = useTheme();
  return (
    <View style={[styles.segmented, { backgroundColor: isDark ? colors.dark.elevated : colors.gray[100] }]}>
      {options.map((opt) => {
        const active = value === opt.value;
        return (
          <TouchableOpacity
            key={opt.value}
            style={[
              styles.segmentItem,
              active && [styles.segmentItemActive, { backgroundColor: theme.card }, shadow.sm],
            ]}
            onPress={() => onChange(opt.value)}
            activeOpacity={0.7}
          >
            <Text
              style={[
                styles.segmentText,
                { color: active ? theme.text : theme.textTertiary, fontFamily },
                active && { fontWeight: fontWeight.semibold },
              ]}
            >
              {opt.label}
            </Text>
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

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

  const cardStyle = [styles.card, shadow.sm, { backgroundColor: theme.card, borderColor: isDark ? theme.cardBorder : colors.gray[200] }];

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.bg }]} contentContainerStyle={styles.content}>
      {/* Account */}
      <SectionHeader title={'\u30A2\u30AB\u30A6\u30F3\u30C8'} />
      <View style={cardStyle}>
        <View style={styles.row}>
          <View style={styles.rowIcon}>
            <Ionicons name="person-outline" size={18} color={theme.textSecondary} />
          </View>
          <Text style={[styles.rowLabel, { color: theme.text, fontFamily }]}>{'\u30E1\u30FC\u30EB'}</Text>
          <Text style={[styles.rowValue, { color: theme.textSecondary, fontFamily }]} numberOfLines={1}>
            {user?.email ?? '\u2014'}
          </Text>
        </View>
      </View>

      {/* Notifications */}
      <SectionHeader title={'\u901A\u77E5'} />
      <View style={cardStyle}>
        {[
          { key: 'notify_new_message', label: '\u65B0\u7740\u30E1\u30C3\u30BB\u30FC\u30B8', icon: 'mail-outline' as const },
          { key: 'notify_proactive', label: '\u5148\u56DE\u308A\u30E1\u30C3\u30BB\u30FC\u30B8', icon: 'flash-outline' as const },
          { key: 'notify_reminder', label: '\u30EA\u30DE\u30A4\u30F3\u30C0\u30FC', icon: 'alarm-outline' as const },
        ].map((item, i) => (
          <View key={item.key}>
            {i > 0 && <Divider />}
            <View style={styles.switchRow}>
              <Ionicons name={item.icon} size={18} color={theme.textSecondary} style={styles.switchIcon} />
              <Text style={[styles.switchLabel, { color: theme.text, fontFamily }]}>{item.label}</Text>
              <Switch
                value={(settings as any)?.[item.key] ?? true}
                onValueChange={(v) => handleToggle(item.key, v)}
                trackColor={{ true: colors.primary[500], false: colors.gray[300] }}
              />
            </View>
          </View>
        ))}
      </View>

      {/* Beds24 */}
      <SectionHeader title={'Beds24'} />
      <View style={cardStyle}>
        <View style={styles.row}>
          <View style={styles.rowIcon}>
            <Ionicons name="link-outline" size={18} color={theme.textSecondary} />
          </View>
          <Text style={[styles.rowLabel, { color: theme.text, fontFamily }]}>{'\u30B9\u30C6\u30FC\u30BF\u30B9'}</Text>
          <View style={styles.statusDot}>
            <View style={[styles.dot, { backgroundColor: colors.success[500] }]} />
            <Text style={[styles.statusText, { color: colors.success[500], fontFamily }]}>{'\u63A5\u7D9A\u6E08\u307F'}</Text>
          </View>
        </View>
        <Divider />
        <TouchableOpacity
          style={styles.linkRow}
          onPress={() => router.push('/(onboarding)/beds24-token')}
          activeOpacity={0.6}
        >
          <Ionicons name="refresh-outline" size={18} color={theme.tabActive} style={styles.switchIcon} />
          <Text style={[styles.linkText, { color: theme.tabActive, fontFamily }]}>{'\u518D\u63A5\u7D9A\u3059\u308B'}</Text>
          <Ionicons name="chevron-forward" size={16} color={theme.textTertiary} />
        </TouchableOpacity>
      </View>

      {/* AI */}
      <SectionHeader title={'AI\u8A2D\u5B9A'} />
      <View style={cardStyle}>
        <Text style={[styles.fieldLabel, { color: theme.textSecondary, fontFamily }]}>{'\u30C8\u30FC\u30F3'}</Text>
        <SegmentedControl
          options={toneOptions}
          value={(settings?.ai_tone as ToneOption) ?? 'friendly'}
          onChange={(v) => updateSettings.mutate({ ai_tone: v })}
        />
        <Divider />
        <Text style={[styles.fieldLabel, { color: theme.textSecondary, fontFamily }]}>{'\u7F72\u540D'}</Text>
        <TextInput
          style={[styles.textInput, { color: theme.text, backgroundColor: theme.inputBg, borderColor: theme.border, fontFamily }]}
          value={settings?.ai_signature ?? '\u6C11\u6CCA\u30B9\u30BF\u30C3\u30D5\u4E00\u540C'}
          onEndEditing={(e) => updateSettings.mutate({ ai_signature: e.nativeEvent.text })}
          placeholder={'\u7F72\u540D\u3092\u5165\u529B'}
          placeholderTextColor={theme.textTertiary}
        />
      </View>

      {/* Theme */}
      <SectionHeader title={'\u30C6\u30FC\u30DE'} />
      <View style={cardStyle}>
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
                      ? isDark ? colors.primary[700] : colors.primary[50]
                      : isDark ? colors.dark.elevated : colors.gray[50],
                    borderColor: active ? colors.primary[500] : 'transparent',
                  },
                ]}
                onPress={() => setThemeMode(opt.value)}
                activeOpacity={0.7}
              >
                <Ionicons
                  name={opt.icon}
                  size={20}
                  color={active ? colors.primary[500] : theme.textTertiary}
                />
                <Text style={[
                  styles.themeBtnText,
                  { color: active ? colors.primary[600] : theme.textSecondary, fontFamily },
                  active && { fontWeight: fontWeight.semibold },
                ]}>
                  {opt.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </View>

      {/* About */}
      <SectionHeader title={'\u30A2\u30D7\u30EA\u60C5\u5831'} />
      <View style={cardStyle}>
        <View style={styles.row}>
          <View style={styles.rowIcon}>
            <Ionicons name="information-circle-outline" size={18} color={theme.textSecondary} />
          </View>
          <Text style={[styles.rowLabel, { color: theme.text, fontFamily }]}>{'\u30D0\u30FC\u30B8\u30E7\u30F3'}</Text>
          <Text style={[styles.rowValue, { color: theme.textSecondary, fontFamily }]}>1.2.0</Text>
        </View>
      </View>

      {/* Logout */}
      <TouchableOpacity
        style={[styles.logoutBtn, { borderColor: colors.danger[500] }]}
        onPress={() => {
          Alert.alert('\u30ED\u30B0\u30A2\u30A6\u30C8', '\u672C\u5F53\u306B\u30ED\u30B0\u30A2\u30A6\u30C8\u3057\u307E\u3059\u304B\uFF1F', [
            { text: '\u30AD\u30E3\u30F3\u30BB\u30EB', style: 'cancel' },
            { text: '\u30ED\u30B0\u30A2\u30A6\u30C8', style: 'destructive', onPress: async () => { await unregister(); signOut(); } },
          ]);
        }}
        activeOpacity={0.6}
      >
        <Ionicons name="log-out-outline" size={18} color={colors.danger[500]} />
        <Text style={[styles.logoutText, { fontFamily }]}>{'\u30ED\u30B0\u30A2\u30A6\u30C8'}</Text>
      </TouchableOpacity>

      <View style={{ height: spacing['3xl'] }} />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: spacing.lg },
  sectionTitle: {
    fontSize: fontSize.captionMd,
    fontWeight: fontWeight.semibold,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    marginTop: spacing['2xl'],
    marginBottom: spacing.sm,
    marginLeft: spacing.xs,
  },
  card: {
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
    borderWidth: StyleSheet.hairlineWidth,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  rowIcon: { width: 28 },
  rowLabel: { flex: 1, fontSize: fontSize.bodyMd },
  rowValue: { fontSize: fontSize.bodyMd },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  switchIcon: { width: 28 },
  switchLabel: { flex: 1, fontSize: fontSize.bodyMd },
  divider: { height: StyleSheet.hairlineWidth, marginVertical: spacing.md },
  linkRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.xs,
  },
  linkText: { flex: 1, fontSize: fontSize.bodyMd, fontWeight: fontWeight.medium },
  fieldLabel: {
    fontSize: fontSize.captionMd,
    fontWeight: fontWeight.medium,
    marginBottom: spacing.sm,
  },
  statusDot: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  dot: { width: 7, height: 7, borderRadius: 4 },
  statusText: { fontSize: fontSize.bodySm, fontWeight: fontWeight.medium },
  segmented: {
    flexDirection: 'row',
    borderRadius: borderRadius.sm,
    padding: 3,
    gap: 2,
  },
  segmentItem: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.xs,
    alignItems: 'center',
  },
  segmentItemActive: {},
  segmentText: { fontSize: fontSize.bodySm, fontWeight: fontWeight.medium },
  textInput: {
    fontSize: fontSize.bodyMd,
    borderRadius: borderRadius.sm,
    padding: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
  },
  themeRow: { flexDirection: 'row', gap: spacing.sm },
  themeBtn: {
    flex: 1,
    paddingVertical: spacing.md,
    borderRadius: borderRadius.md,
    alignItems: 'center',
    gap: spacing.xs,
    borderWidth: 1.5,
  },
  themeBtnText: { fontSize: fontSize.caption, fontWeight: fontWeight.medium },
  logoutBtn: {
    marginTop: spacing['3xl'],
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.sm,
    borderWidth: 1,
  },
  logoutText: {
    color: colors.danger[500],
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
  },
});
