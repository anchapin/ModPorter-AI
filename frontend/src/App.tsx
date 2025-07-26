import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ConversionUploadReal } from './components/ConversionUpload/ConversionUploadReal';
import { DocumentationSimple } from './pages/DocumentationSimple';
import { Dashboard } from './pages/Dashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
import { TopNavigation } from './components/TopNavigation';
import { ComparisonView } from './components/ComparisonView';
import { BehavioralTest } from './components/BehavioralTest';
import EditorPage from './pages/EditorPage'; // Added for Editor Route
import './App.css';
import styles from './App.module.css';

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
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/comparison" element={<div style={{ padding: '2rem' }}><ComparisonView /></div>} />
                <Route path="/comparison/:comparisonId" element={<div style={{ padding: '2rem' }}><ComparisonView /></div>} />
                <Route path="/behavioral-test" element={<div style={{ padding: '2rem' }}><BehavioralTest conversionId="sample" /></div>} />
                <Route path="/docs" element={<DocumentationSimple />} />
                <Route path="/editor/:addonId" element={<EditorPage />} /> {/* Added Editor Route */}
              </Routes>
            </main>
          </div>
        </Router>
      </NotificationProvider>
    </ErrorBoundary>
  );
}

export default App;