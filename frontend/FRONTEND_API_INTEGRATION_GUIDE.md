# Frontend API Integration Guide

This document explains how the frontend should integrate with the current Prism backend from authentication through the latest market phases. It is written for a frontend engineer who needs to replace demo data with real backend calls and do it in a professional, maintainable way.

The backend is cookie-based. That means the frontend should not build around access tokens stored in local storage or session storage. Authentication state should come from secure cookies and `/auth/me`.

The current API envelope is consistent across auth and market routes:

```json
{
  "success": true,
  "message": "Human readable message",
  "data": {}
}
```

On errors, the backend returns:

```json
{
  "success": false,
  "message": "Error message",
  "data": null
}
```

Validation errors are slightly different because they include a validation list:

```json
{
  "success": false,
  "message": "Validation error",
  "errors": [
    {
      "field": "email",
      "message": "value is not a valid email address"
    }
  ],
  "data": null
}
```

Your frontend API layer should understand all three shapes.

## Base URL Strategy

Do not hardcode URLs directly inside page components. Use environment variables.

For local development, the frontend should ideally use a same-origin dev proxy instead of calling the backend host directly from the browser.

That means:

```text
frontend runs on http://127.0.0.1:5173
browser calls /api/v1/...
Vite proxies /api to http://127.0.0.1:8000
```

The actual FastAPI backend still runs on:

```text
http://127.0.0.1:8000
```

For the deployed backend, the current base is:

```text
https://prism-60b21aab4083.herokuapp.com/api/v1
```

Important note: the deployed backend currently does not yet reflect the latest market/live-state changes. It is an older deployment from when auth had first been set up. So in practice, local development should be treated as the source of truth until the latest backend is deployed.

In a Vite app, the recommended environment variable is:

```text
VITE_API_BASE_URL
```

For the frontend-only admin route prefix, also use:

```text
VITE_ADMIN_ROUTE_PREFIX
```

A professional setup would look like this.

`.env.local`

```env
# optional; if omitted, local frontend falls back to the dev proxy path
# VITE_API_BASE_URL=/api/v1
VITE_ADMIN_ROUTE_PREFIX=/control-room
```

`.env.production`

```env
VITE_API_BASE_URL=https://prism-60b21aab4083.herokuapp.com/api/v1
VITE_ADMIN_ROUTE_PREFIX=/control-room
```

Then create one API client file, for example:

```ts
// frontend/src/lib/api/client.ts
import axios from 'axios'

const LOCAL_API_BASE_URL = '/api/v1'
const LIVE_API_BASE_URL = 'https://prism-60b21aab4083.herokuapp.com/api/v1'

function isLocalFrontendHost(hostname: string) {
  return hostname === 'localhost' || hostname === '127.0.0.1' || hostname === '::1'
}

function resolveApiBaseUrl() {
  const envBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim()
  if (envBaseUrl) {
    return envBaseUrl
  }

  if (typeof window !== 'undefined' && isLocalFrontendHost(window.location.hostname)) {
    return LOCAL_API_BASE_URL
  }

  return LIVE_API_BASE_URL
}

export const api = axios.create({
  baseURL: resolveApiBaseUrl(),
  withCredentials: true,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
})
```

This is the professional fallback order:

1. `VITE_API_BASE_URL` wins when explicitly set
2. if no env is set and the frontend is running on `localhost` or `127.0.0.1`, the client talks to the local FastAPI backend
3. otherwise it falls back to the deployed backend

That gives you local-first testing without having to keep editing source files every time you switch between local development and deployment.

For local work, the most reliable setup is the proxy path because it avoids cross-site cookie problems completely.

One important local cookie note: if your backend runs on `http://127.0.0.1:8000`, the frontend should also be opened on `127.0.0.1`, not `localhost`. Browsers can treat `localhost` and `127.0.0.1` as different sites for cookie purposes. The current Vite config should therefore run the frontend on:

```text
http://127.0.0.1:5173
```

That keeps local cookie behavior aligned with the backend host.

The Vite dev server should also proxy API traffic:

```ts
// vite.config.ts
server: {
  host: '127.0.0.1',
  port: 5173,
  proxy: {
    '/api': {
      target: 'http://127.0.0.1:8000',
      changeOrigin: false,
      secure: false,
    },
  },
}
```

## Source-Aware Markets

The market APIs are now source-aware. Frontend should treat `source` as a first-class request parameter, not just a local UI filter.

