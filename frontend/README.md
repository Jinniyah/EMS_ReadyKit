# EMS ReadyKit Frontend

React PWA for the EMS ReadyKit inventory and vehicle readiness platform.

## Local development

### Prerequisites
- Node.js 20+
- The FastAPI backend running locally at `http://localhost:8000`

### Setup

```bash
cd frontend
npm install
npm run dev
```

The Vite dev server starts at `http://localhost:5173`.  
API calls to `/api/*` are proxied to the local FastAPI backend automatically — no CORS configuration needed.

### Dev authentication

When `VITE_APP_ENV=development` (the default), the app skips real MSAL authentication and uses a **fake token** menu instead. You'll see a dev banner at the top of every page with role-switcher buttons:

- **Test Administrator** — full access
- **Test Supervisor** — station management
- **Test Responder** — check submission only

This maps to the same fake tokens the FastAPI backend accepts (`Bearer test-administrator`, etc.).

To test against the real Azure AD (production auth), set:
```
VITE_APP_ENV=production
VITE_AZURE_CLIENT_ID=<your-client-id>
VITE_AZURE_TENANT_ID=<your-tenant-id>
```

### Running tests

```bash
npm test            # run once
npm run test:watch  # watch mode
```

### Building for production

```bash
npm run build       # outputs to dist/
npm run preview     # serve the dist/ build locally
```

## Project structure

```
src/
  main.jsx              # React root, MSAL provider, router
  App.jsx               # Top-level routes and ErrorBoundary wiring
  shared/
    api/
      client.js         # Fetch wrapper — attaches auth token, handles errors
    components/
      ErrorBoundary.jsx # Catches module crashes; renders inline error state
      UserPill.jsx      # Logged-in user identity on every screen
      StatusBadge.jsx   # Color+label status chip (PASS/FAIL/NEEDS_RESTOCK)
      Spinner.jsx       # Loading indicator
      Modal.jsx         # Confirmation dialog base component
    hooks/
      useAuth.jsx        # Auth state — real MSAL or dev fake token
      useDraft.js       # localStorage draft save/resume for daily checks
      useApi.js         # Data fetching with loading/error state
    utils/
      statusCalc.js     # Maps API status strings → UI color/label/icon
      dateHelpers.js    # Date formatting, ISO string helpers
      roleGuard.js      # Role-based render guards
  modules/
    check-wizard/       # Phase 5B — daily check workflow
    item-management/    # Phase 5D — add/remove items
    vehicle-status/     # Phase 5E — inactive toggle, repair requests
    supervisor-dashboard/ # Phase 5F — calendar, compliance, print
    user-management/    # Phase 5G — onboarding requests
    feedback/           # Phase 5G — bug reports, enhancements
    help/               # Phase 5C — tutorial, FAQ, contextual help
    supply-room/        # Phase 5G — restock workflow
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_APP_ENV` | `development` | `development` or `production` |
| `VITE_API_BASE_URL` | `` (proxy) | Override API base URL (leave blank in dev) |
| `VITE_AZURE_CLIENT_ID` | — | Azure AD App Registration client ID |
| `VITE_AZURE_TENANT_ID` | — | Azure AD tenant ID |

Copy `.env.example` to `.env.local` and fill in values for production testing.
