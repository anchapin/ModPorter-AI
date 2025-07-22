import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ConversionUploadReal } from './components/ConversionUpload/ConversionUploadReal';
import { DocumentationSimple } from './pages/DocumentationSimple';
import { Dashboard } from './pages/Dashboard';
import { ErrorBoundary } from './components/ErrorBoundary';
import { NotificationProvider } from './components/NotificationSystem';
import EditorPage from './pages/EditorPage'; // Added for Editor Route
import './App.css';

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
                    <div style={{ padding: '2rem', textAlign: 'center', background: 'rgba(255, 255, 255, 0.95)', borderRadius: '16px', margin: '2rem', boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)' }}>
                      <h1 style={{ fontSize: '3rem', color: '#333', marginBottom: '1rem', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
                        ModPorter AI
                      </h1>
                      <p style={{ fontSize: '1.2rem', color: '#666', marginBottom: '2rem' }}>
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