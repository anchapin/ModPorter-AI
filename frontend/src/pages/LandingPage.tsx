import React, { useState } from 'react';
import './LandingPage.css';
import { Link } from 'react-router-dom';

const benchmarks = [
  {
    label: 'Avg. Texture Coverage',
    value: '68%',
    description: 'Across 30 real-world mods',
  },
  {
    label: 'Avg. Model Coverage',
    value: '68%',
    description: 'Java block/entity geometry',
  },
  {
    label: 'Conversions',
    value: '100%',
    description: 'Zero crashes in testing',
  },
  {
    label: 'Time Saved',
    value: '60-80%',
    description: 'Manual work reduction',
  },
];

const features = [
  {
    icon: '⚡',
    title: 'Automated Conversion',
    description:
      'Handles the tedious 60-80% of Java→Bedrock work automatically. Textures, models, recipes, entities and more.',
  },
  {
    icon: '📊',
    title: 'Detailed Conversion Report',
    description:
      'Clear report shows exactly what converted and what needs manual work. No guesswork.',
  },
  {
    icon: '🎯',
    title: 'Professional-Grade Output',
    description:
      'Marketplace-ready .mcaddon files that meet Microsoft submission standards.',
  },
  {
    icon: '🔧',
    title: 'Smart AI Assumptions',
    description:
      'Intelligent handling of ambiguous cases with documented fallback decisions.',
  },
];

const steps = [
  { number: '1', title: 'Upload', description: 'Drop your Java mod JAR file' },
  { number: '2', title: 'Convert', description: 'AI processes the conversion' },
  {
    number: '3',
    title: 'Review Report',
    description: 'See coverage breakdown',
  },
  {
    number: '4',
    title: 'Finish Manual',
    description: 'Complete remaining work',
  },
];

const testimonials = [
  {
    quote:
      'ModPorter cut my conversion time from 3 weeks to 4 days. The report feature is a game-changer.',
    author: 'Alex M.',
    role: 'Marketplace Creator',
    mods: '15+ mods ported',
  },
  {
    quote:
      'Finally, a tool that understands the complexity of modern Java mods. The entity conversion is impressive.',
    author: 'Jordan K.',
    role: 'Mod Author',
    mods: 'Create framework specialist',
  },
  {
    quote:
      'The hybrid approach makes sense. Automated conversion with clear manual work items.',
    author: 'Sam R.',
    role: 'Studio Lead',
    mods: 'Team of 5 modders',
  },
];

const faqs = [
  {
    question: 'What about IP and licensing?',
    answer:
      "ModPorter processes your mod locally. We don't store or retain your files. You retain all rights to your converted content.",
  },
  {
    question: 'What quality should I expect?',
    answer:
      'Most mods achieve 60-80% automatic coverage. The detailed report shows exactly what needs review. Complex mods may require more manual work.',
  },
  {
    question: 'What manual work remains?',
    answer:
      'Typically: custom textures, advanced AI behaviors, complex recipe chains, and 3rd party mod integrations. The report pinpoints exactly what.',
  },
  {
    question: 'How does the Marketplace tier work?',
    answer:
      'For commercial use on Minecraft Marketplace, we offer licensing plans with priority support and dedicated conversion assistance.',
  },
  {
    question: 'Is there a free tier?',
    answer:
      'Yes! Free tier includes 5 conversions per month for testing and hobby projects. Pro and Studio tiers offer unlimited conversions.',
  },
];

const footerLinks = {
  documentation: [
    { label: 'Getting Started', href: '/docs' },
    { label: 'Conversion Guide', href: '/docs/conversion' },
    { label: 'API Reference', href: '/docs/api' },
    { label: 'Troubleshooting', href: '/docs/troubleshooting' },
  ],
  company: [
    { label: 'About', href: '/about' },
    { label: 'Blog', href: '/blog' },
    { label: 'Careers', href: '/careers' },
    { label: 'Contact', href: '/contact' },
  ],
  legal: [
    { label: 'Terms of Service', href: '/terms' },
    { label: 'Privacy Policy', href: '/privacy' },
    { label: 'Cookie Policy', href: '/cookies' },
  ],
  social: [
    { label: 'GitHub', href: 'https://github.com/anchapin/ModPorter-AI' },
    { label: 'Discord', href: 'https://discord.gg/modporter' },
    { label: 'Twitter', href: 'https://twitter.com/modporterai' },
  ],
};

