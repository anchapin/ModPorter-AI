/**
 * Documentation Page - Interactive system diagrams and technical documentation
 */

import React from 'react';
import { MermaidDiagram } from '../components/MermaidDiagram/MermaidDiagram';

const systemArchitecture = `
graph TB
    User[👤 User] --> Frontend[⚛️ React Frontend<br/>Vite + TypeScript]
    Frontend --> API[🔌 API Gateway<br/>FastAPI]
    
    API --> Backend[🐍 Backend Service<br/>Python + FastAPI]
    Backend --> AIEngine[🤖 AI Engine<br/>CrewAI + LangChain]
    Backend --> Database[(🗄️ PostgreSQL<br/>Conversion Data)]
    Backend --> Cache[(⚡ Redis<br/>Session Cache)]
    Backend --> FileStorage[📁 File Storage<br/>Conversion Assets]
    
    AIEngine --> JavaAnalyzer[🔍 Java Analyzer<br/>Agent]
    AIEngine --> BedrockArchitect[🏗️ Bedrock Architect<br/>Agent]
    AIEngine --> LogicTranslator[🔄 Logic Translator<br/>Agent]
    AIEngine --> AssetConverter[🎨 Asset Converter<br/>Agent]
    AIEngine --> PackagingAgent[📦 Packaging<br/>Agent]
    AIEngine --> QAValidator[✅ QA Validator<br/>Agent]
    
    classDef userClass fill:#e1f5fe
    classDef frontendClass fill:#f3e5f5
    classDef backendClass fill:#e8f5e8
    classDef aiClass fill:#fff3e0
    classDef dataClass fill:#fce4ec
    classDef agentClass fill:#f1f8e9
    
    class User userClass
    class Frontend,API frontendClass
    class Backend backendClass
    class AIEngine aiClass
    class Database,Cache,FileStorage dataClass
    class JavaAnalyzer,BedrockArchitect,LogicTranslator,AssetConverter,PackagingAgent,QAValidator agentClass
`;

const conversionFlow = `
flowchart TD
    Start([🚀 User Starts Conversion]) --> Upload{📤 Upload Method?}
    
    Upload -->|File| FileUpload[📁 File Upload<br/>PRD Feature 1]
    Upload -->|URL| URLInput[🔗 URL Input<br/>CurseForge/Modrinth]
    
    FileUpload --> Validate[✅ File Validation<br/>.jar/.zip check]
    URLInput --> Validate
    
    Validate --> |✅ Valid| StartConversion[🔄 Start Conversion<br/>PRD Feature 2]
    Validate --> |❌ Invalid| Error[❌ Show Error Message]
    Error --> Upload
    
    StartConversion --> JavaAnalysis[🔍 Java Analyzer Agent<br/>• Identify assets<br/>• Parse code logic<br/>• Find dependencies<br/>• Categorize features]
    
    JavaAnalysis --> Planning[🏗️ Bedrock Architect Agent<br/>• Map Java → Bedrock<br/>• Apply Smart Assumptions<br/>• Flag incompatible features<br/>• Generate conversion plan]
    
    Planning --> SmartAssumptions{🤖 Smart Assumptions<br/>Required?}
    
    SmartAssumptions -->|Yes| ApplyAssumptions[⚙️ Apply PRD Assumptions<br/>• Custom Dimensions → Structures<br/>• Complex Machinery → Simple Blocks<br/>• Custom GUI → Books/Signs<br/>• Exclude Client Rendering]
    SmartAssumptions -->|No| DirectConversion[🔄 Direct Conversion]
    
    ApplyAssumptions --> Complete[✅ Conversion Complete]
    DirectConversion --> Complete
    
    classDef startEnd fill:#4caf50,color:#fff
    classDef process fill:#2196f3,color:#fff
    classDef decision fill:#ff9800,color:#fff
    classDef agent fill:#9c27b0,color:#fff
    classDef assumption fill:#f44336,color:#fff
    
    class Start,Complete startEnd
    class FileUpload,URLInput,Validate,StartConversion,DirectConversion process
    class Upload,SmartAssumptions decision
    class JavaAnalysis,Planning agent
    class ApplyAssumptions assumption
`;

