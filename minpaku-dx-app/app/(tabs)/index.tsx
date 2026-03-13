import { useState, useMemo, useEffect } from 'react';
import { FlatList, RefreshControl, StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { useRouter } from 'expo-router';
import { useMessages, useSendMessage, useSkipMessage } from '@/hooks/useMessages';
import { useNotifications } from '@/hooks/useNotifications';
import { useTheme } from '@/hooks/useTheme';
import { SwipeableCard } from '@/components/SwipeableCard';
import { SkeletonList } from '@/components/SkeletonCard';
import { EmptyState } from '@/components/EmptyState';
import { InboxClearIllustration } from '@/components/illustrations/InboxClear';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, shadow } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

type FilterTab = 'all' | 'reply' | 'proactive';

const FILTER_TABS: { key: FilterTab; label: string }[] = [
  { key: 'all', label: '\u3059\u3079\u3066' },
  { key: 'reply', label: '\u8FD4\u4FE1' },
  { key: 'proactive', label: '\u5148\u56DE\u308A' },
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

  const counts = useMemo(() => {
    if (!messages) return { all: 0, reply: 0, proactive: 0 };
    return {
      all: messages.length,
      reply: messages.filter((m) => m.type === 'reply').length,
      proactive: messages.filter((m) => m.type === 'proactive').length,
    };
  }, [messages]);

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
      {/* Filter bar */}
      <View style={[styles.filterBar, { backgroundColor: theme.card, borderBottomColor: theme.divider }]}>
        {FILTER_TABS.map((tab) => {
          const active = filter === tab.key;
          const count = counts[tab.key];
          return (
            <TouchableOpacity
              key={tab.key}
              style={[
                styles.filterChip,
                active
                  ? { backgroundColor: isDark ? colors.primary[700] : colors.primary[600] }
                  : { backgroundColor: isDark ? colors.dark.elevated : colors.gray[100] },
              ]}
              onPress={() => setFilter(tab.key)}
              activeOpacity={0.7}
            >
              <Text
                style={[
                  styles.filterText,
                  { color: active ? colors.white : theme.textSecondary, fontFamily },
                ]}
              >
                {tab.label}
              </Text>
              {count > 0 && (
                <View style={[
                  styles.filterCount,
                  { backgroundColor: active ? 'rgba(255,255,255,0.25)' : theme.divider },
                ]}>
                  <Text style={[
                    styles.filterCountText,
                    { color: active ? colors.white : theme.textTertiary, fontFamily },
                  ]}>
                    {count}
                  </Text>
                </View>
              )}
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
              illustration={<InboxClearIllustration />}
              title={'\u672A\u51E6\u7406\u30E1\u30C3\u30BB\u30FC\u30B8\u306F\u3042\u308A\u307E\u305B\u3093'}
              subtitle={'\u65B0\u3057\u3044\u30B2\u30B9\u30C8\u30E1\u30C3\u30BB\u30FC\u30B8\u304C\u5C4A\u304F\u3068\u3053\u3053\u306B\u8868\u793A\u3055\u308C\u307E\u3059'}
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
  filterBar: {
    flexDirection: 'row',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    gap: spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  filterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    paddingHorizontal: spacing.lg,
    borderRadius: borderRadius.full,
    gap: spacing.xs,
  },
  filterText: {
    fontSize: fontSize.bodySm,
    fontWeight: fontWeight.semibold,
  },
  filterCount: {
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 5,
  },
  filterCountText: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.bold,
  },
  list: {
    paddingTop: spacing.md,
    paddingBottom: spacing['4xl'],
  },
  emptyContainer: {
    flex: 1,
  },
});