Allowed values:

```text
bayse
polymarket
```

If `source` is omitted on discovery, the backend returns the mixed discovery feed.

Examples:

```text
GET /api/v1/events?currency=NGN
GET /api/v1/events?currency=NGN&source=bayse
GET /api/v1/events?currency=NGN&source=polymarket
```

Detail and tracking routes are also source-aware:

```text
GET    /api/v1/events/{event_id}?source=bayse
GET    /api/v1/events/{event_id}?source=polymarket
POST   /api/v1/track/{event_id}?source=bayse
POST   /api/v1/track/{event_id}?source=polymarket
DELETE /api/v1/track/{event_id}?source=bayse
DELETE /api/v1/track/{event_id}?source=polymarket
```

Important frontend rule:

- when a card is clicked, carry the source into the route search state
- when track/untrack is clicked, send the same source back to the backend

For example, a TanStack Router detail navigation should look like:

```ts
navigate({
  to: `/app/events/${event.id}`,
  search: { source: event.source.toLowerCase() },
})
```

Then the detail page should read `search.source` and pass it into the API call.

## Discovery Feed Ordering

The mixed discovery feed is intentionally backend-curated:

- first 3 cards are Bayse
- remaining cards are Polymarket ranked by liquidity/activity

So the frontend should not reorder that mixed feed on its own.

If the user clicks the Bayse or Poly filter buttons, the frontend should re-fetch from the backend with `source=...` instead of trying to filter the already-loaded mixed list locally.

## Currency Notes

Prism defaults to `NGN` at the app level, but Polymarket cards still come back as `USD`.

That is expected.

Frontend should render whatever `event.currency` says for each card/detail response instead of assuming the page-level currency applies to all sources uniformly.

## Admin Discovery

Admin discovery is also source-aware:

```text
GET /api/v1/admin/discovery?currency=NGN
GET /api/v1/admin/discovery?currency=NGN&source=bayse
GET /api/v1/admin/discovery?currency=NGN&source=polymarket
```

System tracking actions must also carry source:

```text
POST   /api/v1/admin/system-track/{event_id}?source=polymarket
DELETE /api/v1/admin/system-track/{event_id}?source=polymarket
```

## UI Guidance

Do not redesign the app because Polymarket was added.

New market-source behavior should still follow the existing Prism visual system:

- same card shell
- same typography
- same spacing rhythm
- same button treatment
- same loading skeleton style

The source badge should be enough to distinguish Bayse from Polymarket. Do not create a separate “Polymarket theme”.

With this setup, the browser only talks to `127.0.0.1:5173`, and Vite forwards API calls to FastAPI. That is why cookies work much more reliably in local development.

If you use `fetch` instead of Axios, the important equivalent is:

```ts
credentials: 'include'
```

Without that, cookie auth will not work.

## Demo Features That Must Be Removed

The frontend currently still depends on mock/demo data and demo-access behavior. That needs to be removed before proper integration.

The main files to delete or refactor away from are:

```text
frontend/src/data/mockEvents.ts
frontend/src/pages/app/DiscoveryPage.tsx
frontend/src/pages/app/TrackerPage.tsx
frontend/src/pages/app/EventDetail.tsx
frontend/src/pages/ExplanationPage.tsx
```

The current `mockEvents.ts` file defines types and fake event data that no longer match the backend contract. It should not remain as a fallback source for real pages. If you want to keep frontend types in one place, keep the type definitions but remove the fake data array.

The frontend also needs to remove any demo flow that bypasses authentication just to “see inside the app”. That is no longer acceptable once cookie auth is the real auth model. App pages should rely on real backend auth state, not mock access.

In routing, the app should also be cleaned up so protected pages do not behave like public demo pages. The current route naming in `frontend/src/router.tsx` also has this issue:

```ts
path: '/events/$marketId'
```

That route is actually working with an event id, not a market id. Rename it to:

```ts
path: '/events/$eventId'
```

and update the component accordingly.

## The Recommended Frontend API Structure

Do not call `axios` directly inside every page. Create a small API layer and a small adapter layer.

The clean separation is:

```text
frontend/src/lib/api/client.ts
frontend/src/lib/api/auth.ts
frontend/src/lib/api/markets.ts
frontend/src/lib/api/types.ts
frontend/src/lib/api/adapters.ts
```

