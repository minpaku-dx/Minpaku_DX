import { supabase, DEV_SKIP_AUTH } from './supabase';

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

  // In dev mode without Supabase, use mock token
  const accessToken = DEV_SKIP_AUTH
    ? 'dev-mock-token'
    : await supabase.auth.getSession().then(({ data: { session } }) => {
        if (!session?.access_token) throw new Error('Not authenticated');
        return session.access_token;
      });

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
    Authorization: `Bearer ${accessToken}`,
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 401 && !DEV_SKIP_AUTH) {
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
  /** true when this host message was generated/sent by AI */
  aiGenerated?: boolean;
};

export type MessageDetail = {
  message: MessageCard;
  booking: Record<string, unknown>;
  thread: ThreadMessage[];
  draft: { draft_text: string; model: string } | null;
};

export type Property = {
  property_id: number;
  property_name?: string;
  permission?: string;
  pending_count?: number;
};

export type UserSettings = {
  supabase_user_id: string;
  notify_new_message: boolean;
  notify_proactive: boolean;
  notify_reminder: boolean;
  line_fallback: boolean;
  ai_tone: string;
  ai_signature: string;
  theme: string;
};

export type OnboardingResult = {
  ok: boolean;
  properties: { property_id: number; property_name: string }[];
  message: string;
};

// ─── Mock data for dev mode ───

const now = new Date();
const ago = (minutes: number) => new Date(now.getTime() - minutes * 60000).toISOString();

const MOCK_THREAD_1: ThreadMessage[] = [
  {
    id: 101, bookingId: 5001, propertyId: 206100,
    message: 'はじめまして。3月15日から3泊で予約したJohnです。チェックインの手順を教えていただけますか？',
    time: ago(180), source: 'guest', read: true,
  },
  {
    id: 102, bookingId: 5001, propertyId: 206100,
    message: 'John様、ご予約ありがとうございます。チェックインは15:00以降となります。玄関のスマートロックに暗証番号「2847」を入力してお入りください。',
    time: ago(170), source: 'host', read: true, aiGenerated: true,
  },
  {
    id: 103, bookingId: 5001, propertyId: 206100,
    message: 'ありがとうございます！もう一つ質問なのですが、近くにコンビニはありますか？あと、駐車場は使えますか？',
    time: ago(45), source: 'guest', read: true,
  },
  {
    id: 104, bookingId: 5001, propertyId: 206100,
    message: '徒歩2分のところにセブンイレブンがあります。駐車場は1台分ご用意がありますので、そのままご利用ください。',
    time: ago(35), source: 'host', read: true, aiGenerated: false,
  },
  {
    id: 105, bookingId: 5001, propertyId: 206100,
    message: '了解です。あと、Wi-Fiのパスワードは部屋に書いてありますか？到着したらすぐにリモートワークをしたいので。',
    time: ago(8), source: 'guest', read: false,
  },
];

const MOCK_THREAD_2: ThreadMessage[] = [
  {
    id: 201, bookingId: 5002, propertyId: 206200,
    message: 'こんにちは。チェックアウトの時間を1時間延長することは可能ですか？フライトが午後なので…',
    time: ago(25), source: 'guest', read: false,
  },
];

const MOCK_THREAD_3: ThreadMessage[] = [
  {
    id: 301, bookingId: 5003, propertyId: 206100,
    message: 'お世話になっております。予約を確認したいのですが、朝食は含まれていますか？',
    time: ago(120), source: 'guest', read: true,
  },
  {
    id: 302, bookingId: 5003, propertyId: 206100,
    message: 'Maria様、お問い合わせありがとうございます。当施設は素泊まりプランとなっておりますが、近隣に美味しいカフェやレストランが多数ございます。おすすめリストをお送りしましょうか？',
    time: ago(110), source: 'host', read: true, aiGenerated: true,
  },
  {
    id: 303, bookingId: 5003, propertyId: 206100,
    message: 'はい、ぜひお願いします！あと、タオルは何枚ありますか？4人で泊まるので足りるか心配です。',
    time: ago(15), source: 'guest', read: false,
  },
];

