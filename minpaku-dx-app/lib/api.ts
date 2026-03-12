import { supabase } from './supabase';

const API_BASE = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000';

type RequestOptions = {
  method?: string;
  body?: unknown;
  params?: Record<string, string | number>;
};

/**
 * Authenticated API client.
 * Automatically attaches Supabase JWT to every request.
 */
async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, params } = options;

  // Get current session token
  const { data: { session } } = await supabase.auth.getSession();
  if (!session?.access_token) {
    throw new Error('Not authenticated');
  }

  // Build URL with query params
  let url = `${API_BASE}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.set(key, String(value));
      }
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {
    Authorization: `Bearer ${session.access_token}`,
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401) {
    // Try refreshing the session
    const { error } = await supabase.auth.refreshSession();
    if (error) throw new Error('Session expired');
    // Retry once
    return request(path, options);
  }

  if (!response.ok) {
    const errorBody = await response.text().catch(() => '');
    throw new Error(`API error ${response.status}: ${errorBody}`);
  }

  return response.json();
}

// ─── Typed API functions ───

export type MessageCard = {
  id: string | number;
  bookingId: number;
  propertyId: number;
  guestText: string;
  time: string;
  guestName: string;
  checkIn: string;
  checkOut: string;
  propertyName: string;
  draft: string;
  thread: ThreadMessage[];
  type: 'reply' | 'proactive';
  triggerType?: string;
  triggerLabel?: string;
};

export type ThreadMessage = {
  id: number;
  bookingId: number;
  propertyId: number;
  message: string;
  time: string;
  source: string;
  read: boolean;
};

export type MessageDetail = {
  message: MessageCard;
  booking: Record<string, unknown>;
  thread: ThreadMessage[];
  draft: { draft_text: string; model: string } | null;
};

export type Property = {
  id: number;
  name: string;
  pendingCount: number;
};

export const api = {
  // Messages
  getMessages: () =>
    request<{ messages: MessageCard[] }>('/api/messages'),

  getMessageHistory: (params: { status?: string; limit?: number; offset?: number }) =>
    request<{ messages: MessageCard[]; hasMore: boolean }>('/api/messages/history', { params: params as Record<string, string | number> }),

  getMessageDetail: (id: string | number) =>
    request<MessageDetail>(`/api/messages/${id}`),

  sendMessage: (data: { messageId: string | number; bookingId: number; message: string }) =>
    request<{ ok: boolean }>('/api/app/send', { method: 'POST', body: data }),

  skipMessage: (data: { messageId: string | number }) =>
    request<{ ok: boolean }>('/api/app/skip', { method: 'POST', body: data }),

  // User
  getMe: () =>
    request<{ user: { id: string; email: string }; properties: Property[] }>('/api/me'),

  // Devices
  registerDevice: (fcmToken: string, platform: string) =>
    request<{ ok: boolean }>('/api/devices', { method: 'POST', body: { fcm_token: fcmToken, platform } }),

  unregisterDevice: (fcmToken: string) =>
    request<{ ok: boolean }>(`/api/devices/${encodeURIComponent(fcmToken)}`, { method: 'DELETE' }),

  // Properties
  getProperties: () =>
    request<{ properties: Property[] }>('/api/properties'),

  // Bookings
  getBookings: (params?: { propertyId?: number }) =>
    request<{ bookings: Record<string, unknown>[] }>('/api/bookings', { params: params as Record<string, string | number> }),

  // Mark as read
  markAsRead: (messageId: string | number) =>
    request<{ ok: boolean }>(`/api/messages/${messageId}/read`, { method: 'POST' }),
};
