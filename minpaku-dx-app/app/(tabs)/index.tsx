import { useState, useMemo, useEffect } from 'react';
import { FlatList, RefreshControl, StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useMessages, useSendMessage, useSkipMessage } from '@/hooks/useMessages';
import { useNotifications } from '@/hooks/useNotifications';
import { useTheme } from '@/hooks/useTheme';
import { SwipeableCard } from '@/components/SwipeableCard';
import { SkeletonList } from '@/components/SkeletonCard';
import { EmptyState } from '@/components/EmptyState';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

type FilterTab = 'all' | 'reply' | 'proactive';

const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: 'all', label: 'すべて' },
  { key: 'reply', label: '返信' },
  { key: 'proactive', label: 'プロアクティブ' },
];

export default function InboxScreen() {
  const { theme, isDark } = useTheme();
  const router = useRouter();
  const { data: messages, isLoading, refetch, isRefetching } = useMessages();
  const sendMutation = useSendMessage();
  const skipMutation = useSkipMessage();
  const { requestPermission } = useNotifications();

  const [filter, setFilter] = useState<FilterTab>('all');

  useEffect(() => {
    requestPermission();
  }, []);

  const filteredMessages = useMemo(() => {
    if (!messages) return [];
    if (filter === 'all') return messages;
    return messages.filter((m) => m.type === filter);
  }, [messages, filter]);

  const handlePress = (msg: MessageCardType) => {
    router.push(`/messages/${msg.id}`);
  };

  const handleSend = (msg: MessageCardType) => {
    sendMutation.mutate({
      messageId: msg.id,
      bookingId: msg.bookingId,
      message: msg.draft,
    });
  };

  const handleSkip = (msg: MessageCardType) => {
    skipMutation.mutate({ messageId: msg.id });
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.bg }]}>
      {/* Filter Tabs */}
      <View style={[styles.filterRow, { backgroundColor: theme.card, borderBottomColor: theme.divider }]}>
        {FILTER_TABS.map((tab) => {
          const active = filter === tab.key;
          return (
            <TouchableOpacity
              key={tab.key}
              style={[
                styles.filterTab,
                active && { backgroundColor: colors.primary[500] },
                !active && {
                  backgroundColor: isDark ? colors.dark.elevated : colors.gray[100],
                },
              ]}
              onPress={() => setFilter(tab.key)}
            >
              <Text
                style={[
                  styles.filterTabText,
                  { color: active ? colors.white : theme.textSecondary },
                ]}
              >
                {tab.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {isLoading ? (
        <SkeletonList />
      ) : (
        <FlatList
          data={filteredMessages}
          keyExtractor={(item) => String(item.id)}
          renderItem={({ item }) => (
            <SwipeableCard
              message={item}
              onPress={() => handlePress(item)}
              onSend={() => handleSend(item)}
              onSkip={() => handleSkip(item)}
              disabled={sendMutation.isPending || skipMutation.isPending}
            />
          )}
          refreshControl={
            <RefreshControl
              refreshing={isRefetching}
              onRefresh={refetch}
              tintColor={colors.primary[500]}
            />
          }
          contentContainerStyle={
            !filteredMessages.length ? styles.emptyContainer : styles.list
          }
          ListEmptyComponent={
            <EmptyState
              icon="📭"
              title="未処理メッセージはありません"
              subtitle="新しいゲストメッセージが届くとここに表示されます"
            />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  filterRow: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    gap: spacing.sm,
    borderBottomWidth: 1,
  },
  filterTab: {
    flex: 1,
    paddingVertical: spacing.sm,
    borderRadius: borderRadius.md,
    alignItems: 'center',
  },
  filterTabText: {
    fontSize: fontSize.bodySm,
    fontWeight: fontWeight.medium,
  },
  list: {
    paddingTop: spacing.md,
    paddingBottom: spacing['3xl'],
  },
  emptyContainer: {
    flex: 1,
  },
});