const smartAssumptions = `
flowchart TD
    Feature[🔍 Java Feature Detected] --> CheckAPI{🔌 Bedrock API<br/>Available?}
    
    CheckAPI -->|✅ Yes| DirectMap[✅ Direct Mapping<br/>• Blocks → Blocks<br/>• Items → Items<br/>• Basic Recipes → Recipes]
    
    CheckAPI -->|❌ No| FeatureType{🏷️ Feature Type?}
    
    FeatureType -->|🌍 Custom Dimension| DimensionAssumption[🏗️ Dimension → Structure<br/>• Extract biome data<br/>• Convert to large structure<br/>• Place in Overworld/End<br/>• Preserve visual elements]
    
    FeatureType -->|⚙️ Complex Machinery| MachineryAssumption[🔧 Machinery → Simple Block<br/>• Keep model & texture<br/>• Remove power system<br/>• Convert to container/decoration<br/>• Document original function]
    
    FeatureType -->|📱 Custom GUI| GUIAssumption[📖 GUI → Book Interface<br/>• Extract UI elements<br/>• Convert to book pages<br/>• Preserve information access<br/>• Adapt user interaction]
    
    DirectMap --> Success[✅ Conversion Success<br/>Feature works normally]
    DimensionAssumption --> Partial[⚠️ Partial Success<br/>Functionality changed]
    MachineryAssumption --> Partial
    GUIAssumption --> Partial
    
    classDef input fill:#e3f2fd
    classDef decision fill:#fff3e0
    classDef assumption fill:#f3e5f5
    classDef result fill:#e8f5e8
    
    class Feature input
    class CheckAPI,FeatureType decision
    class DimensionAssumption,MachineryAssumption,GUIAssumption assumption
    class DirectMap,Success,Partial result
`;