const MOCK_MESSAGES: MessageCard[] = [
  {
    id: '1',
    bookingId: 5001,
    propertyId: 206100,
    guestName: 'John Smith',
    propertyName: '渋谷キャビン301',
    guestText: 'Wi-Fiのパスワードは部屋に書いてありますか？到着したらすぐにリモートワークをしたいので。',
    draft: 'John様、Wi-Fiのパスワードはリビングのテレビ横にあるカードに記載しております。SSID: Shibuya301_5G、パスワード: welcome2024 です。快適なリモートワークをお楽しみください。',
    time: ago(8),
    checkIn: '2026-03-15',
    checkOut: '2026-03-18',
    thread: MOCK_THREAD_1,
    type: 'reply',
  },
  {
    id: '2',
    bookingId: 5002,
    propertyId: 206200,
    guestName: 'Kim Soo-jin',
    propertyName: '新宿スイート502',
    guestText: 'チェックアウトの時間を1時間延長することは可能ですか？フライトが午後なので…',
    draft: 'Kim様、レイトチェックアウトのご希望承知いたしました。当日の予約状況を確認しましたところ、12:00までの延長が可能です。追加料金は2,000円となりますが、よろしいでしょうか？',
    time: ago(25),
    checkIn: '2026-03-13',
    checkOut: '2026-03-16',
    thread: MOCK_THREAD_2,
    type: 'reply',
  },
  {
    id: '3',
    bookingId: 5003,
    propertyId: 206100,
    guestName: 'Maria Garcia',
    propertyName: '渋谷キャビン301',
    guestText: 'タオルは何枚ありますか？4人で泊まるので足りるか心配です。',
    draft: 'Maria様、バスタオルとフェイスタオルを各4枚ずつご用意しております。また、予備のタオルもクローゼットの上段に置いてありますので、ご自由にお使いください。',
    time: ago(15),
    checkIn: '2026-03-20',
    checkOut: '2026-03-23',
    thread: MOCK_THREAD_3,
    type: 'reply',
  },
  {
    id: '4',
    bookingId: 5004,
    propertyId: 206200,
    guestName: 'David Chen',
    propertyName: '新宿スイート502',
    guestText: '',
    draft: 'David様、ご予約ありがとうございます。チェックインまであと2日となりました。アクセス方法やお部屋の設備について、ご不明な点がございましたらお気軽にお申し付けください。楽しいご滞在となりますよう、スタッフ一同お待ちしております。',
    time: ago(60),
    checkIn: '2026-03-15',
    checkOut: '2026-03-17',
    thread: [],
    type: 'proactive',
    triggerType: 'pre_checkin',
    triggerLabel: 'チェックイン前',
  },
  {
    id: '5',
    bookingId: 5005,
    propertyId: 206100,
    guestName: 'Sophie Laurent',
    propertyName: '渋谷キャビン301',
    guestText: '',
    draft: 'Sophie様、ご滞在はいかがでしたでしょうか？チェックアウトは明日11:00となっております。ゴミは分別して玄関横のボックスにお願いいたします。またのご利用を心よりお待ちしております。',
    time: ago(90),
    checkIn: '2026-03-10',
    checkOut: '2026-03-14',
    thread: [],
    type: 'proactive',
    triggerType: 'pre_checkout',
    triggerLabel: 'チェックアウト前',
  },
];

const MOCK_HISTORY: MessageCard[] = [
  {
    id: '100',
    bookingId: 4901,
    propertyId: 206100,
    guestName: 'Tanaka Yuki',
    propertyName: '渋谷キャビン301',
    guestText: 'エアコンの使い方がわかりません',
    draft: 'Tanaka様、エアコンのリモコンはベッドサイドのテーブルにございます。冷房は「冷房」ボタンを押してからご希望の温度に設定してください。',
    time: '2026-03-11T14:30:00',
    checkIn: '2026-03-10',
    checkOut: '2026-03-12',
    thread: [],
    type: 'reply',
  },
  {
    id: '101',
    bookingId: 4902,
    propertyId: 206200,
    guestName: 'Alex Johnson',
    propertyName: '新宿スイート502',
    guestText: '',
    draft: 'Alex様、ご予約ありがとうございます。チェックインのご案内です。',
    time: '2026-03-10T09:00:00',
    checkIn: '2026-03-12',
    checkOut: '2026-03-14',
    thread: [],
    type: 'proactive',
    triggerType: 'pre_checkin',
    triggerLabel: 'チェックイン前',
  },
];