The reason for the adapter layer is that your current UI shape does not exactly match the backend response shape. For example, the current frontend mock model uses `id`, `title`, and `outcomes`, while the backend uses `event_id`, `event_title`, and `markets`.

Instead of forcing backend responses straight into UI components, define backend-facing types and map them into presentation models.

## Auth Endpoints

All auth routes are under:

```text
/auth
```

### `POST /auth/signup`

Request body:

```json
{
  "email": "user@example.com",
  "password": "secret123",
  "confirm_password": "secret123"
}
```

Success response:

```json
{
  "success": true,
  "message": "Signup successful, an OTP has been sent to your email to verify your account.",
  "data": {
    "uid": "uuid",
    "email": "user@example.com",
    "email_verified": false
  }
}
```

Important behavior: signup also sets auth cookies. The frontend should not expect token strings in the body.

Very important frontend flow note: the signup response contains the `uid` that the OTP verification route needs. That means the signup page should navigate to the OTP page with both:

```ts
{
  email,
  uid,
}
```

Do not build OTP verification around email alone.

### `POST /auth/verify-otp`

Request body:

```json
{
  "uid": "uuid",
  "otp": "123456",
  "otp_type": "signup"
}
```

or:

```json
{
  "uid": "uuid",
  "otp": "123456",
  "otp_type": "forgotpassword"
}
```

For `signup`, success means the account is now verified.

The frontend should call this route with:

```ts
await authApi.verifyOTP(uid, otp, 'signup')
```

not with `{ email, otp }`.

For the Prism UX, once signup OTP verification succeeds, redirect straight to the main authenticated app page. Do not send the user back to login, because the backend already has enough information to set the auth cookies again on successful verification.

For `forgotpassword`, success returns:

```json
{
  "uid": "uuid",
  "reset_token": "..."
}
```

### `POST /auth/resend-otp`

Request body:

```json
{
  "email": "user@example.com",
  "otp_type": "signup"
}
```

or:

```json
{
  "email": "user@example.com",
  "otp_type": "forgotpassword"
}
```

### `POST /auth/forgot-password`

Request body:

```json
{
  "email": "user@example.com"
}
```

### `POST /auth/reset-password`

Request body:

```json
{
  "reset_token": "...",
  "new_password": "new-secret"
}
```

### `POST /auth/login`

Request body:

```json
{
  "email": "user@example.com",
  "password": "secret123"
}
```

This route is JSON-based. Do not send `application/x-www-form-urlencoded` and do not use an OAuth2 form helper here.

Success response:

```json
{
  "success": true,
  "message": "Login successful",
  "data": {
    "uid": "uuid",
    "email": "user@example.com",
    "email_verified": true
  }
}
```

Again, tokens are not returned in the body. The backend sets cookies.

### `POST /auth/renew-access-token`

No request body is required on the frontend. The backend reads the refresh cookie automatically.

Use this when a protected request fails with `401` and you want a silent session refresh attempt before redirecting the user to login.

Do not call this blindly before any session exists. The safer pattern is:

1. try `/auth/me`
2. if it returns `401`, try `/auth/renew-access-token`
3. if renew also returns `401`, redirect to login

### `POST /auth/logout`

No request body is required. The backend clears the cookies.

### `GET /auth/me`

This is the canonical way to determine whether the current browser session is authenticated.

The frontend should call `/auth/me` when the app boots or when a protected route loads. If it succeeds, the user is authenticated. If it returns `401`, the app should redirect to login.

## Market Endpoints

All market routes are under:

```text
/api/v1
```

Since your configured base URL already includes `/api/v1`, the frontend client should call:

```text
/events
/events/:eventId
/track/:eventId
/tracker
```

not the full prefixed path again.

All market routes currently require authentication, so the frontend must only call them from an authenticated context or handle `401` cleanly.

### Currency Handling

Where supported, the frontend can pass:

```text
?currency=USD
```

or:

```text
?currency=NGN
```

If the frontend wants a consistent experience, keep a global market currency preference in app state and pass it on:

```text
GET /events?currency=USD
GET /events/{eventId}?currency=USD
POST /track/{eventId}?currency=USD
DELETE /track/{eventId}?currency=USD
GET /tracker?currency=USD
```

### `GET /events`

This is the discovery feed.

Success response shape:

