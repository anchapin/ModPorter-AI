import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import './styles/variables.css';
import './index.css';
import App from './App.tsx';
import * as Sentry from '@sentry/react';

// Initialize Sentry for error tracking
// Only initialize if SENTRY_DSN is provided in environment
const sentryDsn = import.meta.env.VITE_SENTRY_DSN;
if (sentryDsn) {
  Sentry.init({
    dsn: sentryDsn,
    environment: import.meta.env.MODE,
    release: `modporter-ai-frontend@${import.meta.env.VITE_APP_VERSION || '1.0.0'}`,
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        maskAllText: false,
        blockAllMedia: false,
      }),
    ],
    // Performance monitoring
    tracesSampleRate: parseFloat(
      import.meta.env.VITE_SENTRY_TRACES_SAMPLE_RATE || '0.1'
    ),
    // Session replay
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
    // Filter events
    beforeSend(event) {
      // Don't send events in development unless explicitly enabled
      if (
        import.meta.env.MODE === 'development' &&
        !import.meta.env.VITE_SENTRY_ENABLE_DEV
      ) {
        return null;
      }
      return event;
    },
  });
  console.log('Sentry error tracking initialized');
}

Sentry.captureConsoleIntegration();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
