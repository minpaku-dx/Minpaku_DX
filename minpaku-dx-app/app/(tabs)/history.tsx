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
import { Ionicons } from '@expo/vector-icons';
import { useMessageHistory } from '@/hooks/useMessages';
import { useTheme } from '@/hooks/useTheme';
import { EmptyState } from '@/components/EmptyState';
import { NoHistoryIllustration } from '@/components/illustrations/NoHistory';
import { Badge } from '@/components/ui/Badge';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, lineHeight, shadow } from '@/lib/theme';

type StatusFilter = 'sent' | 'skipped' | undefined;

const LIMIT = 20;

const FILTERS: { label: string; value: StatusFilter; icon: keyof typeof Ionicons.glyphMap }[] = [
  { label: '\u3059\u3079\u3066', value: undefined, icon: 'list-outline' },
  { label: '\u9001\u4FE1\u6E08\u307F', value: 'sent', icon: 'checkmark-circle-outline' },
  { label: '\u30B9\u30AD\u30C3\u30D7', value: 'skipped', icon: 'arrow-forward-circle-outline' },
];

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
      {/* Segment tabs */}
      <View style={[styles.filterBar, { backgroundColor: theme.card, borderBottomColor: theme.divider }]}>
        {FILTERS.map((f) => {
          const active = statusFilter === f.value;
          return (
            <TouchableOpacity
              key={f.label}
              onPress={() => { setStatusFilter(f.value); setOffset(0); }}
              style={[
                styles.filterTab,
                active && { borderBottomColor: theme.tabActive },
              ]}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.filterLabel,
                  { color: active ? theme.tabActive : theme.textTertiary, fontFamily },
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
            style={[styles.card, shadow.sm, { backgroundColor: theme.card, borderColor: isDark ? theme.cardBorder : colors.gray[200] }]}
            activeOpacity={0.55}
            onPress={() => router.push(`/messages/${item.id}`)}
          >
            <View style={styles.cardTop}>
              <View style={[
                styles.avatar,
                { backgroundColor: item.type === 'proactive' ? colors.primary[50] : colors.success[50] },
              ]}>
                <Text style={[
                  styles.avatarText,
                  { color: item.type === 'proactive' ? colors.primary[600] : colors.success[600] },
                ]}>
                  {item.guestName.charAt(0).toUpperCase()}
                </Text>
              </View>
              <View style={styles.cardInfo}>
                <Text style={[styles.guestName, { color: theme.text, fontFamily }]} numberOfLines={1}>
                  {item.guestName}
                </Text>
                <Text style={[styles.propertyName, { color: theme.textTertiary, fontFamily }]} numberOfLines={1}>
                  {item.propertyName}
                </Text>
              </View>
              <View style={styles.cardMeta}>
                <Badge
                  label={item.type === 'reply' ? '\u8FD4\u4FE1' : '\u5148\u56DE\u308A'}
                  variant={item.type === 'reply' ? 'sent' : 'proactive'}
                />
                <Text style={[styles.time, { color: theme.textTertiary, fontFamily }]}>{item.time?.slice(5, 10).replace('-', '/')}</Text>
              </View>
            </View>
            {item.draft ? (
              <Text style={[styles.preview, { color: theme.textSecondary, fontFamily }]} numberOfLines={1}>
                {item.draft}
              </Text>
            ) : null}
          </TouchableOpacity>
        )}
        refreshControl={
          <RefreshControl refreshing={isRefetching} onRefresh={handleRefresh} tintColor={colors.primary[500]} />
        }
        contentContainerStyle={!messages.length ? styles.emptyContainer : styles.list}
        ListEmptyComponent={
          isLoading ? null : (
            <EmptyState
              illustration={<NoHistoryIllustration />}
              title={'\u5C65\u6B74\u306F\u307E\u3060\u3042\u308A\u307E\u305B\u3093'}
              subtitle={'\u51E6\u7406\u3057\u305F\u30E1\u30C3\u30BB\u30FC\u30B8\u304C\u3053\u3053\u306B\u8868\u793A\u3055\u308C\u307E\u3059'}
            />
          )
        }
        ListFooterComponent={
          hasMore ? (
            <TouchableOpacity
              style={[styles.loadMore, { borderColor: theme.border }]}
              onPress={() => setOffset((o) => o + LIMIT)}
              activeOpacity={0.7}
            >
              <Text style={[styles.loadMoreText, { color: theme.tabActive, fontFamily }]}>
                {'\u3082\u3063\u3068\u8AAD\u307F\u8FBC\u3080'}
              </Text>
              <Ionicons name="chevron-down" size={16} color={theme.tabActive} />
            </TouchableOpacity>
          ) : null
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  filterBar: {
    flexDirection: 'row',
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  filterTab: {
    flex: 1,
    paddingVertical: spacing.md,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  filterLabel: {
    fontSize: fontSize.bodySm,
    fontWeight: fontWeight.semibold,
  },
  list: { paddingTop: spacing.md, paddingBottom: spacing['4xl'] },
  emptyContainer: { flex: 1 },
  card: {
    marginHorizontal: spacing.lg,
    marginBottom: spacing.sm,
    padding: spacing.lg,
    borderRadius: borderRadius.lg,
    borderWidth: StyleSheet.hairlineWidth,
    gap: spacing.sm,
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  avatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.bold,
  },
  cardInfo: { flex: 1, gap: 1 },
  cardMeta: { alignItems: 'flex-end', gap: spacing.xs },
  guestName: {
    fontSize: fontSize.bodyMd,
    fontWeight: fontWeight.semibold,
    letterSpacing: -0.2,
  },
  propertyName: { fontSize: fontSize.caption },
  preview: { fontSize: fontSize.bodySm, lineHeight: lineHeight.bodySm, marginLeft: 46 },
  time: { fontSize: fontSize.xs },
  loadMore: {
    marginHorizontal: spacing.lg,
    marginVertical: spacing.md,
    padding: spacing.md,
    borderRadius: borderRadius.md,
    alignItems: 'center',
    borderWidth: StyleSheet.hairlineWidth,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: spacing.xs,
  },
  loadMoreText: {
    fontSize: fontSize.bodySm,
    fontWeight: fontWeight.semibold,
  },
});