```json
{
  "success": true,
  "message": "Discovery events fetched successfully",
  "data": [
    {
      "event_id": "string",
      "event_title": "string",
      "event_slug": "string | null",
      "source": "bayse",
      "currency": "USD",
      "event_type": "single | combined",
      "category": "string | null",
      "status": "string | null",
      "engine": "AMM | CLOB",
      "total_liquidity": 123.45,
      "event_total_orders": 20,
      "closing_date": "ISO datetime | null",
      "tracked_markets_count": 2,
      "tracking_enabled": true,
      "last_updated": "ISO datetime | null",
      "ai_insight": "Insight unavailable",
      "highest_scoring_market": {
        "market_id": "string",
        "market_title": "string",
        "current_probability": 0.63,
        "probability_delta": 0.04,
        "signal": {
          "score": 67.4,
          "classification": "moderate",
          "direction": "RISING",
          "formula": "CLOB: ...",
          "factors": {},
          "notes": [],
          "detected_at": "ISO datetime | null"
        }
      }
    }
  ]
}
```

This route is now safe for the frontend to use instead of the old `mockEvents` discovery cards.

### `GET /events/{eventId}`

This is the event detail route.

Success response shape:

```json
{
  "success": true,
  "message": "Event detail fetched successfully",
  "data": {
    "event_id": "string",
    "event_title": "string",
    "event_slug": "string | null",
    "source": "bayse",
    "currency": "USD",
    "event_type": "single | combined",
    "category": "string | null",
    "status": "string | null",
    "engine": "AMM | CLOB",
    "total_liquidity": 123.45,
    "event_total_orders": 20,
    "closing_date": "ISO datetime | null",
    "tracked_markets_count": 2,
    "tracking_enabled": true,
    "last_updated": "ISO datetime | null",
    "ai_insight": "Insight unavailable",
    "highest_scoring_market": { "...": "..." },
    "markets": [
      {
        "market_id": "string",
        "market_title": "string",
        "market_image_url": "string | null",
        "market_image_128_url": "string | null",
        "rules": "string | null",
        "yes_outcome_id": "string",
        "yes_outcome_label": "Yes",
        "no_outcome_id": "string",
        "no_outcome_label": "No",
        "current_probability": 0.63,
        "inverse_probability": 0.37,
        "market_total_orders": 12,
        "probability_delta": 0.04,
        "event_liquidity": 123.45,
        "signal": {
          "score": 67.4,
          "classification": "moderate",
          "direction": "RISING",
          "formula": "CLOB: ...",
          "factors": {},
          "notes": [],
          "detected_at": "ISO datetime | null"
        },
        "last_updated": "ISO datetime | null"
      }
    ]
  }
}
```

This is the route the current `EventDetail` page should use.

### `POST /track/{eventId}`

This is the user action route for tracking an event. The backend tracks the markets under it.

Success response:

```json
{
  "success": true,
  "message": "Event tracked successfully",
  "data": {
    "event_id": "string",
    "event_title": "string",
    "event_slug": "string | null",
    "source": "bayse",
    "currency": "USD",
    "event_type": "single | combined",
    "engine": "AMM | CLOB",
    "tracked_markets_count": 2,
    "tracking_enabled": true
  }
}
```

### `DELETE /track/{eventId}`

This disables tracking for the current user. The backend uses a soft disable, not a hard delete. From the frontend point of view, the event is simply removed from the user’s tracked set.

### `GET /tracker`

This returns the user’s tracked event summaries. It is the correct route for the tracker page.

The shape is similar to discovery, but only for the user’s tracked events.

## How To Handle The Current Signal Model

The current backend signal model is:

```json
{
  "score": 0.0,
  "classification": "unscored | noise | weak | moderate | strong | high_conviction",
  "direction": "RISING | FALLING | STABLE",
  "formula": "string | null",
  "factors": {},
  "notes": [],
  "detected_at": "ISO datetime | null"
}
```

This does not match the old demo types exactly. The frontend should stop using:

```ts
'INFORMED_MOVE' | 'NOISE' | 'UNCERTAIN'
```

and instead adopt the backend classifications directly. If the design team wants prettier labels, create a presentation mapper:

```ts
noise -> Noise
weak -> Weak signal
moderate -> Moderate conviction
strong -> Strong signal
high_conviction -> High conviction
unscored -> Unscored
```

Do not distort the backend values at the API boundary.

## AI Insight Placeholder Handling

AI explanation is not ready yet, but the backend always returns:

```text
Insight unavailable
```

for the `ai_insight` field.

This is intentional. The frontend should still render the insight block at its intended height. Do not hide it conditionally. Use the placeholder text and preserve layout height so the page structure remains stable when AI explanations are added later.

