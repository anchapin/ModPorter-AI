/**
 * Documentation Page - System information and usage guide
 */

import React from 'react';
import styles from './DocumentationSimple.module.css';

export const DocumentationSimple: React.FC = () => {
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>
          ModPorter AI - Documentation
        </h1>
        <p className={styles.subtitle}>
          Learn how to use ModPorter AI to convert Minecraft Java Edition mods to Bedrock Edition add-ons.
        </p>
      </header>

      <nav className={styles.navigation}>
        <a href="#getting-started" className={styles.navLink}>Getting Started</a>
        <a href="#features" className={styles.navLink}>Features</a>
        <a href="#process" className={styles.navLink}>Conversion Process</a>
        <a href="#assumptions" className={styles.navLink}>Smart Assumptions</a>
      </nav>

      <section id="getting-started" className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Getting Started
        </h2>
        <div className={styles.quickStartPanel}>
          <h3 className={styles.quickStartTitle}>Quick Start:</h3>
          <ol className={styles.quickStartList}>
            <li><strong>Upload Your Mod:</strong> Drag and drop a .jar file or .zip modpack, or paste a CurseForge/Modrinth URL</li>
            <li><strong>Configure Options:</strong> Choose whether to enable Smart Assumptions and include dependencies</li>
            <li><strong>Start Conversion:</strong> Click "Convert to Bedrock" to begin the AI-powered conversion process</li>
            <li><strong>Download Result:</strong> Once complete, download your converted .mcaddon file</li>
          </ol>
        </div>
      </section>

      <section id="features" className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Key Features
        </h2>
        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <h3 className={styles.featureTitle}>📤 Multiple Input Methods</h3>
            <p className={styles.featureDescription}>
              Support for direct file uploads (.jar, .zip) and URL imports from CurseForge and Modrinth repositories.
            </p>
          </div>
          <div className={styles.featureCard}>
            <h3 className={styles.featureTitle}>🤖 Smart Assumptions</h3>
            <p className={styles.featureDescription}>
              AI-powered conversion that intelligently adapts Java-only features to work in Bedrock Edition.
            </p>
          </div>
          <div className={styles.featureCard}>
            <h3 className={styles.featureTitle}>⚡ Real-time Progress</h3>
            <p className={styles.featureDescription}>
              Live updates during conversion with detailed progress tracking and stage information.
            </p>
          </div>
        </div>
      </section>

      <section id="process" className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Conversion Process
        </h2>
        <div className={styles.processPanel}>
          <h3 className={styles.processPanelTitle}>Process Stages:</h3>
          <div className={styles.processStages}>
            <div className={styles.processStage}>
              <strong>1. Analysis:</strong> The AI analyzes your Java mod structure, identifying blocks, items, recipes, and custom features.
            </div>
            <div className={styles.processStage}>
              <strong>2. Mapping:</strong> Features are mapped to Bedrock Edition equivalents, with smart assumptions applied where needed.
            </div>
            <div className={styles.processStage}>
              <strong>3. Conversion:</strong> Code logic is translated, assets are converted, and the add-on structure is created.
            </div>
            <div className={styles.processStage}>
              <strong>4. Packaging:</strong> The final .mcaddon file is generated and validated for compatibility.
            </div>
          </div>
        </div>
      </section>

      <section id="assumptions" className={styles.section}>
        <h2 className={styles.sectionTitle}>
          Smart Assumptions
        </h2>
        <div className={styles.assumptionsPanel}>
          <h3 className={styles.assumptionsPanelTitle}>How Smart Assumptions Work:</h3>
          <div className={styles.assumptionsGrid}>
            <div className={styles.assumptionItem}>
              <h4>🌍 Custom Dimensions</h4>
              <p>
                Converted to large explorable structures placed in existing dimensions, preserving the unique environment and biomes.
              </p>
            </div>
            <div className={styles.assumptionItem}>
              <h4>⚙️ Complex Machinery</h4>
              <p>
                Simplified to decorative blocks or containers while maintaining visual design and basic functionality.
              </p>
            </div>
            <div className={styles.assumptionItem}>
              <h4>📱 Custom GUIs</h4>
              <p>
                Transformed into book-based interfaces or sign interactions to preserve information access.
              </p>
            </div>
            <div className={styles.assumptionItem}>
              <h4>🎨 Advanced Rendering</h4>
              <p>
                Client-side rendering features are adapted to work within Bedrock's rendering capabilities.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className={styles.helpSection}>
        <h2 className={styles.helpTitle}>Need Help?</h2>
        <p className={styles.helpDescription}>
          ModPorter AI is designed to be intuitive, but if you encounter issues or have questions:
        </p>
        <div className={styles.helpButtons}>
          <button className={styles.examplesButton}>
            View Examples
          </button>
          <button className={styles.supportButton}>
            Get Support
          </button>
        </div>
      </section>
    </div>
  );
};