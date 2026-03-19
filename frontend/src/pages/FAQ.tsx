/**
 * FAQ Page - Frequently Asked Questions
 */

import React, { useState } from 'react';
import styles from './FAQ.module.css';

interface FAQItem {
  question: string;
  answer: string;
  category: 'general' | 'pricing' | 'conversion' | 'technical' | 'troubleshooting';
}

const faqItems: FAQItem[] = [
  // General Questions
  {
    question: "What is ModPorter AI?",
    answer: "ModPorter AI is an AI-powered tool that converts Minecraft Java Edition mods to Bedrock Edition add-ons. It uses advanced machine learning to analyze Java mod code and automatically translate it into compatible Bedrock format.",
    category: 'general'
  },
  {
    question: "What platforms does ModPorter AI support?",
    answer: "ModPorter AI converts mods from Minecraft Java Edition (PC) to Bedrock Edition (Windows 10, Xbox, PlayStation, Nintendo Switch, iOS, Android). The output is a .mcaddon file that can be installed directly on Bedrock platforms.",
    category: 'general'
  },
  {
    question: "Is ModPorter AI free to use?",
    answer: "ModPorter AI offers a free tier with limited conversions per month. We also have Pro, Studio, and Enterprise plans with higher limits and additional features. See our Pricing page for details.",
    category: 'general'
  },
  {
    question: "How long does a conversion take?",
    answer: "Conversion time depends on the complexity of the mod. Simple mods may take 5-10 minutes, while complex mods with many custom features can take 30 minutes or longer. You'll receive real-time progress updates during the conversion.",
    category: 'general'
  },
  {
    question: "Can I convert any Java mod to Bedrock?",
    answer: "Most mods can be converted, but there are limitations due to differences between Java and Bedrock editions. Some Java-specific features may require 'Smart Assumptions' - our AI will adapt these to work in Bedrock as closely as possible.",
    category: 'conversion'
  },
  
  // Pricing Questions
  {
    question: "What are the pricing tiers?",
    answer: "We offer four tiers: Free (5 conversions/month), Pro ($19/month - 50 conversions), Studio ($49/month - 200 conversions), and Enterprise (unlimited + priority support). All tiers include access to Smart Assumptions.",
    category: 'pricing'
  },
  {
    question: "Can I upgrade or downgrade my plan at any time?",
    answer: "Yes! You can upgrade or downgrade your plan at any time from your dashboard. Changes take effect immediately, and we'll prorate any differences in billing.",
    category: 'pricing'
  },
  {
    question: "Do unused conversions roll over?",
    answer: "No, monthly conversion allocations do not roll over. Your conversion count resets at the beginning of each billing cycle.",
    category: 'pricing'
  },
  {
    question: "Is there a trial period for paid plans?",
    answer: "Yes! All paid plans come with a 7-day free trial. You won't be charged until the trial ends, and you can cancel anytime during the trial period.",
    category: 'pricing'
  },
  {
    question: "What payment methods do you accept?",
    answer: "We accept all major credit cards (Visa, Mastercard, American Express) and PayPal. Enterprise customers can also pay via invoice.",
    category: 'pricing'
  },
  
  // Conversion Questions
  {
    question: "What file formats do you accept?",
    answer: "We accept .jar files (individual mods) and .zip files (modpacks). You can also paste direct links from CurseForge or Modrinth.",
    category: 'conversion'
  },
  {
    question: "What happens to mod dependencies?",
    answer: "ModPorter AI can automatically detect and include common dependencies. You can enable 'Include Dependencies' in the advanced options before starting conversion.",
    category: 'conversion'
  },
  {
    question: "What are Smart Assumptions?",
    answer: "Smart Assumptions are AI-powered adaptations for Java-only features that don't have direct Bedrock equivalents. For example, custom dimensions become explorable structures, and complex machinery is simplified to functional blocks.",
    category: 'conversion'
  },
  {
    question: "Can I edit the converted add-on after conversion?",
    answer: "Yes! After conversion, you can use our built-in Behavior Editor to modify blocks, recipes, loot tables, and other add-on components. The editor provides a visual interface for making changes.",
    category: 'conversion'
  },
  {
    question: "How accurate are the conversions?",
    answer: "Conversion accuracy depends on mod complexity. Simple mods with basic blocks and items achieve 90%+ functionality. Complex mods with custom mechanics may require manual adjustments. Each conversion includes a QA report detailing what was converted and any limitations.",
    category: 'conversion'
  },
  
  // Technical Questions
  {
    question: "What versions of Minecraft Bedrock are supported?",
    answer: "Our converted add-ons are compatible with Minecraft Bedrock 1.20.x and newer. We recommend keeping your Bedrock edition updated for the best experience.",
    category: 'technical'
  },
  {
    question: "Will the converted add-on work on servers?",
    answer: "Converted add-ons work on both single-player and multiplayer servers. However, server-specific mods may have limitations depending on the server's add-on support.",
    category: 'technical'
  },
  {
    question: "Can I use the converted add-on commercially?",
    answer: "This depends on the original mod's license. ModPorter AI does not transfer ownership of original mod code. Please respect the original mod author's rights and check their license terms.",
    category: 'technical'
  },
  {
    question: "How do I install the converted .mcaddon file?",
    answer: "Double-click the .mcaddon file to open it in Minecraft Bedrock Edition. The add-on will be installed automatically. You can also place the file in your Minecraft 'com.mojang' folder for manual installation.",
    category: 'technical'
  },
  
  // Troubleshooting
  {
    question: "The conversion failed - what should I do?",
    answer: "First, check the conversion report for error details. Common issues include incompatible mod features or missing dependencies. You can try again with 'Smart Assumptions' enabled, or contact support with the error code.",
    category: 'troubleshooting'
  },
  {
    question: "The converted add-on crashes my game",
    answer: "This can happen with complex conversions. Try these steps: 1) Disable other add-ons temporarily, 2) Start a new world with the add-on, 3) Check if your Bedrock version is up to date. If issues persist, please report it with the conversion ID.",
    category: 'troubleshooting'
  },
  {
    question: "Some features don't work in the converted add-on",
    answer: "This is expected for features that couldn't be directly translated. The QA report lists all adapted features. You can use our Behavior Editor to manually adjust or add missing functionality.",
    category: 'troubleshooting'
  },
  {
    question: "I can't find my converted add-on files",
    answer: "Converted add-ons are saved in your account's dashboard. You can download them anytime. Look for 'Conversion History' in the sidebar menu.",
    category: 'troubleshooting'
  },
  {
    question: "How do I report a bug or issue?",
    answer: "Use the 'Report Issue' button in your conversion history, or visit our Discord server to share feedback. Include the conversion ID and describe what went wrong.",
    category: 'troubleshooting'
  }
];