## Suggested Frontend Mapping Layer

The current UI mock types are not a clean match to the backend types. The professional solution is to create adapters instead of bending the API or the UI randomly.

For example:

```ts
export function mapDiscoveryEvent(apiEvent: DiscoveryEventApi): DiscoveryCardViewModel {
  return {
    id: apiEvent.event_id,
    title: apiEvent.event_title,
    source: apiEvent.source,
    eventType: apiEvent.event_type,
    totalLiquidity: apiEvent.total_liquidity ?? 0,
    lastUpdated: apiEvent.last_updated,
    aiInsight: apiEvent.ai_insight,
    highestScoringMarket: apiEvent.highest_scoring_market,
  }
}
```

That gives you freedom to change component props without forcing a backend contract rewrite every time.

## Error Handling Recommendations

The frontend should centralize HTTP error handling.

For protected routes:

1. If a request returns `401`, try `POST /auth/renew-access-token`
2. If renew succeeds, retry the original request once
3. If renew fails, redirect to login

For validation errors:

1. Read `message`
2. If `errors` exists, map them into form field errors

For business errors:

1. Show the backend `message`
2. Do not replace it with a generic “Something went wrong” unless you truly have no backend message

## Route Protection Recommendations

The frontend app should have an auth bootstrap flow. On app mount:

1. Call `/auth/me`
2. If success, keep the user in app routes
3. If failure, redirect to login

Do not keep the old “demo bypass” that lets a user see internal pages without a real session.

## What The Frontend Can Safely Build Now

With the current backend, the frontend can now safely build and connect:

1. Signup
2. Login
3. OTP verification
4. Forgot password flow
5. Protected discovery page
6. Protected tracker page
7. Protected event detail page
8. Track/untrack actions

The frontend should not wait for the AI layer before integrating. The placeholder is already in place for layout stability.

## Admin API

The backend now has a separate admin namespace:

```text
/admin
```

This is not just another page. It is a restricted RBAC surface. The frontend must treat it as a separate protected area. Do not reuse the old demo bypass logic here. Every admin page should first confirm the session is an actual admin session.

The recommended admin page flow is:

1. admin login page
2. admin shell/layout
3. admin overview dashboard
4. admin discovery page
5. admin system-tracker page

### `POST /admin/login`

Request body:

```json
{
  "email": "admin@example.com",
  "password": "very-secure-password"
}
```

This uses the same cookie auth system as the rest of the app. There is no separate token system for admin. The difference is RBAC. The backend checks that the account role is actually `admin`.

### `GET /admin/me`

Use this the same way you use `/auth/me`, but specifically for the admin area. If this fails, the frontend should kick the user out of admin pages immediately.

### `GET /admin/overview`

This is the main admin dashboard route. It now includes:

```text
registered user counts
verified user counts
admin user counts
system-tracked market counts
system-tracked event counts
user-tracked event counts
most tracked events
recent signal snapshot counts
system status
system tracked event summaries
```

Example payload shape:

```json
{
  "success": true,
  "message": "Admin overview fetched successfully",
  "data": {
    "total_users": 120,
    "verified_users": 98,
    "admin_users": 1,
    "total_user_tracked_events": 17,
    "total_user_event_links": 42,
    "total_system_tracked_events": 6,
    "total_system_tracked_markets": 14,
    "recent_signal_snapshot_count": 28,
    "most_tracked_events": [
      {
        "event_id": "string",
        "event_title": "string",
        "event_slug": "string | null",
        "tracker_count": 8,
        "market_count": 2,
        "system_tracked": true
      }
    ],
    "system_tracked_events": [],
    "system_status": {
      "redis_ok": true,
      "websocket": {
        "connected": true,
        "background_task_running": true,
        "subscription_sync_running": true,
        "active_subscription_count": 9,
        "last_connect_at": "ISO datetime | null",
        "last_message_at": "ISO datetime | null",
        "reconnect_count": 0,
        "last_error": "string | null",
        "baseline_cache_size": 11
      }
    }
  }
}
```

This is the route the admin dashboard should use for summary cards and operational visibility.

### `GET /admin/analytics`

This exposes the analytics part directly, without bundling it into the rest of the overview payload. Use this if the frontend wants analytics cards to load separately.

### `GET /admin/system-status`

This exposes the operational health part directly:

