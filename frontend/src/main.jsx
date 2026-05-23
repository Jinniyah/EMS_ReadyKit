import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { MsalProvider } from '@azure/msal-react'
import { PublicClientApplication } from '@azure/msal-browser'

import App from './App.jsx'
import { DevAuthProvider } from './shared/hooks/useAuth.jsx'
import { msalConfig } from './shared/api/authConfig.js'
import './index.css'
import './wizard.css'
import './wizard-station.css'
import './submitted-screen-patch.css'

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
