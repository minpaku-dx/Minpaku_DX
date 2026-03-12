import { FlatList, RefreshControl, View, Text, StyleSheet } from 'react-native';
import { useQuery } from '@tanstack/react-query';
import { api, type Property } from '@/lib/api';
import { useTheme } from '@/hooks/useTheme';
import { EmptyState } from '@/components/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

export default function PropertiesScreen() {
  const { theme } = useTheme();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ['properties'],
    queryFn: () => api.getProperties().then((r) => r.properties),
  });

  const properties = data ?? [];

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      <FlatList
        data={properties}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <View style={[styles.card, { backgroundColor: theme.card }]}>
            <View style={styles.cardRow}>
              <Text style={[styles.name, { color: theme.text }]}>{item.name}</Text>
              {item.pendingCount > 0 && (
                <Badge label={String(item.pendingCount)} variant="count" />
              )}
            </View>
            <Text style={[styles.id, { color: theme.textTertiary }]}>
              ID: {item.id}
            </Text>
          </View>
        )}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={refetch}
            tintColor={colors.primary[500]}
          />
        }
        contentContainerStyle={!properties.length ? styles.emptyContainer : styles.list}
        ListEmptyComponent={
          isLoading ? null : (
            <EmptyState
              icon="🏠"
              title="物件がありません"
              subtitle="管理物件が登録されるとここに表示されます"
            />
          )
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  list: {
    paddingTop: spacing.md,
    paddingBottom: spacing['3xl'],
  },
  emptyContainer: {
    flex: 1,
  },
  card: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    padding: spacing.lg,
    borderRadius: borderRadius.lg,
  },
  cardRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  name: {
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.semibold,
    flex: 1,
    marginRight: spacing.sm,
  },
  id: {
    fontSize: fontSize.caption,
  },
});
