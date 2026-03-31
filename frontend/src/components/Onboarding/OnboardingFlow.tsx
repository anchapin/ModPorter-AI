import React, { useState, useEffect } from 'react';
import './OnboardingFlow.css';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  component?: React.ReactNode;
  action?: string;
  checklist?: string[];
}

interface OnboardingFlowProps {
  onComplete?: () => void;
  onClose?: () => void;
  isOpen: boolean;
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to ModPorter AI! 🎮',
    description:
      'Convert your Minecraft Java mods to Bedrock add-ons in minutes, not months. Let us show you around.',
    component: (
      <div className="onboarding-welcome">
        <div className="welcome-animation">
          <div className="java-block">J</div>
          <div className="arrow">→</div>
          <div className="bedrock-block">B</div>
        </div>
        <p className="welcome-stats">
          <strong>60-80%</strong> automation
          <br />
          <strong>5-30 min</strong> per conversion
          <br />
          <strong>1000+</strong> mods converted
        </p>
      </div>
    ),
    action: 'Get Started',
  },
  {
    id: 'upload',
    title: 'Upload Your Java Mod',
    description:
      'Start by uploading a Java mod file (.jar or .zip). We support Forge, Fabric, and vanilla mods.',
    component: (
      <div className="onboarding-demo">
        <div className="upload-area-demo">
          <svg
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
          >
            <path
              d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M17 8l-5-5-5 5M12 3v12"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <p>Drag & drop your .jar file here</p>
          <p className="demo-hint">or click to browse</p>
        </div>
      </div>
    ),
    checklist: [
      'Have your Java mod file ready (.jar or .zip)',
      'Make sure it works in Java Edition first',
      'Maximum file size: 100MB (Free), 500MB (Pro)',
    ],
    action: 'I have my mod ready',
  },
  {
    id: 'features',
    title: 'What Can You Convert? 🎯',
    description:
      'ModPorter AI handles everything from simple items to complex entities and dimensions.',
    component: (
      <div className="onboarding-features">
        <div className="feature-grid">
          <div className="feature-card">
            <div className="feature-icon">⚔️</div>
            <h4>Items & Tools</h4>
            <p>Swords, armor, custom items</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🧱</div>
            <h4>Blocks</h4>
            <p>Custom blocks with properties</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🐷</div>
            <h4>Entities</h4>
            <p>Mobs, NPCs, creatures</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">⚗️</div>
            <h4>Recipes</h4>
            <p>Crafting, smelting, brewing</p>
          </div>
        </div>
        <div className="complexity-note">
          <strong>Tip:</strong> Simple mods convert at 95%+ accuracy. Complex
          mods may need some manual adjustments.
        </div>
      </div>
    ),
    action: 'Got it!',
  },
  {
    id: 'process',
    title: 'How It Works 🤖',
    description:
      'Our multi-agent AI system analyzes, translates, validates, and packages your conversion automatically.',
    component: (
      <div className="onboarding-process">
        <div className="process-steps">
          <div className="process-step">
            <div className="step-number">1</div>
            <h4>Analyze</h4>
            <p>AI parses your Java code</p>
          </div>
          <div className="process-arrow">↓</div>
          <div className="process-step">
            <div className="step-number">2</div>
            <h4>Translate</h4>
            <p>Convert to Bedrock JS</p>
          </div>
          <div className="process-arrow">↓</div>
          <div className="process-step">
            <div className="step-number">3</div>
            <h4>Convert</h4>
            <p>Textures, models, sounds</p>
          </div>
          <div className="process-arrow">↓</div>
          <div className="process-step">
            <div className="step-number">4</div>
            <h4>Package</h4>
            <p>Create .mcaddon file</p>
          </div>
        </div>
        <div className="process-time">
          <strong>Simple mods:</strong> 5-10 min
          <br />
          <strong>Complex mods:</strong> 20-30 min
        </div>
      </div>
    ),
    action: 'Continue',
  },
  {
    id: 'results',
    title: 'Review Your Conversion 📊',
    description:
      'After conversion, you get a detailed report showing what worked and what needs manual adjustment.',
    component: (
      <div className="onboarding-results">
        <div className="results-demo">
          <div className="success-rate">
            <div className="rate-circle">95%</div>
            <p>Success Rate</p>
          </div>
          <div className="components-list">
            <h4>Components Converted</h4>
            <ul>
              <li>✓ Ruby Sword Item</li>
              <li>✓ Custom Texture</li>
              <li>✓ Attack Damage Logic</li>
              <li>✓ Durability System</li>
            </ul>
          </div>
        </div>
        <div className="manual-steps">
          <h4>Manual Steps (if any)</h4>
          <p className="no-steps">None! Your add-on is ready to use.</p>
        </div>
      </div>
    ),
    action: 'Awesome!',
  },
  {
    id: 'first-conversion',
    title: 'Ready for Your First Conversion? 🚀',
    description:
      "You have 5 free conversions this month. Let's convert your first mod together!",
    component: (
      <div className="onboarding-checklist">
        <h4>Before You Start:</h4>
        <ul className="checklist-items">
          <li>
            <input type="checkbox" id="check1" />
            <label htmlFor="check1">
              I have a Java mod file (.jar or .zip)
            </label>
          </li>
          <li>
            <input type="checkbox" id="check2" />
            <label htmlFor="check2">The mod works in Java Edition</label>
          </li>
          <li>
            <input type="checkbox" id="check3" />
            <label htmlFor="check3">
              I have Minecraft Bedrock Edition installed
            </label>
          </li>
          <li>
            <input type="checkbox" id="check4" />
            <label htmlFor="check4">
              I have 5-30 minutes for the conversion
            </label>
          </li>
        </ul>
        <div className="pro-tip">
          <strong>💡 Pro Tip:</strong> Start with a simple item or block mod for
          your first conversion. Save complex mods for later!
        </div>
      </div>
    ),
    action: 'Start My First Conversion',
  },
];

