/**
 * Documentation Page - System information and usage guide
 */

import React from 'react';

export const DocumentationSimple: React.FC = () => {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
      <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2.5rem', color: '#333', marginBottom: '1rem' }}>
          ModPorter AI - Documentation
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#666', maxWidth: '600px', margin: '0 auto' }}>
          Learn how to use ModPorter AI to convert Minecraft Java Edition mods to Bedrock Edition add-ons.
        </p>
      </header>

      <nav style={{ 
        backgroundColor: '#f8f9fa', 
        padding: '1rem', 
        borderRadius: '8px', 
        marginBottom: '2rem',
        textAlign: 'center'
      }}>
        <a href="#getting-started" style={{ margin: '0 1rem', color: '#007bff', textDecoration: 'none' }}>Getting Started</a>
        <a href="#features" style={{ margin: '0 1rem', color: '#007bff', textDecoration: 'none' }}>Features</a>
        <a href="#process" style={{ margin: '0 1rem', color: '#007bff', textDecoration: 'none' }}>Conversion Process</a>
        <a href="#assumptions" style={{ margin: '0 1rem', color: '#007bff', textDecoration: 'none' }}>Smart Assumptions</a>
      </nav>

      <section id="getting-started" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          Getting Started
        </h2>
        <div style={{ 
          backgroundColor: '#e8f5e8', 
          padding: '1.5rem', 
          borderRadius: '8px',
          marginBottom: '2rem'
        }}>
          <h3 style={{ color: '#333', marginBottom: '1rem' }}>Quick Start:</h3>
          <ol style={{ fontSize: '1.1rem', color: '#555', lineHeight: '1.8' }}>
            <li><strong>Upload Your Mod:</strong> Drag and drop a .jar file or .zip modpack, or paste a CurseForge/Modrinth URL</li>
            <li><strong>Configure Options:</strong> Choose whether to enable Smart Assumptions and include dependencies</li>
            <li><strong>Start Conversion:</strong> Click "Convert to Bedrock" to begin the AI-powered conversion process</li>
            <li><strong>Download Result:</strong> Once complete, download your converted .mcaddon file</li>
          </ol>
        </div>
      </section>

      <section id="features" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          Key Features
        </h2>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', 
          gap: '2rem',
          marginBottom: '2rem'
        }}>
          <div style={{ backgroundColor: '#f8f9fa', padding: '1.5rem', borderRadius: '8px' }}>
            <h3 style={{ color: '#007bff', marginBottom: '1rem' }}>📤 Multiple Input Methods</h3>
            <p style={{ color: '#555', lineHeight: '1.6' }}>
              Support for direct file uploads (.jar, .zip) and URL imports from CurseForge and Modrinth repositories.
            </p>
          </div>
          <div style={{ backgroundColor: '#f8f9fa', padding: '1.5rem', borderRadius: '8px' }}>
            <h3 style={{ color: '#007bff', marginBottom: '1rem' }}>🤖 Smart Assumptions</h3>
            <p style={{ color: '#555', lineHeight: '1.6' }}>
              AI-powered conversion that intelligently adapts Java-only features to work in Bedrock Edition.
            </p>
          </div>
          <div style={{ backgroundColor: '#f8f9fa', padding: '1.5rem', borderRadius: '8px' }}>
            <h3 style={{ color: '#007bff', marginBottom: '1rem' }}>⚡ Real-time Progress</h3>
            <p style={{ color: '#555', lineHeight: '1.6' }}>
              Live updates during conversion with detailed progress tracking and stage information.
            </p>
          </div>
        </div>
      </section>

      <section id="process" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          Conversion Process
        </h2>
        <div style={{ 
          backgroundColor: '#fff3e0', 
          padding: '1.5rem', 
          borderRadius: '8px',
          marginBottom: '2rem'
        }}>
          <h3 style={{ color: '#333', marginBottom: '1rem' }}>Process Stages:</h3>
          <div style={{ fontSize: '1.1rem', color: '#555', lineHeight: '1.8' }}>
            <div style={{ marginBottom: '1rem' }}>
              <strong>1. Analysis:</strong> The AI analyzes your Java mod structure, identifying blocks, items, recipes, and custom features.
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <strong>2. Mapping:</strong> Features are mapped to Bedrock Edition equivalents, with smart assumptions applied where needed.
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <strong>3. Conversion:</strong> Code logic is translated, assets are converted, and the add-on structure is created.
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <strong>4. Packaging:</strong> The final .mcaddon file is generated and validated for compatibility.
            </div>
          </div>
        </div>
      </section>

      <section id="assumptions" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          Smart Assumptions
        </h2>
        <div style={{ 
          backgroundColor: '#f3e5f5', 
          padding: '1.5rem', 
          borderRadius: '8px',
          marginBottom: '2rem'
        }}>
          <h3 style={{ color: '#333', marginBottom: '1rem' }}>How Smart Assumptions Work:</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', fontSize: '1rem' }}>
            <div>
              <h4 style={{ color: '#9c27b0', marginBottom: '0.5rem' }}>🌍 Custom Dimensions</h4>
              <p style={{ color: '#555', lineHeight: '1.6' }}>
                Converted to large explorable structures placed in existing dimensions, preserving the unique environment and biomes.
              </p>
            </div>
            <div>
              <h4 style={{ color: '#9c27b0', marginBottom: '0.5rem' }}>⚙️ Complex Machinery</h4>
              <p style={{ color: '#555', lineHeight: '1.6' }}>
                Simplified to decorative blocks or containers while maintaining visual design and basic functionality.
              </p>
            </div>
            <div>
              <h4 style={{ color: '#9c27b0', marginBottom: '0.5rem' }}>📱 Custom GUIs</h4>
              <p style={{ color: '#555', lineHeight: '1.6' }}>
                Transformed into book-based interfaces or sign interactions to preserve information access.
              </p>
            </div>
            <div>
              <h4 style={{ color: '#9c27b0', marginBottom: '0.5rem' }}>🎨 Advanced Rendering</h4>
              <p style={{ color: '#555', lineHeight: '1.6' }}>
                Client-side rendering features are adapted to work within Bedrock's rendering capabilities.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section style={{ 
        backgroundColor: '#e3f2fd', 
        padding: '2rem', 
        borderRadius: '8px',
        textAlign: 'center',
        marginTop: '3rem'
      }}>
        <h2 style={{ color: '#1976d2', marginBottom: '1rem' }}>Need Help?</h2>
        <p style={{ color: '#555', fontSize: '1.1rem', marginBottom: '1rem' }}>
          ModPorter AI is designed to be intuitive, but if you encounter issues or have questions:
        </p>
        <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', flexWrap: 'wrap' }}>
          <button style={{ 
            backgroundColor: '#007bff', 
            color: 'white', 
            border: 'none', 
            padding: '0.75rem 1.5rem', 
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}>
            View Examples
          </button>
          <button style={{ 
            backgroundColor: '#28a745', 
            color: 'white', 
            border: 'none', 
            padding: '0.75rem 1.5rem', 
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '1rem'
          }}>
            Get Support
          </button>
        </div>
      </section>
    </div>
  );
};