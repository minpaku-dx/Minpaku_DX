import { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  TouchableOpacity,
} from 'react-native';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/hooks/useTheme';
import { Button } from '@/components/ui/Button';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

export default function LoginScreen() {
  const { theme, isDark } = useTheme();
  const { signIn, signUp } = useAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignUp, setIsSignUp] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!email.trim() || !password.trim()) {
      setError('メールアドレスとパスワードを入力してください');
      return;
    }

    setLoading(true);
    setError('');

    try {
      if (isSignUp) {
        await signUp(email.trim(), password);
      } else {
        await signIn(email.trim(), password);
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '認証エラーが発生しました';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.bg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <View style={styles.inner}>
        {/* Logo / Title */}
        <View style={styles.header}>
          <Text style={[styles.appName, { color: colors.primary[500] }]}>
            Minpaku DX
          </Text>
          <Text style={[styles.tagline, { color: theme.textSecondary }]}>
            民泊メッセージ管理
          </Text>
        </View>

        {/* Form */}
        <View style={styles.form}>
          <TextInput
            style={[
              styles.input,
              {
                backgroundColor: isDark ? colors.dark.elevated : colors.white,
                color: theme.text,
                borderColor: theme.border,
              },
            ]}
            placeholder="メールアドレス"
            placeholderTextColor={theme.textTertiary}
            value={email}
            onChangeText={setEmail}
            keyboardType="email-address"
            autoCapitalize="none"
            autoComplete="email"
          />

          <TextInput
            style={[
              styles.input,
              {
                backgroundColor: isDark ? colors.dark.elevated : colors.white,
                color: theme.text,
                borderColor: theme.border,
              },
            ]}
            placeholder="パスワード"
            placeholderTextColor={theme.textTertiary}
            value={password}
            onChangeText={setPassword}
            secureTextEntry
            autoComplete="password"
          />

          {error ? (
            <Text style={styles.error}>{error}</Text>
          ) : null}

          <Button
            title={isSignUp ? 'アカウント作成' : 'ログイン'}
            onPress={handleSubmit}
            loading={loading}
          />

          <TouchableOpacity
            onPress={() => {
              setIsSignUp((v) => !v);
              setError('');
            }}
            style={styles.toggleBtn}
          >
            <Text style={[styles.toggleText, { color: colors.primary[500] }]}>
              {isSignUp
                ? 'アカウントをお持ちの方はこちら'
                : 'アカウントを作成する'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  inner: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing['3xl'],
  },
  appName: {
    fontSize: 32,
    fontWeight: fontWeight.bold,
    marginBottom: spacing.xs,
  },
  tagline: {
    fontSize: fontSize.bodyLg,
  },
  form: {
    gap: spacing.md,
  },
  input: {
    height: 48,
    borderRadius: borderRadius.md,
    borderWidth: 1,
    paddingHorizontal: spacing.lg,
    fontSize: fontSize.bodyMd,
  },
  error: {
    color: colors.danger[500],
    fontSize: fontSize.bodySm,
    textAlign: 'center',
  },
  toggleBtn: {
    alignItems: 'center',
    paddingVertical: spacing.sm,
  },
  toggleText: {
    fontSize: fontSize.bodyMd,
  },
});