const LandingPage: React.FC = () => {
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  return (
    <div className="landing-page">
      {/* SEO Meta Tags - these would be set via react-helmet or similar in production */}
      <head>
        <title>ModPorter AI — Java to Bedrock Conversion Accelerator</title>
        <meta
          name="description"
          content="Convert Minecraft Java Edition mods to Bedrock Edition 60-80% automatically. Detailed conversion reports, professional-grade output for Marketplace creators."
        />
        <meta
          property="og:title"
          content="ModPorter AI — Conversion Accelerator"
        />
        <meta
          property="og:description"
          content="Convert Java mods to Bedrock 60-80% automatically with detailed reports."
        />
        <meta property="og:type" content="website" />
        <meta name="twitter:card" content="summary_large_image" />
      </head>

      {/* Navigation */}
      <nav className="landing-nav">
        <div className="nav-container">
          <div className="nav-logo">
            <span className="logo-icon">🎮</span>
            <span className="logo-text">ModPorter AI</span>
          </div>
          <div className="nav-links">
            <a href="#features">Features</a>
            <a href="#how-it-works">How It Works</a>
            <a href="#benchmarks">Benchmarks</a>
            <a href="#pricing">Pricing</a>
            <a href="/docs">Docs</a>
          </div>
          <div className="nav-actions">
            <Link to="/login" className="nav-link-login">
              Log In
            </Link>
            <Link to="/signup" className="nav-cta">
              Start Free
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="hero-section">
        <div className="hero-container">
          <div className="hero-badge">B2B Ready — Marketplace Creators</div>
          <h1 className="hero-title">
            Get Your Java Mods on the
            <br />
            <span className="hero-highlight">Marketplace Faster</span>
          </h1>
          <p className="hero-subtitle">
            ModPorter AI handles 60-80% of Java→Bedrock conversion
            automatically. Detailed reports show exactly what needs manual work
            — no guesswork.
          </p>
          <div className="hero-cta-group">
            <Link to="/convert" className="hero-cta primary">
              Start Converting Free
            </Link>
            <a href="#how-it-works" className="hero-cta secondary">
              See How It Works
            </a>
          </div>
          <div className="hero-stats">
            <div className="stat">
              <span className="stat-value">295+</span>
              <span className="stat-label">Marketplace Partners</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-value">30+</span>
              <span className="stat-label">Mods Tested</span>
            </div>
            <div className="stat-divider" />
            <div className="stat">
              <span className="stat-value">68%</span>
              <span className="stat-label">Avg. Coverage</span>
            </div>
          </div>
        </div>
      </section>

      {/* Benchmarks Section */}
      <section id="benchmarks" className="benchmarks-section">
        <div className="section-container">
          <h2 className="section-title">Real Conversion Benchmarks</h2>
          <p className="section-subtitle">
            Tested across 30 real-world Java mods from the community
          </p>
          <div className="benchmarks-grid">
            {benchmarks.map((benchmark, index) => (
              <div key={index} className="benchmark-card">
                <div className="benchmark-value">{benchmark.value}</div>
                <div className="benchmark-label">{benchmark.label}</div>
                <div className="benchmark-description">
                  {benchmark.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="features-section">
        <div className="section-container">
          <h2 className="section-title">Everything You Need to Go to Market</h2>
          <p className="section-subtitle">
            Built for professional modders who need reliable, repeatable
            conversion
          </p>
          <div className="features-grid">
            {features.map((feature, index) => (
              <div key={index} className="feature-card">
                <div className="feature-icon">{feature.icon}</div>
                <h3 className="feature-title">{feature.title}</h3>
                <p className="feature-description">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="how-it-works-section">
        <div className="section-container">
          <h2 className="section-title">Simple Workflow</h2>
          <p className="section-subtitle">
            From upload to marketplace-ready in four steps
          </p>
          <div className="steps-container">
            {steps.map((step, index) => (
              <div key={index} className="step-card">
                <div className="step-number">{step.number}</div>
                <h3 className="step-title">{step.title}</h3>
                <p className="step-description">{step.description}</p>
                {index < steps.length - 1 && (
                  <div className="step-arrow">→</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Social Proof Section */}
      <section className="social-proof-section">
        <div className="section-container">
          <h2 className="section-title">Trusted by Marketplace Creators</h2>
          <div className="testimonials-grid">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="testimonial-card">
                <div className="testimonial-quote">"{testimonial.quote}"</div>
                <div className="testimonial-author">
                  <div className="author-name">{testimonial.author}</div>
                  <div className="author-role">{testimonial.role}</div>
                  <div className="author-mods">{testimonial.mods}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="pricing-section">
        <div className="section-container">
          <h2 className="section-title">Simple Pricing</h2>
          <p className="section-subtitle">
            Free tier for testing, paid plans for commercial use
          </p>
          <div className="pricing-grid">
            <div className="pricing-card">
              <div className="pricing-tier">Free</div>
              <div className="pricing-price">$0</div>
              <div className="pricing-period">forever</div>
              <ul className="pricing-features">
                <li>5 conversions/month</li>
                <li>Basic conversion reports</li>
                <li>Community support</li>
              </ul>
              <Link to="/signup" className="pricing-cta">
                Get Started
              </Link>
            </div>
            <div className="pricing-card featured">
              <div className="popular-badge">Most Popular</div>
              <div className="pricing-tier">Pro</div>
              <div className="pricing-price">$9.99</div>
              <div className="pricing-period">/month</div>
              <ul className="pricing-features">
                <li>Unlimited conversions</li>
                <li>Advanced reports</li>
                <li>Priority support</li>
                <li>API access</li>
              </ul>
              <Link to="/signup?plan=pro" className="pricing-cta primary">
                Start Free Trial
              </Link>
            </div>
            <div className="pricing-card">
              <div className="pricing-tier">Marketplace</div>
              <div className="pricing-price">Custom</div>
              <div className="pricing-period">licensing</div>
              <ul className="pricing-features">
                <li>Commercial use rights</li>
                <li>Dedicated support</li>
                <li>Custom integrations</li>
                <li>SLA guarantee</li>
              </ul>
              <a href="mailto:sales@modporter.ai" className="pricing-cta">
                Contact Sales
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="faq-section">
        <div className="section-container">
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
                  <span
                    className={`faq-icon ${expandedFaq === index ? 'rotated' : ''}`}
                  >
                    ▼
                  </span>
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

      {/* Footer */}
      <footer className="landing-footer">
        <div className="footer-container">
          <div className="footer-brand">
            <div className="footer-logo">
              <span className="logo-icon">🎮</span>
              <span className="logo-text">ModPorter AI</span>
            </div>
            <p className="footer-tagline">
              Java to Bedrock conversion for the Minecraft community.
            </p>
          </div>
          <div className="footer-links-grid">
            <div className="footer-column">
              <h4>Documentation</h4>
              <ul>
                {footerLinks.documentation.map((link, index) => (
                  <li key={index}>
                    <a href={link.href}>{link.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div className="footer-column">
              <h4>Company</h4>
              <ul>
                {footerLinks.company.map((link, index) => (
                  <li key={index}>
                    <a href={link.href}>{link.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div className="footer-column">
              <h4>Legal</h4>
              <ul>
                {footerLinks.legal.map((link, index) => (
                  <li key={index}>
                    <a href={link.href}>{link.label}</a>
                  </li>
                ))}
              </ul>
            </div>
            <div className="footer-column">
              <h4>Community</h4>
              <ul>
                {footerLinks.social.map((link, index) => (
                  <li key={index}>
                    <a
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <div className="footer-bottom">
            <p>© 2026 ModPorter AI. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
