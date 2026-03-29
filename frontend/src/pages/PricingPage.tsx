import React, { useState } from 'react';
import './PricingPage.css';

interface PricingTier {
  name: string;
  price: string;
  period: string;
  description: string;
  features: string[];
  cta: string;
  popular?: boolean;
  pricePerMonth?: number;
}

const pricingTiers: PricingTier[] = [
  {
    name: 'Free',
    price: '$0',
    period: 'forever',
    description: 'Perfect for testing and hobbyists',
    features: [
      '5 conversions per month',
      'Simple to moderate mods',
      'Community support (Discord)',
      'Basic conversion reports',
      'Standard processing speed',
    ],
    cta: 'Get Started',
  },
  {
    name: 'Pro',
    price: '$9.99',
    period: '/month',
    pricePerMonth: 9.99,
    description: 'For serious mod creators',
    popular: true,
    features: [
      'Unlimited conversions',
      'Complex mods (entities, dimensions)',
      'Priority email support (24hr response)',
      'Advanced features (API, batch processing)',
      'Visual editor access',
      'Faster processing speed',
      'Conversion history (90 days)',
      'No ModPorter branding',
    ],
    cta: 'Start Free Trial',
  },
  {
    name: 'Studio',
    price: '$29.99',
    period: '/month',
    pricePerMonth: 29.99,
    description: 'For teams and studios',
    features: [
      'Everything in Pro',
      'Team collaboration (up to 10 seats)',
      'API access (1,000 calls/month)',
      'Custom templates',
      'White-label options',
      'Dedicated support (Slack)',
      'Conversion history (1 year)',
      'Advanced analytics',
    ],
    cta: 'Contact Sales',
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: 'pricing',
    description: 'For large organizations',
    features: [
      'Everything in Studio',
      'On-premise deployment',
      'Unlimited API access',
      'Custom integrations',
      'Dedicated support manager',
      'SLA guarantees (99.9% uptime)',
      'Unlimited storage',
      'Training and onboarding',
    ],
    cta: 'Contact Sales',
  },
];

const faqs = [
  {
    question: 'Can I change plans anytime?',
    answer:
      'Yes! You can upgrade, downgrade, or cancel your subscription at any time from your account settings. Changes take effect at the end of your billing period.',
  },
  {
    question: 'What payment methods do you accept?',
    answer:
      'We accept all major credit cards (Visa, MasterCard, American Express), PayPal, and wire transfers for Enterprise plans. All payments are processed securely through Stripe.',
  },
  {
    question: 'Is there a free trial for paid plans?',
    answer:
      'Yes! Pro and Studio plans include a 14-day free trial with full access to all features. No credit card required to start.',
  },
  {
    question: 'What happens if I exceed my limits?',
    answer:
      "Free tier: Conversions pause until next month. Pro/Studio: No hard limits on conversions. API calls: You'll be notified at 80% and can purchase additional capacity or upgrade your plan.",
  },
  {
    question: 'Can I get a refund?',
    answer:
      "We offer a 30-day money-back guarantee for all paid plans. If you're not satisfied, contact support for a full refund. No questions asked.",
  },
  {
    question: 'Do you offer discounts for education or non-profits?',
    answer:
      'Yes! We offer 50% off for educational institutions and registered non-profits. Contact sales@modporter.ai with your documentation.',
  },
];

const comparison = [
  {
    feature: 'Conversions per month',
    free: '5',
    pro: 'Unlimited',
    studio: 'Unlimited',
    enterprise: 'Unlimited',
  },
  {
    feature: 'Mod complexity',
    free: 'Simple to moderate',
    pro: 'Up to complex',
    studio: 'Any complexity',
    enterprise: 'Any complexity',
  },
  {
    feature: 'API access',
    free: 'No',
    pro: '1,000 calls/mo',
    studio: '10,000 calls/mo',
    enterprise: 'Unlimited',
  },
  {
    feature: 'Team seats',
    free: '1',
    pro: '1',
    studio: '10',
    enterprise: 'Unlimited',
  },
  {
    feature: 'Support',
    free: 'Community (Discord)',
    pro: 'Email (24hr)',
    studio: 'Slack (4hr)',
    enterprise: 'Dedicated (1hr)',
  },
  {
    feature: 'Storage',
    free: '1 GB',
    pro: '10 GB',
    studio: '100 GB',
    enterprise: 'Unlimited',
  },
  {
    feature: 'Conversion history',
    free: '7 days',
    pro: '90 days',
    studio: '1 year',
    enterprise: 'Forever',
  },
  {
    feature: 'White-label',
    free: 'No',
    pro: 'No',
    studio: 'Yes',
    enterprise: 'Yes',
  },
  {
    feature: 'SLA guarantee',
    free: 'No',
    pro: 'No',
    studio: 'No',
    enterprise: '99.9%',
  },
];

