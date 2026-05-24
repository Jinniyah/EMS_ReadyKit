/**
 * shared/api/authConfig.js
 * MSAL configuration for Azure AD authentication.
 *
 * Used only in production (VITE_APP_ENV=production).
 * In development, DevAuthProvider in useAuth.jsx replaces MSAL entirely.
 *
 * Required GitHub secrets (injected at build time by deploy.yml):
 *   VITE_AZURE_AD_CLIENT_ID  — App Registration client ID
 *   VITE_AZURE_AD_TENANT_ID  — Azure AD tenant ID
 */

export const msalConfig = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_AD_CLIENT_ID ?? '',
    authority: `https://login.microsoftonline.com/${import.meta.env.VITE_AZURE_AD_TENANT_ID ?? 'common'}`,
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

export const apiTokenRequest = {
  scopes: [`api://${import.meta.env.VITE_AZURE_AD_CLIENT_ID}/user_impersonation`],
}
