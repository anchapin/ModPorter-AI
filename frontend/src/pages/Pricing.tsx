/**
 * Pricing Page - Subscription Plans
 */

import React, { useState } from 'react';
import styles from './Pricing.module.css';

interface PricingTier {
  name: string;
  price: number;
  period: string;
  description: string;
  features: string[];
  highlighted?: boolean;
  buttonText: string;
  conversionsPerMonth: number;
  popular?: boolean;
}

const pricingTiers: PricingTier[] = [
  {
    name: 'Free',
    price: 0,
    period: 'forever',
    description: 'Perfect for trying out ModPorter AI',
    conversionsPerMonth: 5,
    buttonText: 'Get Started',
    features: [
      '5 conversions per month',
      'Basic conversion support',
      'Community Discord access',
      'Standard processing speed',
      'Basic QA reports'
    ]
  },
  {
    name: 'Pro',
    price: 19,
    period: 'month',
    description: 'For regular mod converters',
    conversionsPerMonth: 50,
    highlighted: true,
    popular: true,
    buttonText: 'Start Pro Trial',
    features: [
      '50 conversions per month',
      'Advanced conversion support',
      'Priority processing speed',
      'Detailed QA reports',
      'Smart Assumptions enabled',
      'Email support'
    ]
  },
  {
    name: 'Studio',
    price: 49,
    period: 'month',
    description: 'For mod developers and studios',
    conversionsPerMonth: 200,
    buttonText: 'Start Studio Trial',
    features: [
      '200 conversions per month',
      'Premium conversion support',
      'Fastest processing speed',
      'Full QA reports with insights',
      'Smart Assumptions enabled',
      'Priority email support',
      'API access',
      'Custom add-on templates'
    ]
  },
  {
    name: 'Enterprise',
    price: 199,
    period: 'month',
    description: 'For large teams and organizations',
    conversionsPerMonth: -1, // unlimited
    buttonText: 'Contact Sales',
    features: [
      'Unlimited conversions',
      'Dedicated support manager',
      'Custom processing queues',
      'Advanced analytics dashboard',
      'White-label options',
      'SLA guarantee',
      'Custom integrations',
      'On-premise deployment option',
      'Team collaboration features'
    ]
  }
];

export const Pricing: React.FC = () => {
  const [billingPeriod, setBillingPeriod] = useState<'monthly' | 'yearly'>('monthly');
  const [hoveredTier, setHoveredTier] = useState<string | null>(null);

  const getPrice = (tier: PricingTier) => {
    if (billingPeriod === 'yearly' && tier.price > 0) {
      return Math.round(tier.price * 0.8); // 20% discount
    }
    return tier.price;
  };

  const getSavings = (tier: PricingTier) => {
    if (tier.price > 0 && billingPeriod === 'yearly') {
      return Math.round(tier.price * 12 * 0.2);
    }
    return 0;
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Simple, Transparent Pricing</h1>
        <p className={styles.subtitle}>
          Choose the plan that fits your needs. All plans include access to our AI-powered conversion engine.
        </p>
      </header>

      {/* Billing Toggle */}
      <div className={styles.billingToggle}>
        <span className={billingPeriod === 'monthly' ? styles.activeLabel : ''}>
          Monthly
        </span>
        <button
          className={`${styles.toggle} ${billingPeriod === 'yearly' ? styles.toggleYearly : ''}`}
          onClick={() => setBillingPeriod(billingPeriod === 'monthly' ? 'yearly' : 'monthly')}
          aria-label="Toggle billing period"
        >
          <span className={styles.toggleKnob} />
        </button>
        <span className={billingPeriod === 'yearly' ? styles.activeLabel : ''}>
          Yearly
          <span className={styles.discountBadge}>Save 20%</span>
        </span>
      </div>

      {/* Pricing Cards */}
      <div className={styles.pricingGrid}>
        {pricingTiers.map((tier) => (
          <div
            key={tier.name}
            className={`${styles.pricingCard} ${tier.highlighted ? styles.highlighted : ''} ${hoveredTier === tier.name ? styles.hovered : ''}`}
            onMouseEnter={() => setHoveredTier(tier.name)}
            onMouseLeave={() => setHoveredTier(null)}
          >
            {tier.popular && (
              <div className={styles.popularBadge}>Most Popular</div>
            )}
            
            <div className={styles.cardHeader}>
              <h2 className={styles.tierName}>{tier.name}</h2>
              <p className={styles.tierDescription}>{tier.description}</p>
            </div>

            <div className={styles.priceSection}>
              <div className={styles.price}>
                <span className={styles.currency}>$</span>
                <span className={styles.amount}>{getPrice(tier)}</span>
                {tier.price > 0 && (
                  <span className={styles.period}>/{billingPeriod === 'yearly' ? 'mo' : tier.period}</span>
                )}
              </div>
              {billingPeriod === 'yearly' && tier.price > 0 && (
                <div className={styles.savings}>
                  Save ${getSavings(tier)}/year
                </div>
              )}
            </div>

            <div className={styles.conversions}>
              {tier.conversionsPerMonth === -1 ? (
                <span className={styles.unlimited}>Unlimited conversions</span>
              ) : (
                <span>{tier.conversionsPerMonth} conversions/month</span>
              )}
            </div>

            <ul className={styles.featuresList}>
              {tier.features.map((feature, index) => (
                <li key={index} className={styles.featureItem}>
                  <span className={styles.checkIcon}>✓</span>
                  {feature}
                </li>
              ))}
            </ul>

            <button
              className={`${styles.ctaButton} ${tier.highlighted ? styles.primaryButton : styles.secondaryButton}`}
            >
              {tier.buttonText}
            </button>
          </div>
        ))}
      </div>

      {/* Enterprise Call-to-Action */}
      <div className={styles.enterpriseCTA}>
        <div className={styles.enterpriseContent}>
          <h2>Need a custom solution?</h2>
          <p>
            We offer tailored plans for large organizations with specific requirements.
            Get dedicated support, custom integrations, and flexible processing options.
          </p>
          <a href="mailto:enterprise@modporter.ai" className={styles.enterpriseButton}>
            Contact Our Sales Team
          </a>
        </div>
      </div>

      {/* FAQ Link */}
      <div className={styles.faqLink}>
        <p>Have questions about pricing?</p>
        <a href="/faq">Check our FAQ →</a>
      </div>

      {/* Money-back Guarantee */}
      <div className={styles.guarantee}>
        <span className={styles.guaranteeIcon}>🛡️</span>
        <div>
          <strong>30-Day Money-Back Guarantee</strong>
          <p>Try risk-free. If you're not satisfied, get a full refund within 30 days.</p>
        </div>
      </div>
    </div>
  );
};

export default Pricing;
