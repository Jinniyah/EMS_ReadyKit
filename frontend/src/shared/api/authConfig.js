/**
 * shared/api/authConfig.js
 * MSAL configuration for Azure AD authentication.
 *
 * Used only in production (VITE_APP_ENV=production).
 * In development, DevAuthProvider in useAuth.jsx replaces MSAL entirely.
 *
 * Environment variables are set via .env.local (never committed):
 *   VITE_AZURE_CLIENT_ID  — App Registration client ID
 *   VITE_AZURE_TENANT_ID  — Azure AD tenant ID
 */

export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID ?? '',
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_TENANT_ID ?? 'common'}`,
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: 'sessionStorage',
    storeAuthStateInCookie: false,
  },
  system: {
    loggerOptions: {
      loggerCallback: (level, message, containsPii) => {
        if (containsPii) return
        if (import.meta.env.VITE_APP_ENV === 'development') {
          console.debug('[MSAL]', message)
        }
      },
    },
  },
}

// Scopes requested when acquiring an access token for the API.
// The API audience matches the App Registration Application ID URI.
export const apiTokenRequest = {
  scopes: [`api://${import.meta.env.VITE_AZURE_CLIENT_ID}/user_impersonation`],
}
