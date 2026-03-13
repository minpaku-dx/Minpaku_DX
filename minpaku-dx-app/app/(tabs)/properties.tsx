import { FlatList, RefreshControl, View, Text, StyleSheet } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useQuery } from '@tanstack/react-query';
import { api, type Property } from '@/lib/api';
import { useTheme } from '@/hooks/useTheme';
import { EmptyState } from '@/components/EmptyState';
import { NoPropertiesIllustration } from '@/components/illustrations/NoProperties';
import { Badge } from '@/components/ui/Badge';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, shadow } from '@/lib/theme';

export default function PropertiesScreen() {
  const { theme, isDark } = useTheme();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['properties'],
    queryFn: () => api.getProperties().then((r) => r.properties),
  });

  const properties = data ?? [];

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <FlatList
        data={properties}
        keyExtractor={(item) => String(item.property_id)}
        renderItem={({ item }) => (
          <View
            style={[styles.card, shadow.sm, { backgroundColor: theme.card, borderColor: isDark ? theme.cardBorder : colors.gray[200] }]}
          >
            <View style={styles.iconCircle}>
              <Ionicons name="business" size={18} color={colors.primary[600]} />
            </View>
            <View style={styles.info}>
              <Text style={[styles.name, { color: theme.text, fontFamily }]} numberOfLines={1}>
                {item.property_name ?? `\u7269\u4EF6 ${item.property_id}`}
              </Text>
              <Text style={[styles.id, { color: theme.textTertiary, fontFamily }]}>
                ID: {item.property_id}
              </Text>
            </View>
            {(item.pending_count ?? 0) > 0 && (
              <Badge label={String(item.pending_count)} variant="count" />
            )}
          </View>
        )}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={colors.primary[500]} />
        }
        contentContainerStyle={!properties.length ? styles.emptyContainer : styles.list}
        ListEmptyComponent={
          isLoading ? null : (
            <EmptyState
              illustration={<NoPropertiesIllustration />}
              title={'\u7269\u4EF6\u304C\u3042\u308A\u307E\u305B\u3093'}
              subtitle={'\u7BA1\u7406\u7269\u4EF6\u304C\u767B\u9332\u3055\u308C\u308B\u3068\u3053\u3053\u306B\u8868\u793A\u3055\u308C\u307E\u3059'}
            />
          )
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  list: { paddingTop: spacing.md, paddingBottom: spacing['4xl'] },
  emptyContainer: { flex: 1 },
  card: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    padding: spacing.lg,
    borderRadius: borderRadius.lg,
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    borderWidth: StyleSheet.hairlineWidth,
  },
  iconCircle: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: colors.primary[50],
    alignItems: 'center',
    justifyContent: 'center',
  },
  info: { flex: 1, gap: 2 },
  name: {
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.semibold,
    letterSpacing: -0.2,
  },
  id: { fontSize: fontSize.caption },
});
