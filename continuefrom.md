# Continue From Here — v1.1.0

## What Was Just Completed

### Track 1: AI Response Quality
- **Property rules** (`rules/property_206100.md`): Expanded from 32→150 lines with access info, recommended spots by category, cultural tips for foreign guests, expanded FAQ, check-in/out procedures, emergency contacts. Items marked `【要確認】` need real data from the owner.
- **Cultural tone guidance** (`ai_engine.py`): `_build_cultural_context()` adjusts AI tone based on guest origin (Western → friendly + Japan tips, Asian → polite), family status (kids → kid-friendly spots), group size (3+ adults → gentle noise reminder).
- **Language handling** (`ai_engine.py`): `_build_language_instruction()` with explicit "Write ENTIRE reply in {language}" instruction. Country→language fallback map (FR→French, DE→German, CN→Chinese, KR→Korean, etc.) for when `guestLanguage` field is empty.
- **User AI settings** (`ai_engine.py`, `sync_service.py`): Both `generate_reply` and `generate_proactive_message` accept `user_settings` param. Uses `ai_signature` and `ai_tone` (friendly/formal/casual). Sync service looks up owner settings via `user_properties` → `user_settings` table.

### Track 2: Mobile App
- **Backend endpoints** (`app.py`): `GET/PUT /api/settings`, `POST /api/onboarding` (validates Beds24 refresh token, detects properties from bookings table, associates user).
- **Inbox filter tabs** (`app/(tabs)/index.tsx`): 3 filter tabs (すべて / 返信 / プロアクティブ) with client-side filtering on `type` field.
- **Settings screen** (`app/(tabs)/settings.tsx`): Notification toggles (3 switches), Beds24 connection status + re-onboard button, AI tone selector (3 buttons), signature text input.
- **Onboarding flow** (`app/(onboarding)/`): 3-screen wizard — Beds24 token input → property detection → push notification permission → redirect to tabs.
- **AuthGate** (`app/_layout.tsx`): Checks if authenticated user has properties, redirects to onboarding if empty.
- **useSettings hook** (`hooks/useSettings.ts`): Query + optimistic mutation for user settings.
- **API client** (`lib/api.ts`): Added `getSettings`, `updateSettings`, `submitOnboarding`. Fixed `Property` type to match backend snake_case keys.

### Bug Fixes
- Fixed `user["sub"]` → `user["id"]` in device unregister endpoint (pre-existing bug).

### Tests
- 188 tests passing (151 existing + 37 new).
- New test file: `tests/test_new_features.py` covers cultural context, language handling, user settings in prompts, settings/onboarding endpoints, and owner settings lookup in sync service.

---

## What Needs To Be Done Next

### 1. Mobile App Testing (Expo Go) — HIGH PRIORITY
The mobile app features are coded but untested on a real device. Run:
```bash
cd minpaku-dx-app
npx expo start
```

Test these flows:
- [ ] **Inbox filter tabs**: Tap すべて / 返信 / プロアクティブ, verify filtering works
- [ ] **Settings screen**: Toggle notification switches, change AI tone, edit signature — verify they persist (requires backend running with Supabase auth)
- [ ] **Onboarding flow**: Log in as a new user with no properties → should redirect to `/(onboarding)/beds24-token` → enter token → see detected properties → enable notifications → land on tabs
- [ ] **AuthGate redirect**: Existing user with properties should skip onboarding and go straight to tabs

### 2. Fill in 【要確認】 in Property Rules
`rules/property_206100.md` has placeholder `【要確認】` markers. The AI is instructed to NOT use these. Get real info from the owner for:
- WiFi password
- Exact walking time from Hirai station
- Nearest convenience store / supermarket names
- Key box location and procedure
- Parking info (nearest coin parking)
- Laundry machine details

### 3. Deploy to Railway
Push to production. The sync service will automatically use the new AI prompts for all future messages. Existing `draft_ready` messages won't be re-generated — only new incoming messages.

### 4. Future Improvements (from airesponsebrainstorm.md)
- Phase 2: Response quality scoring, A/B testing different prompt strategies
- Phase 3: Multi-property support with per-property rules
- Per-property Beds24 tokens (current MVP uses global env var token)

---

## Architecture Notes for New Developers

### Key Files
| File | Purpose |
|------|---------|
| `app.py` | FastAPI server — LINE webhook, web dashboard, mobile API |
| `ai_engine.py` | Gemini AI prompt construction and generation |
| `sync_service.py` | Background sync: Beds24 → DB → AI → LINE/push |
| `db.py` | Database abstraction (SQLite local / PostgreSQL prod) |
| `beds24.py` | Beds24 API client |
| `auth.py` | Supabase JWT verification for mobile endpoints |
| `rules/property_*.md` | Per-property knowledge base for AI |

### Mobile App Stack
- Expo Router (file-based routing)
- React Query for data fetching
- Zustand for client state
- Supabase Auth for authentication

### How AI Drafts Work
1. `sync_service.py` runs every 5 min
2. Pulls unread guest messages from Beds24
3. For each message: loads property rules → builds prompt with cultural context + language instruction + user settings → calls Gemini → saves draft to DB → sends LINE notification + push notification
4. Owner approves/edits/skips via LINE or mobile app
5. Approved message sent back to Beds24

### Database
- `DATABASE_URL` env var: PostgreSQL (Supabase) in production, SQLite locally
- Key tables: `messages`, `ai_drafts`, `bookings`, `proactive_messages`, `user_settings`, `user_properties`, `devices`
