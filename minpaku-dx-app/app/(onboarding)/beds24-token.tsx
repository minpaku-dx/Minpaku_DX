import { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useTheme } from '@/hooks/useTheme';
import { useAppStore } from '@/lib/store';
import { api } from '@/lib/api';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

export default function Beds24TokenScreen() {
  const { theme, isDark } = useTheme();
  const router = useRouter();
  const showToast = useAppStore((s) => s.showToast);

  const [token, setToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    const trimmed = token.trim();
    if (!trimmed) {
      setError('トークンを入力してください');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await api.submitOnboarding(trimmed);
      // Pass detected properties to next screen
      router.push({
        pathname: '/(onboarding)/properties',
        params: {
          properties: JSON.stringify(result.properties),
          message: result.message,
        },
      });
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '接続に失敗しました';
      setError(msg);
      showToast('接続に失敗しました', 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.bg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <View style={styles.content}>
        <Text style={[styles.heading, { color: theme.text }]}>
          Beds24を接続する
        </Text>
        <Text style={[styles.description, { color: theme.textSecondary }]}>
          Beds24のリフレッシュトークンを入力してください。{'\n'}
          トークンはBeds24管理画面のAPI設定から取得できます。
        </Text>

        <TextInput
          style={[
            styles.input,
            {
              color: theme.text,
              backgroundColor: isDark ? colors.dark.elevated : colors.white,
              borderColor: error ? colors.danger[500] : theme.border,
            },
          ]}
          value={token}
          onChangeText={(t) => { setToken(t); setError(''); }}
          placeholder="リフレッシュトークンを入力"
          placeholderTextColor={theme.textTertiary}
          autoCapitalize="none"
          autoCorrect={false}
          editable={!loading}
        />

        {error ? (
          <Text style={styles.errorText}>{error}</Text>
        ) : null}

        <TouchableOpacity
          style={[
            styles.button,
            { opacity: loading || !token.trim() ? 0.6 : 1 },
          ]}
          onPress={handleSubmit}
          disabled={loading || !token.trim()}
        >
          {loading ? (
            <ActivityIndicator color={colors.white} />
          ) : (
            <Text style={styles.buttonText}>接続して物件を検出</Text>
          )}
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
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
    marginBottom: spacing.xl,
  },
  input: {
    fontSize: fontSize.bodyMd,
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    borderWidth: 1,
    marginBottom: spacing.sm,
  },
  errorText: {
    color: colors.danger[500],
    fontSize: fontSize.bodySm,
    marginBottom: spacing.md,
  },
  button: {
    backgroundColor: colors.primary[500],
    borderRadius: borderRadius.md,
    padding: spacing.lg,
    alignItems: 'center',
    marginTop: spacing.md,
  },
  buttonText: {
    color: colors.white,
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
  },
});
