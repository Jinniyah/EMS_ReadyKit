# WP-02: Technology Choices Narrative

**FastAPI over Django or Rails.** The app is fundamentally a stateless API serving a PWA that needs to work reliably on a responder's phone in a rig with spotty signal. FastAPI's async support, automatic OpenAPI schema, and Pydantic validation gave a lightweight, fast backend without the overhead of a full framework built around server-rendered pages — none of which this project needed.

**React over a server-rendered framework.** The check wizard is a multi-step, stateful flow that needs to behave like an app, not a page: offline-tolerant, instant feedback on taps, and installable to a home screen. A PWA built on React gave that app-like feel while still shipping as static files, which kept hosting simple and cheap.

**Azure over AWS.** Azure AD (Entra ID) was the deciding factor: it gave the project enterprise-grade SSO and RS256 JWT-based auth without building or storing a single password. Pairing that with Static Web Apps for the frontend and App Service + PostgreSQL Flexible Server for the backend meant the whole stack could live in one ecosystem with one identity provider, which mattered for a solo developer maintaining everything alone.
