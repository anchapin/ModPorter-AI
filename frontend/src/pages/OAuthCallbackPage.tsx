/**
 * OAuth Callback Page
 * Handles OAuth callback redirects and extracts tokens from URL
 * Issue #980: Add OAuth login (Discord, GitHub, Google)
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { authClient } from '../api/auth';

export const OAuthCallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const { provider } = useParams<{ provider: string }>();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleCallback = async () => {
      const urlParams = new URLSearchParams(window.location.search);
      const code = urlParams.get('code');
      const errorParam = urlParams.get('error');
      const errorDescription = urlParams.get('error_description');

      if (errorParam) {
        setError(errorDescription || `OAuth error: ${errorParam}`);
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      if (!code) {
        setError('No authorization code received');
        setTimeout(() => navigate('/login'), 3000);
        return;
      }

      try {
        const response = await fetch(
          `/api/v1/auth/oauth/${provider}/callback?code=${code}`,
          {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'OAuth callback failed');
        }

        const data = await response.json();
        authClient.storeToken('access_token', data.access_token);
        authClient.storeToken('refresh_token', data.refresh_token);

        if (data.is_new_user) {
          navigate('/dashboard?welcome=true');
        } else {
          navigate('/dashboard');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Authentication failed');
        setTimeout(() => navigate('/login'), 3000);
      }
    };

    handleCallback();
  }, [navigate, provider]);

  if (error) {
    return (
      <div className="oauth-callback-page oauth-callback-error">
        <div className="oauth-callback-content">
          <h2>Authentication Failed</h2>
          <p>{error}</p>
          <p>Redirecting to login page...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="oauth-callback-page oauth-callback-loading">
      <div className="oauth-callback-content">
        <h2>Completing Sign In...</h2>
        <p>Please wait while we complete your authentication.</p>
      </div>
    </div>
  );
};

export default OAuthCallbackPage;