export const Documentation: React.FC = () => {
  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '2rem' }}>
      <header style={{ textAlign: 'center', marginBottom: '3rem' }}>
        <h1 style={{ fontSize: '2.5rem', color: '#333', marginBottom: '1rem' }}>
          ModPorter AI - Technical Documentation
        </h1>
        <p style={{ fontSize: '1.2rem', color: '#666', maxWidth: '600px', margin: '0 auto' }}>
          Interactive visual documentation of the ModPorter AI system architecture, 
          conversion process flow, and technical implementation details.
        </p>
      </header>

      <nav style={{ 
        backgroundColor: '#f8f9fa', 
        padding: '1rem', 
        borderRadius: '8px', 
        marginBottom: '2rem',
        textAlign: 'center'
      }}>
        <a href="#architecture" style={{ margin: '0 1rem', color: '#007bff' }}>System Architecture</a>
        <a href="#process" style={{ margin: '0 1rem', color: '#007bff' }}>Conversion Process</a>
        <a href="#assumptions" style={{ margin: '0 1rem', color: '#007bff' }}>Smart Assumptions</a>
      </nav>

      <section id="architecture" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          System Architecture Overview
        </h2>
        <p style={{ fontSize: '1.1rem', color: '#555', marginBottom: '2rem' }}>
          The ModPorter AI system follows a modern microservices architecture with a React frontend, 
          FastAPI backend, and a multi-agent AI engine powered by CrewAI and LangChain.
        </p>
        <MermaidDiagram chart={systemArchitecture} />
        
        <div style={{ 
          backgroundColor: '#f8f9fa', 
          padding: '1.5rem', 
          borderRadius: '8px',
          marginTop: '1rem'
        }}>
          <h3 style={{ color: '#333', marginBottom: '1rem' }}>Key Components:</h3>
          <ul style={{ fontSize: '1rem', color: '#555', lineHeight: '1.6' }}>
            <li><strong>React Frontend:</strong> Modern TypeScript-based UI with Vite build system</li>
            <li><strong>FastAPI Backend:</strong> High-performance Python API with async support</li>
            <li><strong>AI Engine:</strong> Multi-agent system with specialized conversion agents</li>
            <li><strong>Database Layer:</strong> PostgreSQL for persistence, Redis for caching</li>
            <li><strong>File Storage:</strong> Managed storage for conversion assets and outputs</li>
          </ul>
        </div>
      </section>

      <section id="process" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          Conversion Process Flow
        </h2>
        <p style={{ fontSize: '1.1rem', color: '#555', marginBottom: '2rem' }}>
          The conversion process implements all four PRD features through a sophisticated 
          multi-agent workflow that analyzes Java mods and intelligently converts them to Bedrock add-ons.
        </p>
        <MermaidDiagram chart={conversionFlow} />
        
        <div style={{ 
          backgroundColor: '#e8f5e8', 
          padding: '1.5rem', 
          borderRadius: '8px',
          marginTop: '1rem'
        }}>
          <h3 style={{ color: '#333', marginBottom: '1rem' }}>Process Stages:</h3>
          <ol style={{ fontSize: '1rem', color: '#555', lineHeight: '1.6' }}>
            <li><strong>Input Validation:</strong> Verify file types and repository URLs</li>
            <li><strong>Java Analysis:</strong> Parse mod structure and identify features</li>
            <li><strong>Conversion Planning:</strong> Map features and apply smart assumptions</li>
            <li><strong>Asset & Logic Translation:</strong> Convert code and assets to Bedrock format</li>
            <li><strong>Package Generation:</strong> Create valid .mcaddon files</li>
            <li><strong>Quality Validation:</strong> Verify output and generate reports</li>
          </ol>
        </div>
      </section>

      <section id="assumptions" style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '2rem', color: '#333', marginBottom: '1rem' }}>
          Smart Assumptions Decision Tree
        </h2>
        <p style={{ fontSize: '1.1rem', color: '#555', marginBottom: '2rem' }}>
          When Java features have no direct Bedrock equivalent, the AI engine applies intelligent 
          assumptions to preserve as much functionality as possible while maintaining compatibility.
        </p>
        <MermaidDiagram chart={smartAssumptions} />
        
        <div style={{ 
          backgroundColor: '#fff3e0', 
          padding: '1.5rem', 
          borderRadius: '8px',
          marginTop: '1rem'
        }}>
          <h3 style={{ color: '#333', marginBottom: '1rem' }}>Smart Assumption Categories:</h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', fontSize: '0.95rem' }}>
            <div>
              <h4 style={{ color: '#e65100', marginBottom: '0.5rem' }}>🌍 Custom Dimensions</h4>
              <p style={{ color: '#555' }}>Converted to large explorable structures in existing dimensions</p>
            </div>
            <div>
              <h4 style={{ color: '#e65100', marginBottom: '0.5rem' }}>⚙️ Complex Machinery</h4>
              <p style={{ color: '#555' }}>Simplified to decorative blocks while preserving visual design</p>
            </div>
            <div>
              <h4 style={{ color: '#e65100', marginBottom: '0.5rem' }}>📱 Custom GUIs</h4>
              <p style={{ color: '#555' }}>Transformed into book interfaces for information access</p>
            </div>
            <div>
              <h4 style={{ color: '#e65100', marginBottom: '0.5rem' }}>🎨 Client Rendering</h4>
              <p style={{ color: '#555' }}>Excluded with clear user notification and alternatives</p>
            </div>
          </div>
        </div>
      </section>

      <footer style={{ 
        textAlign: 'center', 
        padding: '2rem', 
        borderTop: '1px solid #e0e0e0',
        marginTop: '3rem',
        color: '#666'
      }}>
        <p>Documentation generated with Mermaid.js - Interactive diagrams for ModPorter AI</p>
        <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
          For technical details, see the <a href="/docs/API.md" style={{ color: '#007bff' }}>API Documentation</a> 
          and <a href="/docs/ARCHITECTURE.md" style={{ color: '#007bff' }}>Architecture Guide</a>
        </p>
      </footer>
    </div>
  );
};