import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
import { TopNavigation } from './components/TopNavigation';
import './App.css';

// Lazy load heavy components
const DocumentationSimple = lazy(() => import('./pages/DocumentationSimple'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ConvertPage = lazy(() => import('./pages/ConvertPage'));
const ComparisonView = lazy(() => import('./components/ComparisonView'));
const BehavioralTestWrapper = lazy(() => import('./components/BehavioralTest/BehavioralTestWrapper'));
const EditorPage = lazy(() => import('./pages/EditorPage'));
const ExperimentsPage = lazy(() => import('./pages/ExperimentsPage'));
const ExperimentResultsPage = lazy(() => import('./pages/ExperimentResultsPage'));
const Settings = lazy(() => import('./pages/Settings'));

function App() {
  console.log('App component is rendering...');

  return (
    <ErrorBoundary>
      <NotificationProvider>
        <Router>
          <div className="app">
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
                <Route path="/dashboard" element={
                  <Suspense fallback={<div>Loading Dashboard...</div>}>
                    <Dashboard />
                  </Suspense>
                } />
                <Route path="/experiments" element={
                  <Suspense fallback={<div>Loading Experiments...</div>}>
                    <ExperimentsPage />
                  </Suspense>
                } />
                <Route path="/experiment-results" element={
                  <Suspense fallback={<div>Loading Results...</div>}>
                    <ExperimentResultsPage />
                  </Suspense>
                } />
                <Route path="/comparison" element={
                  <Suspense fallback={<div>Loading Comparison...</div>}>
                    <div className="page-wrapper"><ComparisonView /></div>
                  </Suspense>
                } />
                <Route path="/comparison/:comparisonId" element={
                  <Suspense fallback={<div>Loading Comparison...</div>}>
                    <div className="page-wrapper"><ComparisonView /></div>
                  </Suspense>
                } />
                <Route path="/behavioral-test/:conversionId" element={
                  <Suspense fallback={<div>Loading Behavioral Test...</div>}>
                    <div className="page-wrapper"><BehavioralTestWrapper /></div>
                  </Suspense>
                } />
                <Route path="/docs" element={
                  <Suspense fallback={<div>Loading Documentation...</div>}>
                    <DocumentationSimple />
                  </Suspense>
                } />
                <Route path="/editor/:addonId" element={
                  <Suspense fallback={<div>Loading Editor...</div>}>
                    <EditorPage />
                  </Suspense>
                } /> {/* Added Editor Route */}
                <Route path="/behavior-editor/:conversionId" element={
                  <Suspense fallback={<div>Loading Behavior Editor...</div>}>
                    <EditorPage />
                  </Suspense>
                } /> {/* Added Behavior Editor Route */}
                <Route path="/settings" element={
                  <Suspense fallback={<div>Loading Settings...</div>}>
                    <Settings />
                  </Suspense>
                } />
              </Routes>
            </main>
          </div>
        </Router>
      </NotificationProvider>
    </ErrorBoundary>
  );
}

export default App;