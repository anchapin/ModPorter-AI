import React from 'react';
import './ShowcasePage.css';

const stats = [
  { value: '2,500+', label: 'Mods Converted' },
  { value: '15+', label: 'Content Types' },
  { value: '94%', label: 'Success Rate' },
];

const successStories = [
  {
    title: 'RPG Prodigy',
    author: 'DevMaster_42',
    description:
      'Converted a 50,000+ line combat system in 3 days. Portkit handled all recipes, entities, and custom potions automatically.',
    screenshot: 'https://placehold.co/600x400/1e293b/6366f1?text=RPG+Prodigy+Screenshot',
    highlights: ['Combat system', 'Custom potions', 'Entity AI'],
  },
  {
    title: 'TechCore Machinery',
    author: 'RedstoneWizard',
    description:
      'Portkit converted my massive IndustrialCraft-style mod. The detailed report helped me complete the complex machine recipes manually.',
    screenshot: 'https://placehold.co/600x400/1e293b/10b981?text=TechCore+Machinery',
    highlights: ['Machine recipes', 'Power systems', 'Ore processing'],
  },
  {
    title: 'Ender Expansion',
    author: 'VoidCrafter',
    description:
      'My ender-themed mod went from Java to Bedrock in under a week. The texture conversion was flawless.',
    screenshot: 'https://placehold.co/600x400/1e293b/a855f7?text=Ender+Expansion',
    highlights: ['Custom biomes', 'Ender mobs', 'Portal blocks'],
  },
];

const testimonials = [
  {
    quote:
      "Portkit saved me weeks of work. The conversion quality exceeded my expectations.",
    author: 'CraftMaster',
    role: 'Mod Developer',
  },
  {
    quote:
      "Finally, a tool that understands Java to Bedrock conversion isn't just syntax mapping. Portkit gets the semantics right.",
    author: 'BedrockBuilder',
    role: 'Marketplace Creator',
  },
  {
    quote:
      "The detailed report was incredibly helpful. I knew exactly what needed manual attention before starting.",
    author: 'JavaWarrior',
    role: 'Server Owner',
  },
];

const galleryImages = [
  { src: 'https://placehold.co/400x300/1e293b/6366f1?text=Converted+Mod+1', alt: 'Converted mod screenshot 1' },
  { src: 'https://placehold.co/400x300/1e293b/10b981?text=Converted+Mod+2', alt: 'Converted mod screenshot 2' },
  { src: 'https://placehold.co/400x300/1e293b/f59e0b?text=Converted+Mod+3', alt: 'Converted mod screenshot 3' },
  { src: 'https://placehold.co/400x300/1e293b/ec4899?text=Converted+Mod+4', alt: 'Converted mod screenshot 4' },
  { src: 'https://placehold.co/400x300/1e293b/06b6d4?text=Converted+Mod+5', alt: 'Converted mod screenshot 5' },
  { src: 'https://placehold.co/400x300/1e293b/8b5cf6?text=Converted+Mod+6', alt: 'Converted mod screenshot 6' },
];

const ShowcasePage: React.FC = () => {
  return (
    <div className="showcase-page">
      <section className="hero-section">
        <div className="section-container">
          <div className="hero-badge">Community Showcase</div>
          <h1 className="hero-title">
            Real Mods, Real Success
          </h1>
          <p className="hero-subtitle">
            See how developers are bringing their Java mods to the Bedrock Marketplace
            with Portkit
          </p>
        </div>
      </section>

      <section className="stats-section">
        <div className="section-container">
          <div className="stats-grid">
            {stats.map((stat, index) => (
              <div key={index} className="stat-card">
                <span className="stat-value">{stat.value}</span>
                <span className="stat-label">{stat.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="success-stories-section">
        <div className="section-container">
          <h2 className="section-title">Success Stories</h2>
          <p className="section-subtitle">
            Case studies from developers who converted their mods with Portkit
          </p>
          <div className="stories-grid">
            {successStories.map((story, index) => (
              <div key={index} className="story-card">
                <div className="story-screenshot">
                  <img src={story.screenshot} alt={story.title} />
                </div>
                <div className="story-content">
                  <h3 className="story-title">{story.title}</h3>
                  <p className="story-author">by {story.author}</p>
                  <p className="story-description">{story.description}</p>
                  <div className="story-highlights">
                    {story.highlights.map((highlight, idx) => (
                      <span key={idx} className="highlight-tag">
                        {highlight}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="gallery-section">
        <div className="section-container">
          <h2 className="section-title">Community Gallery</h2>
          <p className="section-subtitle">
            Screenshots of converted mods running in Bedrock
          </p>
          <div className="gallery-grid">
            {galleryImages.map((image, index) => (
              <div key={index} className="gallery-item">
                <img src={image.src} alt={image.alt} />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="testimonials-section">
        <div className="section-container">
          <h2 className="section-title">What Developers Say</h2>
          <p className="section-subtitle">
            Hear from the community
          </p>
          <div className="testimonials-grid">
            {testimonials.map((testimonial, index) => (
              <div key={index} className="testimonial-card">
                <p className="testimonial-quote">"{testimonial.quote}"</p>
                <div className="testimonial-author">
                  <span className="author-name">{testimonial.author}</span>
                  <span className="author-role">{testimonial.role}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="discord-section">
        <div className="section-container">
          <div className="discord-card">
            <div className="discord-icon">
              <svg height="48" viewBox="0 0 24 24" width="48" xmlns="http://www.w3.org/2000/svg">
                <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z" fill="currentColor"/>
              </svg>
            </div>
            <h2 className="discord-title">Join Our Community</h2>
            <p className="discord-description">
              Share your conversion results, get help, and connect with other mod developers
              in our Discord server.
            </p>
            <a
              href="https://discord.gg/modporter"
              target="_blank"
              rel="noopener noreferrer"
              className="discord-button"
            >
              Join Discord
            </a>
          </div>
        </div>
      </section>
    </div>
  );
};

export default ShowcasePage;