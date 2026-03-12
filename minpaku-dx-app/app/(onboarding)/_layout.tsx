import { Stack } from 'expo-router';
import { useTheme } from '@/hooks/useTheme';
import { fontSize, fontWeight } from '@/lib/theme';

export default function OnboardingLayout() {
  const { theme } = useTheme();

  return (
    <Stack
      screenOptions={{
        headerStyle: { backgroundColor: theme.headerBg },
        headerTitleStyle: {
          fontSize: fontSize.headingLg,
          fontWeight: fontWeight.semibold,
          color: theme.text,
        },
        headerTintColor: theme.text,
      }}
    >
      <Stack.Screen name="beds24-token" options={{ title: 'Beds24接続' }} />
      <Stack.Screen name="properties" options={{ title: '物件確認' }} />
      <Stack.Screen name="notifications" options={{ title: '通知設定' }} />
    </Stack>
  );
}
