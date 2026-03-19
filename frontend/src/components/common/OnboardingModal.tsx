/**
 * Onboarding Modal - Interactive guide for new users
 */

import React, { useState, useEffect } from 'react';
import './OnboardingModal.css';

interface OnboardingStep {
  id: string;
  title: string;
  description: string;
  icon: string;
}

const onboardingSteps: OnboardingStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to ModPorter AI',
    description: 'Your AI-powered tool for converting Minecraft Java Edition mods to Bedrock Edition add-ons. Let\'s take a quick tour!',
    icon: '👋'
  },
  {
    id: 'upload',
    title: 'Upload Your Mod',
    description: 'Drag and drop a .jar file or .zip modpack, or paste a CurseForge or Modrinth URL to get started.',
    icon: '📤'
  },
  {
    id: 'convert',
    title: 'AI-Powered Conversion',
    description: 'Our AI analyzes your mod and converts it to Bedrock format. Smart Assumptions adapt Java-only features to work in Bedrock.',
    icon: '🤖'
  },
  {
    id: 'download',
    title: 'Download & Install',
    description: 'Once complete, download your .mcaddon file and install it in Minecraft Bedrock Edition. It\'s that simple!',
    icon: '📥'
  },
  {
    id: 'explore',
    title: 'Explore More Features',
    description: 'Check out our Dashboard for conversion history, Comparison view for side-by-side analysis, and Editor for custom modifications.',
    icon: '🗺️'
  }
];

interface OnboardingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const OnboardingModal: React.FC<OnboardingModalProps> = ({ isOpen, onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(false);

  // Trigger open animation
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => setIsVisible(true), 10);
    } else {
      setIsVisible(false);
    }
  }, [isOpen]);

  const handleNext = () => {
    if (currentStep < onboardingSteps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleClose();
    }
  };

  const handlePrevious = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleClose = () => {
    setIsVisible(false);
    // Save to localStorage that onboarding is complete
    localStorage.setItem('onboarding_completed', 'true');
    setTimeout(onClose, 300);
  };

  const handleSkip = () => {
    handleClose();
  };

  const step = onboardingSteps[currentStep];
  const progress = ((currentStep + 1) / onboardingSteps.length) * 100;

  if (!isOpen) return null;

  return (
    <div className={`onboarding-overlay ${isVisible ? 'visible' : ''}`}>
      <div className="onboarding-modal">
        {/* Progress Bar */}
        <div className="onboarding-progress">
          <div 
            className="onboarding-progress-bar" 
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Close Button */}
        <button className="onboarding-close" onClick={handleSkip} aria-label="Skip onboarding">
          ✕
        </button>

        {/* Content */}
        <div className="onboarding-content">
          <div className="onboarding-icon">{step.icon}</div>
          
          <div className="onboarding-indicators">
            {onboardingSteps.map((_, index) => (
              <button
                key={index}
                className={`onboarding-dot ${index === currentStep ? 'active' : ''} ${index < currentStep ? 'completed' : ''}`}
                onClick={() => setCurrentStep(index)}
                aria-label={`Go to step ${index + 1}`}
              />
            ))}
          </div>

          <h2 className="onboarding-title">{step.title}</h2>
          <p className="onboarding-description">{step.description}</p>
        </div>

        {/* Navigation */}
        <div className="onboarding-nav">
          <button 
            className="onboarding-btn onboarding-btn-secondary"
            onClick={handlePrevious}
            disabled={currentStep === 0}
          >
            ← Back
          </button>

          <span className="onboarding-step-count">
            {currentStep + 1} of {onboardingSteps.length}
          </span>

          <button 
            className="onboarding-btn onboarding-btn-primary"
            onClick={handleNext}
          >
            {currentStep === onboardingSteps.length - 1 ? 'Get Started!' : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  );
};

// Hook for managing onboarding state
export const useOnboarding = () => {
  const [shouldShowOnboarding, setShouldShowOnboarding] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user has completed onboarding before
    const completed = localStorage.getItem('onboarding_completed');
    if (!completed) {
      setShouldShowOnboarding(true);
    }
    setIsLoading(false);
  }, []);

  const completeOnboarding = () => {
    localStorage.setItem('onboarding_completed', 'true');
    setShouldShowOnboarding(false);
  };

  const resetOnboarding = () => {
    localStorage.removeItem('onboarding_completed');
    setShouldShowOnboarding(true);
  };

  return {
    shouldShowOnboarding,
    isLoading,
    completeOnboarding,
    resetOnboarding
  };
};

export default OnboardingModal;
