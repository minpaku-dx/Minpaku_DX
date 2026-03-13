import { Tabs } from 'expo-router';
import { StyleSheet, Platform } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '@/hooks/useTheme';
import { fontFamily, fontSize, fontWeight, spacing } from '@/lib/theme';

export default function TabsLayout() {
  const { theme } = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerStyle: {
          backgroundColor: theme.headerBg,
          elevation: 0,
          shadowOpacity: 0,
          borderBottomWidth: StyleSheet.hairlineWidth,
          borderBottomColor: theme.divider,
        },
        headerTitleStyle: {
          fontFamily,
          fontSize: fontSize.headingLg,
          fontWeight: fontWeight.bold,
          color: theme.text,
          letterSpacing: -0.5,
        },
        tabBarStyle: {
          backgroundColor: theme.tabBar,
          borderTopColor: theme.tabBarBorder,
          borderTopWidth: StyleSheet.hairlineWidth,
          height: Platform.OS === 'ios' ? 84 : 60,
          paddingBottom: Platform.OS === 'ios' ? 28 : 8,
          paddingTop: spacing.xs,
        },
        tabBarActiveTintColor: theme.tabActive,
        tabBarInactiveTintColor: theme.tabInactive,
        tabBarLabelStyle: {
          fontFamily,
          fontSize: fontSize.xs,
          fontWeight: fontWeight.medium,
          marginTop: 1,
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: '\u53D7\u4FE1\u7BB1',
          tabBarIcon: ({ focused, color }) => (
            <Ionicons name={focused ? 'mail' : 'mail-outline'} size={21} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="history"
        options={{
          title: '\u5C65\u6B74',
          tabBarIcon: ({ focused, color }) => (
            <Ionicons name={focused ? 'time' : 'time-outline'} size={21} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="properties"
        options={{
          title: '\u7269\u4EF6',
          tabBarIcon: ({ focused, color }) => (
            <Ionicons name={focused ? 'business' : 'business-outline'} size={21} color={color} />
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: '\u8A2D\u5B9A',
          tabBarIcon: ({ focused, color }) => (
            <Ionicons name={focused ? 'settings' : 'settings-outline'} size={21} color={color} />
          ),
        }}
      />
    </Tabs>
  );
}
