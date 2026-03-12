import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type MessageCard } from '@/lib/api';
import { useAppStore } from '@/lib/store';

/** Pending messages (inbox) — refetches every 60s when focused */
export function useMessages() {
  return useQuery({
    queryKey: ['messages'],
    queryFn: () => api.getMessages().then((r) => r.messages),
    refetchInterval: 60_000,
  });
}

/** Message history — paginated */
export function useMessageHistory(params: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: ['messages', 'history', params],
    queryFn: () => api.getMessageHistory(params),
  });
}

/** Send (approve) a message — optimistic update */
export function useSendMessage() {
  const queryClient = useQueryClient();
  const showToast = useAppStore((s) => s.showToast);

  return useMutation({
    mutationFn: (data: {
      messageId: string | number;
      bookingId: number;
      message: string;
    }) => api.sendMessage(data),

    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: ['messages'] });
      const previous = queryClient.getQueryData<MessageCard[]>(['messages']);

      // Optimistically remove the card from inbox
      queryClient.setQueryData<MessageCard[]>(['messages'], (old) =>
        old?.filter((m) => String(m.id) !== String(data.messageId)),
      );

      return { previous };
    },

    onSuccess: () => {
      showToast('送信しました', 'success');
    },

    onError: (_err, _data, context) => {
      // Roll back on error
      if (context?.previous) {
        queryClient.setQueryData(['messages'], context.previous);
      }
      showToast('送信に失敗しました', 'error');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['messages'] });
      queryClient.invalidateQueries({ queryKey: ['messages', 'history'] });
    },
  });
}

/** Skip a message — optimistic update */
export function useSkipMessage() {
  const queryClient = useQueryClient();
  const showToast = useAppStore((s) => s.showToast);

  return useMutation({
    mutationFn: (data: { messageId: string | number }) =>
      api.skipMessage(data),

    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: ['messages'] });
      const previous = queryClient.getQueryData<MessageCard[]>(['messages']);

      queryClient.setQueryData<MessageCard[]>(['messages'], (old) =>
        old?.filter((m) => String(m.id) !== String(data.messageId)),
      );

      return { previous };
    },

    onSuccess: () => {
      showToast('スキップしました', 'warning');
    },

    onError: (_err, _data, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['messages'], context.previous);
      }
      showToast('スキップに失敗しました', 'error');
    },

    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['messages'] });
      queryClient.invalidateQueries({ queryKey: ['messages', 'history'] });
    },
  });
}
