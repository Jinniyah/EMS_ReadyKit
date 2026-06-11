# ADR-006: Azure AD Token Lifetime and Session Management

**Status:** Accepted  
**Date:** 2026-06-11  
**Decision Owner:** EMS ReadyKit Project  

---

## Context

EMS ReadyKit authenticates users via Azure Active Directory (Azure AD) using the
MSAL.js library on the frontend. The backend validates RS256-signed JWTs on every
request. We need to document the token lifetime defaults and explain any operational
implications for EMS personnel using the app during a shift.

## Azure AD Default Token Lifetimes

| Token type | Default lifetime | Notes |
|------------|-----------------|-------|
| Access token | 1 hour | Used to call backend API. Non-configurable per-app unless a Token Lifetime Policy is applied. |
| Refresh token | 24 hours (single session) / 90 days (multi-session, sliding) | MSAL silently refreshes the access token before expiry using the refresh token. |
| ID token | 1 hour | Used by MSAL to identify the user. Renewed alongside the access token. |

**Effective session duration:** Up to 90 days of unattended use as long as the
user opens the app at least once every 90 days. In practice, a crew member starting
a shift opens the app, MSAL silently refreshes the access token in the background,
and the user never sees a login prompt during normal use.

## Behavior When a Token Expires Mid-Shift

MSAL.js silently acquires a new access token before the 1-hour window closes by
calling the `/token` endpoint in the background. The user is not interrupted.

If the refresh token has also expired (90-day inactivity) or if the user's account
is disabled in Azure AD, the silent refresh fails. MSAL then requires an interactive
login. In the EMS context:

- The app renders a login redirect.
- Any unsaved draft check data is preserved in `localStorage` and can be resumed
  after re-authentication (see `useDraft.js`).
- No check data is lost.

## HTTPSRedirectMiddleware Decision (I-3 / SEC-H1)

`HTTPSRedirectMiddleware` is intentionally NOT added to the FastAPI application.
Azure App Service terminates TLS at the load balancer and forwards plain HTTP to
the container. The middleware cannot inspect `X-Forwarded-Proto`, so it would
redirect every request to HTTPS, causing an infinite redirect loop.

HTTPS enforcement is handled by Azure App Service's **"HTTPS Only"** platform setting,
which redirects HTTP → HTTPS at the edge before the request reaches the container.
This provides the same security guarantee without the middleware.

## Consequences

- No custom token lifetime policy is needed — Azure AD defaults are appropriate for
  this application's shift-based usage pattern.
- If compliance requirements change (e.g., a shorter idle timeout is mandated),
  apply an Azure AD Conditional Access policy rather than changing application code.
- The 90-day refresh token sliding window means a device that is not used for 90+
  days will require a new login. Acceptable for volunteer EMS where the app may be
  unused for extended periods.
