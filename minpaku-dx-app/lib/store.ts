import { create } from 'zustand';

export type ToastVariant = 'success' | 'error' | 'warning' | 'info';

type ToastItem = {
  id: string;
  message: string;
  variant: ToastVariant;
};

type AppStore = {
  /** Whether the user has completed onboarding */
  onboarded: boolean;
  setOnboarded: (v: boolean) => void;

  /** Dark mode preference: 'system' | 'light' | 'dark' */
  themeMode: 'system' | 'light' | 'dark';
  setThemeMode: (v: 'system' | 'light' | 'dark') => void;

  /** Toast notification queue */
  toasts: ToastItem[];
  showToast: (message: string, variant: ToastVariant) => void;
  dismissToast: (id: string) => void;

  /** Push notification token */
  fcmToken: string | null;
  setFcmToken: (v: string | null) => void;
};

let _toastId = 0;

export const useAppStore = create<AppStore>((set) => ({
  onboarded: false,
  setOnboarded: (v) => set({ onboarded: v }),

  themeMode: 'system',
  setThemeMode: (v) => set({ themeMode: v }),

  toasts: [],
  showToast: (message, variant) => {
    const id = String(++_toastId);
    set((s) => ({ toasts: [...s.toasts.slice(-4), { id, message, variant }] }));
  },
  dismissToast: (id) =>
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),

  fcmToken: null,
  setFcmToken: (v) => set({ fcmToken: v }),
}));
