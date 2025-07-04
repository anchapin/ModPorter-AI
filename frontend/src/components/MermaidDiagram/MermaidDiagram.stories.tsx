/**
 * Storybook stories for MermaidDiagram component
 * Interactive documentation diagrams
 */

import type { Meta, StoryObj } from '@storybook/react';
import { MermaidDiagram } from './MermaidDiagram';

const meta: Meta<typeof MermaidDiagram> = {
  title: 'Documentation/MermaidDiagram',
  component: MermaidDiagram,
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: `
## Interactive System Diagrams

The MermaidDiagram component renders interactive system architecture and process flow diagrams using Mermaid.js.

### Features:
- System architecture visualization
- Process flow documentation
- Interactive diagram elements
- Responsive design
- High-quality SVG output
        `,
      },
    },
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

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

export const SystemArchitecture: Story = {
  args: {
    chart: systemArchitecture,
  },
  parameters: {
    docs: {
      description: {
        story: 'Complete system architecture showing all components and their relationships.',
      },
    },
  },
};

export const ConversionFlow: Story = {
  args: {
    chart: conversionFlow,
  },
  parameters: {
    docs: {
      description: {
        story: 'Conversion process flow from user input to completed add-on.',
      },
    },
  },
};

export const SmartAssumptionsTree: Story = {
  args: {
    chart: smartAssumptions,
  },
  parameters: {
    docs: {
      description: {
        story: 'Decision tree for applying smart assumptions during conversion.',
      },
    },
  },
};