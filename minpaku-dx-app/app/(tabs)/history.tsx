import { useState, useCallback } from 'react';
import {
  FlatList,
  RefreshControl,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useMessageHistory } from '@/hooks/useMessages';
import { useTheme } from '@/hooks/useTheme';
import { EmptyState } from '@/components/EmptyState';
import { Badge } from '@/components/ui/Badge';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

type StatusFilter = 'sent' | 'skipped' | undefined;

const LIMIT = 20;

export default function HistoryScreen() {
  const { theme, isDark } = useTheme();
  const router = useRouter();
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(undefined);
  const [offset, setOffset] = useState(0);

  const { data, isLoading, refetch, isRefetching } = useMessageHistory({
    status: statusFilter,
    limit: LIMIT,
    offset,
  });

  const messages = data?.messages ?? [];
  const hasMore = data?.hasMore ?? false;

  const handleRefresh = useCallback(() => {
    setOffset(0);
    refetch();
  }, [refetch]);

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      {/* Filter Tabs */}
      <View style={[styles.filters, { borderBottomColor: theme.divider }]}>
        {([
          { label: 'すべて', value: undefined },
          { label: '送信済み', value: 'sent' as StatusFilter },
          { label: 'スキップ', value: 'skipped' as StatusFilter },
        ] as const).map((f) => {
          const active = statusFilter === f.value;
          return (
            <TouchableOpacity
              key={f.label}
              onPress={() => {
                setStatusFilter(f.value);
                setOffset(0);
              }}
              style={[
                styles.filterTab,
                active && { borderBottomColor: colors.primary[500] },
              ]}
            >
              <Text
                style={[
                  styles.filterLabel,
                  { color: active ? colors.primary[500] : theme.textSecondary },
                ]}
              >
                {f.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <FlatList
        data={messages}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[styles.card, { backgroundColor: theme.card }]}
            activeOpacity={0.7}
            onPress={() => router.push(`/messages/${item.id}`)}
          >
            <View style={styles.cardHeader}>
              <Text style={[styles.guestName, { color: theme.text }]} numberOfLines={1}>
                {item.guestName}
              </Text>
              <Badge
                label={item.type === 'reply' ? '返信' : '先回り'}
                variant={item.type === 'reply' ? 'sent' : 'checkin'}
              />
            </View>
            <Text style={[styles.propertyName, { color: theme.textSecondary }]} numberOfLines={1}>
              {item.propertyName}
            </Text>
            {item.draft ? (
              <Text style={[styles.preview, { color: theme.textTertiary }]} numberOfLines={1}>
                {item.draft}
              </Text>
            ) : null}
            <Text style={[styles.time, { color: theme.textTertiary }]}>{item.time}</Text>
          </TouchableOpacity>
        )}
        refreshControl={
          <RefreshControl
            refreshing={isRefetching}
            onRefresh={handleRefresh}
            tintColor={colors.primary[500]}
          />
        }
        contentContainerStyle={!messages.length ? styles.emptyContainer : styles.list}
        ListEmptyComponent={
          isLoading ? null : (
            <EmptyState
              icon="📋"
              title="履歴はまだありません"
              subtitle="処理したメッセージがここに表示されます"
            />
          )
        }
        ListFooterComponent={
          hasMore ? (
            <TouchableOpacity
              style={[styles.loadMore, { backgroundColor: isDark ? colors.dark.elevated : colors.gray[100] }]}
              onPress={() => setOffset((o) => o + LIMIT)}
            >
              <Text style={[styles.loadMoreText, { color: colors.primary[500] }]}>
                もっと読み込む
              </Text>
            </TouchableOpacity>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  filters: {
    flexDirection: 'row',
    borderBottomWidth: 1,
    paddingHorizontal: spacing.lg,
  },
  filterTab: {
    paddingVertical: spacing.md,
    marginRight: spacing.xl,
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  filterLabel: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
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
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.xs,
  },
  guestName: {
    fontSize: fontSize.bodyLg,
    fontWeight: fontWeight.semibold,
    flex: 1,
    marginRight: spacing.sm,
  },
  propertyName: {
    fontSize: fontSize.bodySm,
    marginBottom: spacing.xs,
  },
  preview: {
    fontSize: fontSize.bodySm,
    marginBottom: spacing.xs,
  },
  time: {
    fontSize: fontSize.caption,
  },
  loadMore: {
    marginHorizontal: spacing.lg,
    marginVertical: spacing.md,
    padding: spacing.md,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  loadMoreText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.medium,
  },
});
