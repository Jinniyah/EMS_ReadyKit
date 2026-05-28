import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { MsalProvider } from '@azure/msal-react'
import { PublicClientApplication } from '@azure/msal-browser'

import App from './App.jsx'
import { DevAuthProvider } from './shared/hooks/useAuth.jsx'
import { msalConfig } from './shared/api/authConfig.js'

// Global styles
import './index.css'

// Wizard, station, submitted-screen, and reconcile styles — consolidated into
// one file during Session B refactor (REF-5). Previously split across:
//   ./wizard.css, ./wizard-station.css, ./submitted-screen-patch.css
// Those files have been deleted from src/ root.
import './styles/wizard.css'

const isDev = import.meta.env.VITE_APP_ENV !== 'production'
const msalInstance = isDev ? null : new PublicClientApplication(msalConfig)

function Root() {
  if (isDev) {
    return (
      <DevAuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </DevAuthProvider>
    )
  }
  return (
    <MsalProvider instance={msalInstance}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MsalProvider>
  )
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Root />
  </React.StrictMode>
)
