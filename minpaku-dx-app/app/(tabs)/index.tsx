import { useEffect } from 'react';
import { FlatList, RefreshControl, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useMessages, useSendMessage, useSkipMessage } from '@/hooks/useMessages';
import { useNotifications } from '@/hooks/useNotifications';
import { useTheme } from '@/hooks/useTheme';
import { SwipeableCard } from '@/components/SwipeableCard';
import { SkeletonList } from '@/components/SkeletonCard';
import { EmptyState } from '@/components/EmptyState';
import { colors, spacing } from '@/lib/theme';
import type { MessageCard as MessageCardType } from '@/lib/api';

export default function InboxScreen() {
  const { theme } = useTheme();
  const router = useRouter();
  const { data: messages, isLoading, refetch, isRefetching } = useMessages();
  const sendMutation = useSendMessage();
  const skipMutation = useSkipMessage();
  const { requestPermission } = useNotifications();

  useEffect(() => {
    requestPermission();
  }, []);

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
      {isLoading ? (
        <SkeletonList />
      ) : (
        <FlatList
          data={messages ?? []}
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
            !messages?.length ? styles.emptyContainer : styles.list
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
  list: {
    paddingTop: spacing.md,
    paddingBottom: spacing['3xl'],
  },
  emptyContainer: {
    flex: 1,
  },
});
