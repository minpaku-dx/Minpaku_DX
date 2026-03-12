import { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { useLocalSearchParams, Stack } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import * as Haptics from 'expo-haptics';
import { api, type ThreadMessage } from '@/lib/api';
import { useSendMessage, useSkipMessage } from '@/hooks/useMessages';
import { useTheme } from '@/hooks/useTheme';
import { ChatBubble } from '@/components/ChatBubble';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { colors, spacing, borderRadius, fontSize, fontWeight } from '@/lib/theme';

export default function MessageDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { theme, isDark } = useTheme();
  const sendMutation = useSendMessage();
  const skipMutation = useSkipMessage();

  const { data, isLoading } = useQuery({
    queryKey: ['messages', id],
    queryFn: () => api.getMessageDetail(id),
    enabled: !!id,
  });

  const detail = data;
  const thread = detail?.thread ?? [];
  const draft = detail?.draft?.draft_text ?? detail?.message?.draft ?? '';
  const message = detail?.message;

  const [editedDraft, setEditedDraft] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const flatListRef = useRef<FlatList<ThreadMessage>>(null);

  // Initialize draft text when data loads
  useEffect(() => {
    if (draft && !isEditing) {
      setEditedDraft(draft);
    }
  }, [draft]);

  const handleSend = async () => {
    if (!message || !editedDraft.trim()) return;

    try {
      await sendMutation.mutateAsync({
        messageId: message.id,
        bookingId: message.bookingId,
        message: editedDraft.trim(),
      });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
    } catch {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    }
  };

  const handleSkip = async () => {
    if (!message) return;

    try {
      await skipMutation.mutateAsync({ messageId: message.id });
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
    } catch {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
    }
  };

  if (isLoading || !detail) {
    return (
      <View style={[styles.loading, { backgroundColor: theme.bg }]}>
        <Stack.Screen options={{ title: '読み込み中...' }} />
        <ActivityIndicator size="large" color={colors.primary[500]} />
      </View>
    );
  }

  const latestGuestIdx = thread.reduce(
    (acc, msg, i) => (msg.source === 'guest' ? i : acc),
    -1,
  );

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: theme.bg }]}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
    >
      <Stack.Screen
        options={{
          title: message?.guestName ?? '',
          headerStyle: { backgroundColor: theme.headerBg },
          headerTintColor: theme.text,
        }}
      />

      {/* Booking Info Bar */}
      <View style={[styles.infoBar, { backgroundColor: theme.card, borderBottomColor: theme.divider }]}>
        <Text style={[styles.propertyText, { color: theme.textSecondary }]} numberOfLines={1}>
          {message?.propertyName}
        </Text>
        <View style={styles.infoRight}>
          {message?.checkIn && (
            <Text style={[styles.dateText, { color: theme.textTertiary }]}>
              {message.checkIn} → {message.checkOut}
            </Text>
          )}
          {message?.type === 'proactive' && message.triggerLabel && (
            <Badge
              label={message.triggerLabel}
              variant={message.triggerType === 'pre_checkin' ? 'checkin' : 'checkout'}
            />
          )}
        </View>
      </View>

      {/* Thread */}
      <FlatList
        ref={flatListRef}
        data={thread}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item, index }) => (
          <ChatBubble message={item} isLatest={index === latestGuestIdx} />
        )}
        contentContainerStyle={styles.threadList}
        onContentSizeChange={() => {
          flatListRef.current?.scrollToEnd({ animated: false });
        }}
      />

      {/* Draft Editor */}
      <View style={[styles.draftArea, { backgroundColor: theme.card, borderTopColor: theme.divider }]}>
        <View style={styles.draftHeader}>
          <Text style={[styles.draftLabel, { color: theme.textSecondary }]}>
            AI下書き
          </Text>
          {!isEditing && editedDraft !== draft && (
            <Text style={[styles.editedBadge, { color: colors.warning[500] }]}>
              編集済み
            </Text>
          )}
        </View>

        <TextInput
          style={[
            styles.draftInput,
            {
              backgroundColor: isDark ? colors.dark.elevated : colors.gray[50],
              color: theme.text,
              borderColor: isEditing ? colors.primary[500] : theme.border,
            },
          ]}
          value={editedDraft}
          onChangeText={(t) => {
            setEditedDraft(t);
            if (!isEditing) setIsEditing(true);
          }}
          onFocus={() => setIsEditing(true)}
          onBlur={() => setIsEditing(false)}
          multiline
          placeholder="返信メッセージを入力..."
          placeholderTextColor={theme.textTertiary}
        />

        <View style={styles.actions}>
          <Button
            title="スキップ"
            variant="secondary"
            onPress={handleSkip}
            loading={skipMutation.isPending}
            disabled={sendMutation.isPending}
            flex={1}
          />
          <Button
            title="送信"
            variant="primary"
            onPress={handleSend}
            loading={sendMutation.isPending}
            disabled={skipMutation.isPending || !editedDraft.trim()}
            flex={2}
          />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  loading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  infoBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
    borderBottomWidth: 1,
  },
  propertyText: {
    fontSize: fontSize.bodySm,
    flex: 1,
  },
  infoRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
  },
  dateText: {
    fontSize: fontSize.caption,
  },
  threadList: {
    paddingVertical: spacing.lg,
  },
  draftArea: {
    padding: spacing.lg,
    borderTopWidth: 1,
  },
  draftHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: spacing.sm,
  },
  draftLabel: {
    fontSize: fontSize.bodySm,
    fontWeight: fontWeight.semibold,
  },
  editedBadge: {
    fontSize: fontSize.caption,
    fontWeight: fontWeight.medium,
  },
  draftInput: {
    borderWidth: 1,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    fontSize: fontSize.bodyMd,
    minHeight: 80,
    maxHeight: 160,
    textAlignVertical: 'top',
    marginBottom: spacing.md,
  },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
  },
});