export const OnboardingFlow: React.FC<OnboardingFlowProps> = ({
  isOpen,
  onComplete,
  onClose,
}) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isSkipped, setIsSkipped] = useState(false);

  // Load saved onboarding state
  useEffect(() => {
    const saved = localStorage.getItem('onboarding_completed');
    if (saved === 'true' && !isOpen) {
      // Onboarding already completed
      return;
    }
  }, [isOpen]);

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleComplete = () => {
    localStorage.setItem('onboarding_completed', 'true');
    onComplete?.();
  };

  const handleSkip = () => {
    setIsSkipped(true);
    localStorage.setItem('onboarding_completed', 'true');
    onClose?.();
  };

  const step = onboardingSteps[currentStep];
  const progress = ((currentStep + 1) / onboardingSteps.length) * 100;

  if (!isOpen) return null;

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-modal">
        {/* Close button */}
        <button
          className="onboarding-close"
          onClick={handleSkip}
          aria-label="Close onboarding"
        >
          ✕
        </button>

        {/* Progress bar */}
        <div className="onboarding-progress">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }} />
          </div>
          <div className="step-indicator">
            Step {currentStep + 1} of {onboardingSteps.length}
          </div>
        </div>

        {/* Content */}
        <div className="onboarding-content">
          <h2 className="onboarding-title">{step.title}</h2>
          <p className="onboarding-description">{step.description}</p>

          {step.component && (
            <div className="onboarding-component">{step.component}</div>
          )}

          {step.checklist && (
            <ul className="onboarding-checklist-list">
              {step.checklist.map((item, index) => (
                <li key={index} className="checklist-item">
                  <svg
                    className="check-icon"
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
                  {item}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Actions */}
        <div className="onboarding-actions">
          {currentStep > 0 && (
            <button className="btn-back" onClick={handleBack}>
              Back
            </button>
          )}
          <button className="btn-next" onClick={handleNext}>
            {step.action || 'Continue'}
          </button>
        </div>

        {/* Skip link */}
        {currentStep < onboardingSteps.length - 1 && (
          <button className="btn-skip" onClick={handleSkip}>
            Skip onboarding
          </button>
        )}
      </div>
    </div>
  );
};

export default OnboardingFlow;