const categoryLabels: Record<FAQItem['category'], string> = {
  general: 'General',
  pricing: 'Pricing',
  conversion: 'Conversion',
  technical: 'Technical',
  troubleshooting: 'Troubleshooting'
};

export const FAQ: React.FC = () => {
  const [activeCategory, setActiveCategory] = useState<FAQItem['category'] | 'all'>('all');
  const [expandedItems, setExpandedItems] = useState<Set<number>>(new Set());

  const toggleItem = (index: number) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedItems(newExpanded);
  };

  const filteredItems = activeCategory === 'all' 
    ? faqItems 
    : faqItems.filter(item => item.category === activeCategory);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className={styles.title}>Frequently Asked Questions</h1>
        <p className={styles.subtitle}>
          Find answers to common questions about ModPorter AI
        </p>
      </header>

      <nav className={styles.categoryNav}>
        <button
          className={`${styles.categoryButton} ${activeCategory === 'all' ? styles.active : ''}`}
          onClick={() => setActiveCategory('all')}
        >
          All Questions
        </button>
        {(Object.keys(categoryLabels) as FAQItem['category'][]).map(category => (
          <button
            key={category}
            className={`${styles.categoryButton} ${activeCategory === category ? styles.active : ''}`}
            onClick={() => setActiveCategory(category)}
          >
            {categoryLabels[category]}
          </button>
        ))}
      </nav>

      <div className={styles.faqList}>
        {filteredItems.map((item, index) => (
          <div 
            key={index} 
            className={`${styles.faqItem} ${expandedItems.has(index) ? styles.expanded : ''}`}
          >
            <button
              className={styles.questionButton}
              onClick={() => toggleItem(index)}
              aria-expanded={expandedItems.has(index)}
            >
              <span className={styles.questionText}>{item.question}</span>
              <span className={styles.toggleIcon}>
                {expandedItems.has(index) ? '−' : '+'}
              </span>
            </button>
            {expandedItems.has(index) && (
              <div className={styles.answer}>
                <p>{item.answer}</p>
                <span className={styles.categoryTag}>
                  {categoryLabels[item.category]}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>

      <section className={styles.helpSection}>
        <h2>Still have questions?</h2>
        <p>Can't find what you're looking for? We're here to help.</p>
        <div className={styles.helpButtons}>
          <a href="https://discord.gg/modporter" className={styles.discordButton}>
            Join our Discord
          </a>
          <a href="mailto:support@modporter.ai" className={styles.emailButton}>
            Contact Support
          </a>
        </div>
      </section>
    </div>
  );
};

export default FAQ;
