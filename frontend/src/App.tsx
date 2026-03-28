import React, { Suspense, lazy, useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
import { TopNavigation } from './components/TopNavigation';
import { OnboardingFlow } from './components/Onboarding';
import { usePageViewTracking } from './hooks/useAnalytics';
import './App.css';

// Lazy load heavy components
// Using type assertion to handle named exports
const DocumentationSimple = lazy(() =>
  import('./pages/DocumentationSimple').then((m) => ({
    default: m.DocumentationSimple as React.ComponentType<any>,
  }))
);
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ConvertPage = lazy(() => import('./pages/ConvertPage'));
const ComparisonView = lazy(() =>
  import('./components/ComparisonView').then((m) => ({
    default: m.ComparisonView as React.ComponentType<any>,
  }))
);
const BehavioralTestWrapper = lazy(() =>
  import('./components/BehavioralTest/BehavioralTestWrapper').then((m) => ({
    default: m.BehavioralTestWrapper as React.ComponentType<any>,
  }))
);
const EditorPage = lazy(() => import('./pages/EditorPage'));
const ExperimentsPage = lazy(() => import('./pages/ExperimentsPage'));
const ExperimentResultsPage = lazy(
  () => import('./pages/ExperimentResultsPage')
);
const Settings = lazy(() => import('./pages/Settings'));
const PricingPage = lazy(() => import('./pages/PricingPage'));
const UploadPage = lazy(() => import('./pages/UploadPage'));
const ProgressPage = lazy(() => import('./pages/ProgressPage'));
const ResultsPage = lazy(() => import('./pages/ResultsPage'));

function App() {
  console.log('App component is rendering...');

  // Track page views automatically
  usePageViewTracking(true);

  // Onboarding state
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    // Check if user has completed onboarding
    const onboardingCompleted = localStorage.getItem('onboarding_completed');
    if (!onboardingCompleted) {
      // Show onboarding for first-time users
      setShowOnboarding(true);
    }
  }, []);

  return (
    <ErrorBoundary>
      <NotificationProvider>
        <Router>
          <div className="app">
            <OnboardingFlow
              isOpen={showOnboarding}
              onComplete={() => setShowOnboarding(false)}
              onClose={() => setShowOnboarding(false)}
            />
            <TopNavigation />

            <main>
              <Routes>
                <Route
                  path="/"
                  element={
                    <Suspense fallback={<div>Loading...</div>}>
                      <ConvertPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/dashboard"
                  element={
                    <Suspense fallback={<div>Loading Dashboard...</div>}>
                      <Dashboard />
                    </Suspense>
                  }
                />
                <Route
                  path="/experiments"
                  element={
                    <Suspense fallback={<div>Loading Experiments...</div>}>
                      <ExperimentsPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/experiment-results"
                  element={
                    <Suspense fallback={<div>Loading Results...</div>}>
                      <ExperimentResultsPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/comparison"
                  element={
                    <Suspense fallback={<div>Loading Comparison...</div>}>
                      <div className="page-wrapper">
                        <ComparisonView />
                      </div>
                    </Suspense>
                  }
                />
                <Route
                  path="/comparison/:comparisonId"
                  element={
                    <Suspense fallback={<div>Loading Comparison...</div>}>
                      <div className="page-wrapper">
                        <ComparisonView />
                      </div>
                    </Suspense>
                  }
                />
                <Route
                  path="/behavioral-test/:conversionId"
                  element={
                    <Suspense fallback={<div>Loading Behavioral Test...</div>}>
                      <div className="page-wrapper">
                        <BehavioralTestWrapper />
                      </div>
                    </Suspense>
                  }
                />
                <Route
                  path="/docs"
                  element={
                    <Suspense fallback={<div>Loading Documentation...</div>}>
                      <DocumentationSimple />
                    </Suspense>
                  }
                />
                <Route
                  path="/editor/:addonId"
                  element={
                    <Suspense fallback={<div>Loading Editor...</div>}>
                      <EditorPage />
                    </Suspense>
                  }
                />{' '}
                {/* Added Editor Route */}
                <Route
                  path="/behavior-editor/:conversionId"
                  element={
                    <Suspense fallback={<div>Loading Behavior Editor...</div>}>
                      <EditorPage />
                    </Suspense>
                  }
                />{' '}
                {/* Added Behavior Editor Route */}
                <Route
                  path="/settings"
                  element={
                    <Suspense fallback={<div>Loading Settings...</div>}>
                      <Settings />
                    </Suspense>
                  }
                />
                <Route
                  path="/pricing"
                  element={
                    <Suspense fallback={<div>Loading Pricing...</div>}>
                      <PricingPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/upload"
                  element={
                    <Suspense fallback={<div>Loading Upload...</div>}>
                      <UploadPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/progress/:jobId"
                  element={
                    <Suspense fallback={<div>Loading Progress...</div>}>
                      <ProgressPage />
                    </Suspense>
                  }
                />
                <Route
                  path="/results/:jobId"
                  element={
                    <Suspense fallback={<div>Loading Results...</div>}>
                      <ResultsPage />
                    </Suspense>
                  }
                />
              </Routes>
            </main>
          </div>
        </Router>
      </NotificationProvider>
    </ErrorBoundary>
  );
}

export default App;