```text
Redis status
websocket status
active subscription count
last websocket message time
reconnect count
```

The `websocket` field is now nested by source:

```json
{
  "websocket": {
    "bayse": { "...": "..." },
    "polymarket": { "...": "..." }
  },
  "background_jobs": {
    "baseline_scheduler_running": true,
    "discovery_worker_running": true
  }
}
```

So the admin UI should render Bayse and Polymarket status separately instead of assuming one flat websocket object.

This should live only in the admin area, not in the user-facing product.

### `GET /admin/discovery`

This is the admin discovery page. It is specifically for **system tracking discovery**.

That means the `tracking_enabled` flag here should be interpreted as:

```text
is this event currently being tracked by the system?
```

not:

```text
is this admin user personally tracking it?
```

The purpose of this page is to let admins choose which events should become part of Prism’s richer tracked universe, so user discovery does not remain only a lite REST listing.

### `GET /admin/system-tracker`

This returns the events currently tracked by the system, not just by users.

### `POST /admin/system-track/{eventId}`

This tells the backend to mark an event as system-tracked. The backend then stores the markets under it, warms Redis state, and refreshes baselines.

### `DELETE /admin/system-track/{eventId}`

This removes the event from system tracking.

### `GET /admin/audit-logs`

This returns admin action history for important admin actions like adding or removing events from the system-tracked list.

This matters because system tracking is global, but Prism should still know **which admin performed the change**.

## Admin Bootstrap Script

The script to manually create or rotate an admin user is:

```text
backend/admin/bootstrap_admin.py
```

This script does **not** contain an admin password in the repo. It requires:

```text
PRISM_ADMIN_BOOTSTRAP_SECRET
```

from the environment, plus an interactive password entry at runtime.

That means cloning the repo alone is not enough to become admin.

### Important RBAC note

The frontend should never decide admin status from UI assumptions alone. It should always rely on the backend response from `/admin/me` or the failure of admin endpoints. Admin page routing should guard on real backend-confirmed role.

### Admin route strategy on the frontend

The frontend should **not** use an obvious public route like:

```text
/admin
```

for the admin UI shell.

Instead, define the admin frontend route prefix through an environment variable, for example:

```text
VITE_ADMIN_ROUTE_PREFIX=/control-room
```

or:

```text
VITE_ADMIN_ROUTE_PREFIX=/ops-console
```

This is not the primary security measure. Real security is still the backend RBAC checks. But it is still good practice not to make the admin UI route unnecessarily obvious.

So the rule is:

```text
non-obvious frontend admin route
strict backend RBAC
cookie auth with admin-only verification
```

## Updated Product Reality

The backend is now beyond simple REST snapshots. It includes:

```text
Bayse REST ingestion
Bayse websocket ingestion
Redis live state
Redis signal state
periodic baseline refresh
signal snapshot persistence
admin diagnostics surface
```

That means the frontend can now safely build for a real Bayse-first MVP product instead of a pure mock-driven prototype.

The two pieces still intentionally missing are:

```text
AI explanation generation
Polymarket integration
```

The frontend should therefore:

1. render the insight block using the placeholder value from the API
2. avoid building hard dependencies on Polymarket until its integration is actually shipped

## Admin UI Styling Requirement

The new admin pages should follow the existing visual language of the website. Do not build a generic off-the-shelf “blue-gray admin dashboard” that feels disconnected from the current Prism brand.

Keep the same feel by reusing:

```text
the current typography system
the existing spacing rhythm
existing card radius and border language
existing buttons and layout shell
the same color discipline already used in the app
```

That means the admin area should feel like a protected extension of Prism, not like a separate product.

The cleanest layout is:

```text
top summary metric strip
main two-column dashboard section
most tracked events panel
system health / websocket status panel
system tracked events table or card list
admin discovery page using the same event-card family
```

If the frontend team wants to add new components, they should style them by extending the existing component system in:

```text
frontend/src/components/ui
frontend/src/components/layout
```

instead of inventing a separate admin-only design language.

## Final Integration Advice

Treat local backend integration as the main target until the latest backend is deployed. Keep environment variables in place from day one. Remove the mock data and auth bypass paths now instead of trying to support “temporary demo mode” beside the real app. Build one shared API client with `withCredentials: true`, one set of backend-facing TypeScript interfaces, and one adapter layer between API shapes and UI shapes.

That is the cleanest and most maintainable way to connect the current Prism frontend to the current Prism backend.