export const PricingPage: React.FC = () => {
  const [annualBilling, setAnnualBilling] = useState(false);
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  const handleGetStarted = (tier: string) => {
    if (tier === 'Free') {
      window.location.assign('/signup');
    } else if (tier === 'Pro') {
      window.location.assign('/signup?plan=pro&trial=14');
    } else {
      window.location.assign('mailto:sales@modporter.ai?subject=Enterprise%20or%20Studio%20Plan%20Inquiry');
    }
  };

  const getPrice = (tier: PricingTier): string => {
    if (tier.pricePerMonth && annualBilling) {
      const annualPrice = Math.floor(tier.pricePerMonth * 12 * 0.83); // 17% discount
      return `$${annualPrice}`;
    }
    return tier.price;
  };

  const getPeriod = (tier: PricingTier): string => {
    if (tier.pricePerMonth && annualBilling) {
      return '/year';
    }
    return tier.period;
  };

  return (
    <div className="pricing-page">
      {/* Hero Section */}
      <section className="pricing-hero">
        <div className="container">
          <h1 className="pricing-title">Simple, Transparent Pricing</h1>
          <p className="pricing-subtitle">
            Choose the plan that fits your needs. All plans include our core AI
            conversion technology.
          </p>

          {/* Billing Toggle */}
          <div className="billing-toggle">
            <span className={`billing-label ${!annualBilling ? 'active' : ''}`}>
              Monthly
            </span>
            <button
              className={`toggle-switch ${annualBilling ? 'active' : ''}`}
              onClick={() => setAnnualBilling(!annualBilling)}
              aria-label="Toggle annual billing"
            >
              <div className="toggle-slider" />
            </button>
            <span className={`billing-label ${annualBilling ? 'active' : ''}`}>
              Yearly <span className="save-badge">Save 17%</span>
            </span>
          </div>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pricing-cards">
        <div className="container">
          <div className="pricing-grid">
            {pricingTiers.map((tier) => (
              <div
                key={tier.name}
                className={`pricing-card ${tier.popular ? 'popular' : ''}`}
              >
                {tier.popular && (
                  <div className="popular-badge">Most Popular</div>
                )}
                <div className="card-header">
                  <h3 className="tier-name">{tier.name}</h3>
                  <div className="tier-price">
                    <span className="price">{getPrice(tier)}</span>
                    <span className="period">{getPeriod(tier)}</span>
                  </div>
                  <p className="tier-description">{tier.description}</p>
                </div>
                <ul className="tier-features">
                  {tier.features.map((feature, index) => (
                    <li key={index} className="feature-item">
                      <svg
                        className="feature-icon"
                        width="20"
                        height="20"
                        viewBox="0 0 20 20"
                        fill="currentColor"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
                <button
                  className={`cta-button ${tier.popular ? 'primary' : 'secondary'}`}
                  onClick={() => handleGetStarted(tier.name)}
                >
                  {tier.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Feature Comparison */}
      <section className="comparison-section">
        <div className="container">
          <h2 className="section-title">Feature Comparison</h2>
          <div className="comparison-table-wrapper">
            <table className="comparison-table">
              <thead>
                <tr>
                  <th>Feature</th>
                  <th>Free</th>
                  <th className="highlight-column">Pro</th>
                  <th>Studio</th>
                  <th>Enterprise</th>
                </tr>
              </thead>
              <tbody>
                {comparison.map((row, index) => (
                  <tr key={index}>
                    <td className="feature-name">{row.feature}</td>
                    <td>{row.free}</td>
                    <td className="highlight-column">{row.pro}</td>
                    <td>{row.studio}</td>
                    <td>{row.enterprise}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="faq-section">
        <div className="container">
          <h2 className="section-title">Frequently Asked Questions</h2>
          <div className="faq-list">
            {faqs.map((faq, index) => (
              <div key={index} className="faq-item">
                <button
                  className={`faq-question ${expandedFaq === index ? 'expanded' : ''}`}
                  onClick={() =>
                    setExpandedFaq(expandedFaq === index ? null : index)
                  }
                >
                  {faq.question}
                  <svg
                    className={`faq-icon ${expandedFaq === index ? 'rotated' : ''}`}
                    width="20"
                    height="20"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
                {expandedFaq === index && (
                  <div className="faq-answer">
                    <p>{faq.answer}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="pricing-cta">
        <div className="container">
          <h2>Ready to convert your mods?</h2>
          <p>Join thousands of modders already using ModPorter AI</p>
          <div className="cta-buttons">
            <button
              className="cta-button primary"
              onClick={() => (window.location.href = '/signup')}
            >
              Start Free Trial
            </button>
            <button
              className="cta-button secondary"
              onClick={() => (window.location.href = '/docs')}
            >
              Read Documentation
            </button>
          </div>
        </div>
      </section>
    </div>
  );
};

export default PricingPage;
