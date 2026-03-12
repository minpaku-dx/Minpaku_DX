import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, type UserSettings } from '@/lib/api';
import { useAppStore } from '@/lib/store';

/** Fetch user settings */
export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettings().then((r) => r.settings),
  });
}

/** Update user settings — optimistic update */
export function useUpdateSettings() {
  const queryClient = useQueryClient();
  const showToast = useAppStore((s) => s.showToast);

  return useMutation({
    mutationFn: (data: Partial<Omit<UserSettings, 'supabase_user_id'>>) =>
      api.updateSettings(data),

    onMutate: async (data) => {
      await queryClient.cancelQueries({ queryKey: ['settings'] });
      const previous = queryClient.getQueryData<UserSettings>(['settings']);

      queryClient.setQueryData<UserSettings>(['settings'], (old) =>
        old ? { ...old, ...data } : old,
      );

      return { previous };
    },

    onSuccess: (result) => {
      queryClient.setQueryData(['settings'], result.settings);
      showToast('設定を保存しました', 'success');
    },

    onError: (_err, _data, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['settings'], context.previous);
      }
      showToast('設定の保存に失敗しました', 'error');
    },
  });
}
