import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConversionUploadReal } from './components/ConversionUpload/ConversionUploadReal';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
import { TopNavigation } from './components/TopNavigation';
import './App.css';
import styles from './App.module.css';

// Lazy load heavy components
const DocumentationSimple = lazy(() => import('./pages/DocumentationSimple'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const ComparisonView = lazy(() => import('./components/ComparisonView'));
const BehavioralTestWrapper = lazy(() => import('./components/BehavioralTest/BehavioralTestWrapper'));
const EditorPage = lazy(() => import('./pages/EditorPage'));
const ExperimentsPage = lazy(() => import('./pages/ExperimentsPage'));
const ExperimentResultsPage = lazy(() => import('./pages/ExperimentResultsPage'));

function App() {
  console.log('App component is rendering...');
  
  const handleConversionStart = (data: any) => {
    console.log('Conversion started:', data);
  };
  
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
                    <div className={styles.heroSection}>
                      <h1 className={styles.heroTitle}>
                        ModPorter AI
                      </h1>
                      <p className={styles.heroDescription}>
                        Convert Minecraft Java Edition mods to Bedrock Edition add-ons with AI
                      </p>
                      <ConversionUploadReal onConversionStart={handleConversionStart} />
                    </div>
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
              </Routes>
            </main>
          </div>
        </Router>
      </NotificationProvider>
    </ErrorBoundary>
  );
}

export default App;