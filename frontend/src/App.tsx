import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ConversionUploadReal } from './components/ConversionUpload/ConversionUploadReal';
import { DocumentationSimple } from './pages/DocumentationSimple';
import { Dashboard } from './pages/Dashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
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
            <header className="app-header">
              <nav>
                <Link to="/">
                  ModPorter AI
                </Link>
                <div>
                  <Link to="/">
                    Convert
                  </Link>
                  <Link to="/dashboard">
                    Dashboard
                  </Link>
                  <Link to="/docs">
                    Documentation
                  </Link>
                </div>
              </nav>
            </header>

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