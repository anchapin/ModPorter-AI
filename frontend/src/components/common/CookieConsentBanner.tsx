/**
 * Cookie Consent Banner Component
 */

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

interface CookieConsentBannerProps {
  onAccept?: () => void;
  onDecline?: () => void;
}

export const CookieConsentBanner: React.FC<CookieConsentBannerProps> = ({
  onAccept,
  onDecline,
}) => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const consent = localStorage.getItem('cookie_consent');
    if (!consent) {
      setIsVisible(true);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem('cookie_consent', 'accepted');
    setIsVisible(false);
    onAccept?.();
  };

  const handleDecline = () => {
    localStorage.setItem('cookie_consent', 'declined');
    setIsVisible(false);
    onDecline?.();
  };

  if (!isVisible) {
    return null;
  }

  return (
    <div className="cookie-consent-banner">
      <div className="cookie-consent-content">
        <div className="cookie-consent-text">
          <h3>We value your privacy</h3>
          <p>
            We use cookies to enhance your browsing experience, serve
            personalized content, and analyze our traffic. By clicking
            &quot;Accept&quot;, you consent to our use of cookies.
          </p>
          <div className="cookie-consent-links">
            <Link to="/cookies">Cookie Policy</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/terms">Terms of Service</Link>
          </div>
        </div>
        <div className="cookie-consent-actions">
          <button
            className="cookie-consent-btn cookie-consent-decline"
            onClick={handleDecline}
          >
            Decline
          </button>
          <button
            className="cookie-consent-btn cookie-consent-accept"
            onClick={handleAccept}
          >
            Accept
          </button>
        </div>
      </div>
    </div>
  );
};

export default CookieConsentBanner;
