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
import { Ionicons } from '@expo/vector-icons';
import * as Haptics from 'expo-haptics';
import { api, type ThreadMessage } from '@/lib/api';
import { useSendMessage, useSkipMessage } from '@/hooks/useMessages';
import { useTheme } from '@/hooks/useTheme';
import { ChatBubble } from '@/components/ChatBubble';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { colors, spacing, borderRadius, fontSize, fontWeight, fontFamily, lineHeight } from '@/lib/theme';

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

  useEffect(() => {
    if (draft && !isEditing) setEditedDraft(draft);
  }, [draft]);

  const handleSend = async () => {
    if (!message || !editedDraft.trim()) return;
    try {
      await sendMutation.mutateAsync({ messageId: message.id, bookingId: message.bookingId, message: editedDraft.trim() });
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
        <Stack.Screen options={{ title: '' }} />
        <ActivityIndicator size="large" color={colors.primary[500]} />
      </View>
    );
  }

  const latestGuestIdx = thread.reduce((acc, msg, i) => (msg.source === 'guest' ? i : acc), -1);

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
          headerTitleStyle: { fontSize: fontSize.headingSm, fontWeight: fontWeight.semibold, fontFamily },
        }}
      />

      {/* Booking Info */}
      <View style={[styles.infoBar, { backgroundColor: theme.card, borderBottomColor: theme.divider }]}>
        <View style={styles.infoLeft}>
          <View style={styles.propertyRow}>
            <Ionicons name="business-outline" size={13} color={theme.textTertiary} />
            <Text style={[styles.propertyText, { color: theme.textSecondary, fontFamily }]} numberOfLines={1}>
              {message?.propertyName}
            </Text>
          </View>
          {message?.checkIn && (
            <View style={styles.dateRow}>
              <Ionicons name="calendar-outline" size={13} color={theme.textTertiary} />
              <Text style={[styles.dateText, { color: theme.textTertiary, fontFamily }]}>
                {message.checkIn} {'\u2192'} {message.checkOut}
              </Text>
            </View>
          )}
        </View>
        {message?.type === 'proactive' && message.triggerLabel && (
          <Badge label={message.triggerLabel} variant={message.triggerType === 'pre_checkin' ? 'checkin' : 'checkout'} />
        )}
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
        onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: false })}
      />

      {/* Draft Editor */}
      <View style={[styles.draftArea, { backgroundColor: theme.card, borderTopColor: theme.divider }]}>
        <View style={styles.draftHeader}>
          <View style={styles.draftLabelRow}>
            <Ionicons name="sparkles" size={14} color={colors.ai[500]} />
            <Text style={[styles.draftLabelText, { fontFamily }]}>AI{'\u4E0B\u66F8\u304D'}</Text>
            {detail.draft?.model && (
              <Text style={[styles.modelTag, { color: theme.textTertiary, fontFamily }]}>
                {detail.draft.model}
              </Text>
            )}
          </View>
          {editedDraft !== draft && (
            <View style={styles.editedTag}>
              <Ionicons name="pencil" size={10} color={colors.warning[600]} />
              <Text style={[styles.editedText, { color: colors.warning[600], fontFamily }]}>{'\u7DE8\u96C6\u6E08\u307F'}</Text>
            </View>
          )}
        </View>

        <TextInput
          style={[
            styles.draftInput,
            {
              backgroundColor: theme.inputBg,
              color: theme.text,
              borderColor: isEditing ? colors.primary[400] : 'transparent',
              fontFamily,
            },
          ]}
          value={editedDraft}
          onChangeText={(t) => { setEditedDraft(t); if (!isEditing) setIsEditing(true); }}
          onFocus={() => setIsEditing(true)}
          onBlur={() => setIsEditing(false)}
          multiline
          placeholder={'\u8FD4\u4FE1\u30E1\u30C3\u30BB\u30FC\u30B8\u3092\u5165\u529B...'}
          placeholderTextColor={theme.textTertiary}
        />

        <View style={styles.actions}>
          <Button
            title={'\u30B9\u30AD\u30C3\u30D7'}
            variant="secondary"
            onPress={handleSkip}
            loading={skipMutation.isPending}
            disabled={sendMutation.isPending}
            flex={1}
            compact
          />
          <Button
            title={'\u9001\u4FE1'}
            variant="primary"
            onPress={handleSend}
            loading={sendMutation.isPending}
            disabled={skipMutation.isPending || !editedDraft.trim()}
            flex={2}
            compact
          />
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loading: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  infoBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  infoLeft: { flex: 1, gap: spacing.xs },
  propertyRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  propertyText: { fontSize: fontSize.bodySm, fontWeight: fontWeight.medium },
  dateRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  dateText: { fontSize: fontSize.caption },
  threadList: { paddingVertical: spacing.lg },
  draftArea: {
    padding: spacing.lg,
    borderTopWidth: StyleSheet.hairlineWidth,
    gap: spacing.md,
  },
  draftHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  draftLabelRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs },
  draftLabelText: {
    fontSize: fontSize.captionMd,
    fontWeight: fontWeight.bold,
    color: colors.ai[600],
    letterSpacing: 0.2,
  },
  modelTag: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.medium,
    marginLeft: spacing.xs,
  },
  editedTag: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    backgroundColor: colors.warning[50],
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
    borderRadius: borderRadius.xs,
  },
  editedText: {
    fontSize: fontSize.xs,
    fontWeight: fontWeight.semibold,
  },
  draftInput: {
    borderWidth: 1.5,
    borderRadius: borderRadius.md,
    padding: spacing.md,
    fontSize: fontSize.bodyMd,
    minHeight: 72,
    maxHeight: 140,
    textAlignVertical: 'top',
    lineHeight: lineHeight.bodyMd,
  },
  actions: { flexDirection: 'row', gap: spacing.sm },
});