const MOCK_PROPERTIES: Property[] = [
  { property_id: 206100, property_name: '渋谷キャビン301', pending_count: 3 },
  { property_id: 206200, property_name: '新宿スイート502', pending_count: 2 },
  { property_id: 206300, property_name: '浅草タウンハウス', pending_count: 0 },
];

const MOCK_SETTINGS: UserSettings = {
  supabase_user_id: 'dev-user',
  notify_new_message: true,
  notify_proactive: true,
  notify_reminder: false,
  line_fallback: true,
  ai_tone: 'friendly',
  ai_signature: '民泊スタッフ一同',
  theme: 'system',
};

function mockDelay<T>(data: T, ms = 300): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), ms));
}

// ─── API (with dev mock fallback) ───

export const api = {
  // Messages
  getMessages: (): Promise<{ messages: MessageCard[] }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ messages: MOCK_MESSAGES })
      : request('/api/messages'),

  getMessageHistory: (params: { status?: string; limit?: number; offset?: number }): Promise<{ messages: MessageCard[]; hasMore: boolean }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ messages: MOCK_HISTORY, hasMore: false })
      : request('/api/messages/history', { params: params as Record<string, string | number> }),

  getMessageDetail: (id: string | number): Promise<MessageDetail> => {
    if (DEV_SKIP_AUTH) {
      const msg = [...MOCK_MESSAGES, ...MOCK_HISTORY].find((m) => String(m.id) === String(id));
      if (!msg) return Promise.reject(new Error('Not found'));
      return mockDelay({
        message: msg,
        booking: { id: msg.bookingId, guestName: msg.guestName },
        thread: msg.thread,
        draft: msg.draft ? { draft_text: msg.draft, model: 'gemini-2.5-flash' } : null,
      });
    }
    return request(`/api/messages/${id}`);
  },

  sendMessage: (data: { messageId: string | number; bookingId: number; message: string }): Promise<{ ok: boolean }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ ok: true }, 500)
      : request('/api/app/send', { method: 'POST', body: data }),

  skipMessage: (data: { messageId: string | number }): Promise<{ ok: boolean }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ ok: true }, 500)
      : request('/api/app/skip', { method: 'POST', body: data }),

  // User
  getMe: (): Promise<{ user: { id: string; email: string }; properties: Property[]; settings: UserSettings }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ user: { id: 'dev', email: 'owner@minpaku.dev' }, properties: MOCK_PROPERTIES, settings: MOCK_SETTINGS })
      : request('/api/me'),

  // Devices
  registerDevice: (fcmToken: string, platform: string): Promise<{ ok: boolean }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ ok: true })
      : request('/api/devices', { method: 'POST', body: { fcm_token: fcmToken, platform } }),

  unregisterDevice: (fcmToken: string): Promise<{ ok: boolean }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ ok: true })
      : request(`/api/devices/${encodeURIComponent(fcmToken)}`, { method: 'DELETE' }),

  // Properties
  getProperties: (): Promise<{ properties: Property[] }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ properties: MOCK_PROPERTIES })
      : request('/api/properties'),

  // Bookings
  getBookings: (params?: { propertyId?: number }): Promise<{ bookings: Record<string, unknown>[] }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ bookings: [] })
      : request('/api/bookings', { params: params as Record<string, string | number> }),

  // Mark as read
  markAsRead: (messageId: string | number): Promise<{ ok: boolean }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ ok: true })
      : request(`/api/messages/${messageId}/read`, { method: 'POST' }),

  // Settings
  getSettings: (): Promise<{ settings: UserSettings }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ settings: MOCK_SETTINGS })
      : request('/api/settings'),

  updateSettings: (data: Partial<Omit<UserSettings, 'supabase_user_id'>>): Promise<{ settings: UserSettings }> =>
    DEV_SKIP_AUTH
      ? mockDelay({ settings: { ...MOCK_SETTINGS, ...data } })
      : request('/api/settings', { method: 'PUT', body: data }),

  // Onboarding
  submitOnboarding: (beds24RefreshToken: string): Promise<OnboardingResult> =>
    DEV_SKIP_AUTH
      ? mockDelay({ ok: true, properties: MOCK_PROPERTIES.map((p) => ({ property_id: p.property_id, property_name: p.property_name ?? '' })), message: '3物件が検出されました' })
      : request('/api/onboarding', { method: 'POST', body: { beds24_refresh_token: beds24RefreshToken } }),
};
