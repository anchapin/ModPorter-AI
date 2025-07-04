import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { ConversionUpload } from './components/ConversionUpload/ConversionUpload';
import { Documentation } from './pages/Documentation';
import './App.css';

function App() {
  const handleConversionStart = (data: any) => {
    console.log('Conversion started:', data);
    // Handle conversion logic here
  };

  return (
    <Router>
      <div className="app">
        <header className="app-header">
          <nav style={{ 
            display: 'flex', 
            justifyContent: 'space-between', 
            alignItems: 'center',
            padding: '1rem 2rem',
            backgroundColor: '#f8f9fa',
            borderBottom: '1px solid #e0e0e0'
          }}>
            <Link to="/" style={{ 
              fontSize: '1.5rem', 
              fontWeight: 'bold', 
              color: '#333',
              textDecoration: 'none'
            }}>
              ModPorter AI
            </Link>
            <div>
              <Link to="/" style={{ 
                margin: '0 1rem', 
                color: '#007bff',
                textDecoration: 'none'
              }}>
                Convert
              </Link>
              <Link to="/docs" style={{ 
                margin: '0 1rem', 
                color: '#007bff',
                textDecoration: 'none'
              }}>
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
                <div style={{ padding: '2rem', textAlign: 'center' }}>
                  <h1 style={{ fontSize: '3rem', color: '#333', marginBottom: '1rem' }}>
                    ModPorter AI
                  </h1>
                  <p style={{ fontSize: '1.2rem', color: '#666', marginBottom: '2rem' }}>
                    Convert Minecraft Java Edition mods to Bedrock Edition add-ons with AI
                  </p>
                  <ConversionUpload onConversionStart={handleConversionStart} />
                </div>
              } 
            />
            <Route path="/docs" element={<Documentation />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;