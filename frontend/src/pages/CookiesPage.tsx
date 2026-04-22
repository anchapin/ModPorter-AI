/**
 * Cookie Policy Page
 */

import React from 'react';
import styles from './DocumentationSimple.module.css';

export const CookiesPage: React.FC = () => {
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Cookie Policy</h1>
        <p className={styles.subtitle}>
          Last updated:{' '}
          {new Date().toLocaleDateString('en-US', {
            month: 'long',
            day: 'numeric',
            year: 'numeric',
          })}
        </p>
      </header>

      <nav className={styles.navigation}>
        <a href="#what-are-cookies" className={styles.navLink}>
          What Are Cookies
        </a>
        <a href="#how-we-use" className={styles.navLink}>
          How We Use Cookies
        </a>
        <a href="#types" className={styles.navLink}>
          Types We Use
        </a>
        <a href="#third-party" className={styles.navLink}>
          Third-Party
        </a>
        <a href="#managing" className={styles.navLink}>
          Managing Cookies
        </a>
        <a href="#updates" className={styles.navLink}>
          Policy Updates
        </a>
      </nav>

      <section id="what-are-cookies" className={styles.section}>
        <h2 className={styles.sectionTitle}>1. What Are Cookies</h2>
        <p>
          Cookies are small text files stored on your device (computer, tablet,
          or mobile phone) when you visit a website. They help websites remember
          your preferences, login status, and provide a better browsing
          experience.
        </p>
        <p>
          Cookies are widely used across the internet to enable essential
          features, analytics, and marketing services. Our Cookie Policy
          explains what cookies we use and why.
        </p>
      </section>

      <section id="how-we-use" className={styles.section}>
        <h2 className={styles.sectionTitle}>2. How We Use Cookies</h2>
        <p>We use cookies to:</p>
        <ul>
          <li>Keep you logged into your account</li>
          <li>Remember your preferences and settings</li>
          <li>Understand how you use our Service</li>
          <li>Provide secure authentication</li>
          <li>Deliver and measure advertising (where applicable)</li>
          <li>Prevent fraud and ensure security</li>
        </ul>
      </section>

      <section id="types" className={styles.section}>
        <h2 className={styles.sectionTitle}>3. Types of Cookies We Use</h2>
        <h3 className={styles.sectionTitle}>Essential Cookies</h3>
        <p>
          These cookies are required for the Service to function properly. They
          enable core features like authentication, security, and session
          management.
        </p>
        <p>
          <strong>Cannot be disabled.</strong> These are necessary for the
          Service to work and do not require your consent.
        </p>
        <ul>
          <li>Session management cookies</li>
          <li>Security cookies</li>
          <li>Load balancing cookies</li>
        </ul>
        <h3 className={styles.sectionTitle}>Analytics Cookies</h3>
        <p>
          These cookies help us understand how visitors interact with our
          Service by collecting and reporting information anonymously. We use
          privacy-focused analytics tools that minimize data collection.
        </p>
        <ul>
          <li>Page views and navigation patterns</li>
          <li>Error occurrences</li>
          <li>Feature usage statistics</li>
        </ul>
        <p>
          Analytics cookies are optional and require your consent through our
          cookie banner.
        </p>
        <h3 className={styles.sectionTitle}>Functional Cookies</h3>
        <p>
          These cookies enable enhanced functionality and personalization, such
          as remembering your language preferences and settings.
        </p>
        <ul>
          <li>Language preferences</li>
          <li>Theme and display settings</li>
          <li>Recent conversion history</li>
        </ul>
        <p>Functional cookies are optional and require your consent.</p>
        <h3 className={styles.sectionTitle}>Marketing Cookies</h3>
        <p>
          We currently do not use marketing cookies. If this changes in the
          future, we will update this policy and obtain your consent through our
          cookie banner.
        </p>
      </section>

      <section id="third-party" className={styles.section}>
        <h2 className={styles.sectionTitle}>4. Third-Party Cookies</h2>
        <p>
          Some cookies are set by third-party services we use. These third
          parties have their own privacy policies governing their cookie usage.
        </p>
        <h3 className={styles.sectionTitle}>Authentication Providers</h3>
        <p>
          If you sign in using Google, GitHub, or Discord OAuth, these services
          may set cookies on your browser according to their privacy policies.
        </p>
        <ul>
          <li>
            Google:{' '}
            <a href="https://policies.google.com/privacy">Privacy Policy</a>
          </li>
          <li>
            GitHub:{' '}
            <a href="https://docs.github.com/en/privacy">Privacy Policy</a>
          </li>
          <li>
            Discord: <a href="https://discord.com/privacy">Privacy Policy</a>
          </li>
        </ul>
        <h3 className={styles.sectionTitle}>Analytics Providers</h3>
        <p>
          Our analytics tools may set cookies to collect usage data. We use
          privacy-focused alternatives to traditional tracking cookies.
        </p>
        <h3 className={styles.sectionTitle}>Payment Processors</h3>
        <p>
          Stripe, our payment processor, may set cookies when you complete a
          transaction. These cookies are governed by Stripe&apos;s privacy
          policy.
        </p>
      </section>

      <section id="managing" className={styles.section}>
        <h2 className={styles.sectionTitle}>
          5. Managing Your Cookie Preferences
        </h2>
        <p>
          You can manage your cookie preferences at any time through our cookie
          consent banner when you first visit our site, or by contacting us.
        </p>
        <h3 className={styles.sectionTitle}>Cookie Consent Banner</h3>
        <p>
          When you visit our Service, you will see a cookie consent banner that
          allows you to:
        </p>
        <ul>
          <li>Accept all cookies</li>
          <li>Reject non-essential cookies</li>
          <li>Customize your preferences</li>
        </ul>
        <h3 className={styles.sectionTitle}>Browser Settings</h3>
        <p>
          You can also manage cookies through your browser settings. Most
          browsers allow you to:
        </p>
        <ul>
          <li>Block all cookies</li>
          <li>Block third-party cookies only</li>
          <li>Delete existing cookies</li>
          <li>Allow cookies only from websites you trust</li>
          <li>Receive notifications when cookies are set</li>
        </ul>
        <p>
          Note: Blocking essential cookies may prevent the Service from
          functioning properly.
        </p>
        <h3 className={styles.sectionTitle}>Opt-Out Links</h3>
        <p>
          To opt out of analytics tracking, you can contact us at
          privacy@portkit.cloud. Some analytics tools also provide opt-out
          mechanisms through their respective websites.
        </p>
      </section>

      <section id="updates" className={styles.section}>
        <h2 className={styles.sectionTitle}>6. Policy Updates</h2>
        <p>
          We may update this Cookie Policy from time to time to reflect changes
          in our practices, technology, or legal requirements. Any updates will
          be posted on this page with an updated &quot;Last updated&quot; date.
        </p>
        <p>
          We encourage you to review this Cookie Policy periodically to stay
          informed about our use of cookies and related technologies.
        </p>
      </section>

      <section className={styles.section}>
        <h2 className={styles.sectionTitle}>Contact Us</h2>
        <p>
          If you have any questions about our use of cookies, please contact us:
        </p>
        <p>
          <strong>Email:</strong> privacy@portkit.cloud
          <br />
          <strong>Address:</strong> ModPorter AI, [Address]
        </p>
      </section>
    </div>
  );
};

export default CookiesPage;
