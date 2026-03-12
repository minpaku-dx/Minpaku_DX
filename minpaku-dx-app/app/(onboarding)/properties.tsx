import { View, Text, TouchableOpacity, StyleSheet, FlatList } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useTheme } from '@/hooks/useTheme';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

type DetectedProperty = {
  property_id: number;
  property_name: string;
};

export default function PropertiesScreen() {
  const { theme } = useTheme();
  const router = useRouter();
  const params = useLocalSearchParams<{ properties: string; message: string }>();

  const properties: DetectedProperty[] = params.properties
    ? JSON.parse(params.properties)
    : [];
  const message = params.message ?? '';

  const handleNext = () => {
    router.push('/(onboarding)/notifications');
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <View style={styles.content}>
        <Text style={[styles.heading, { color: theme.text }]}>
          検出された物件
        </Text>
        <Text style={[styles.description, { color: theme.textSecondary }]}>
          {message}
        </Text>

        {properties.length > 0 ? (
          <FlatList
            data={properties}
            keyExtractor={(item) => String(item.property_id)}
            renderItem={({ item }) => (
              <View style={[styles.propertyCard, { backgroundColor: theme.card }]}>
                <Text style={[styles.propertyName, { color: theme.text }]}>
                  {item.property_name || `物件 ${item.property_id}`}
                </Text>
                <Text style={[styles.propertyId, { color: theme.textSecondary }]}>
                  ID: {item.property_id}
                </Text>
              </View>
            )}
            contentContainerStyle={styles.list}
            scrollEnabled={false}
          />
        ) : (
          <View style={[styles.emptyCard, { backgroundColor: theme.card }]}>
            <Text style={[styles.emptyText, { color: theme.textSecondary }]}>
              物件が見つかりませんでした。{'\n'}
              予約データが同期されると自動的に検出されます。
            </Text>
          </View>
        )}
      </View>

      <View style={styles.footer}>
        <TouchableOpacity style={styles.button} onPress={handleNext}>
          <Text style={styles.buttonText}>次へ</Text>
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
  list: {
    gap: spacing.sm,
  },
  propertyCard: {
    borderRadius: borderRadius.lg,
    padding: spacing.lg,
  },
  propertyName: {
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.semibold,
  },
  propertyId: {
    fontSize: fontSize.bodySm,
    marginTop: spacing.xs,
  },
  emptyCard: {
    borderRadius: borderRadius.lg,
    padding: spacing.xl,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: fontSize.bodyMd,
    textAlign: 'center',
    lineHeight: 22,
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
