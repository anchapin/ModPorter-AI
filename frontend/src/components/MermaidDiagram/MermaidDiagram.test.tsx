import { render } from '@testing-library/react';
import { vi, describe, beforeEach, test, expect, afterEach } from 'vitest';
import { MermaidDiagram } from './MermaidDiagram';

// Mock mermaid library
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    init: vi.fn(),
  },
}));

describe('MermaidDiagram', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  test('renders diagram container with default props', () => {
    const chart = 'graph TD\n  A-->B';
    
    const { container } = render(<MermaidDiagram chart={chart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(diagramContainer).toHaveClass('mermaid-diagram');
  });

  test('renders with custom id and className', () => {
    const chart = 'graph TD\n  A-->B';
    const customId = 'custom-mermaid-id';
    const customClass = 'custom-class';
    
    const { container } = render(
      <MermaidDiagram 
        chart={chart} 
        id={customId} 
        className={customClass} 
      />
    );
    
    const diagramContainer = container.querySelector(`#${customId}`);
    expect(diagramContainer).toHaveAttribute('id', customId);
    expect(diagramContainer).toHaveClass('mermaid-diagram', customClass);
  });

  test('generates random id when not provided', () => {
    const chart = 'graph TD\n  A-->B';
    
    const { container } = render(<MermaidDiagram chart={chart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    const id = diagramContainer?.getAttribute('id');
    
    expect(id).toBeDefined();
    expect(id).toMatch(/^mermaid-[a-z0-9]{9}$/);
  });

  test('initializes mermaid with correct configuration', async () => {
    const chart = 'graph TD\n  A-->B';
    const mermaid = await import('mermaid');
    
    render(<MermaidDiagram chart={chart} />);
    
    expect(mermaid.default.initialize).toHaveBeenCalledWith({
      startOnLoad: true,
      theme: 'default',
      securityLevel: 'loose',
      flowchart: {
        useMaxWidth: true,
        htmlLabels: true,
        curve: 'basis',
      },
      sequence: {
        diagramMarginX: 50,
        diagramMarginY: 10,
        actorMargin: 50,
        width: 150,
        height: 65,
        boxMargin: 10,
        boxTextMargin: 5,
        noteMargin: 10,
        messageMargin: 35,
        mirrorActors: true,
        bottomMarginAdj: 1,
        useMaxWidth: true,
        rightAngles: false,
        showSequenceNumbers: false,
      },
      gantt: {
        titleTopMargin: 25,
        barHeight: 20,
        fontFamily: '"Open Sans", sans-serif',
        fontSize: 11,
        fontWeight: 'normal',
        gridLineStartPadding: 35,
        bottomPadding: 50,
        leftPadding: 75,
        topPadding: 50,
        numberSectionStyles: 4,
      },
    });
  });

  test('renders diagram content and calls mermaid.init', async () => {
    const chart = 'graph TD\n  A-->B\n  B-->C';
    const mermaid = await import('mermaid');
    
    const { container } = render(<MermaidDiagram chart={chart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.init).toHaveBeenCalled();
  });

  test('re-renders when chart content changes', async () => {
    const initialChart = 'graph TD\n  A-->B';
    const updatedChart = 'graph TD\n  A-->B\n  B-->C';
    const mermaid = await import('mermaid');
    
    const { rerender, container } = render(<MermaidDiagram chart={initialChart} />);
    
    let diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.init).toHaveBeenCalledTimes(1);
    
    rerender(<MermaidDiagram chart={updatedChart} />);
    
    diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.init).toHaveBeenCalledTimes(2);
  });

  test('applies correct styling', () => {
    const chart = 'graph TD\n  A-->B';
    
    const { container } = render(<MermaidDiagram chart={chart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toHaveStyle({
      display: 'flex',
      justifyContent: 'center',
      padding: '1rem',
      backgroundColor: '#fafafa',
      borderRadius: '8px',
      border: '1px solid #e0e0e0',
      margin: '1rem 0',
      overflow: 'auto',
    });
  });

  test('handles flowchart diagrams', async () => {
    const flowchartChart = `
      graph TD
        A[Start] --> B{Decision}
        B -->|Yes| C[Action 1]
        B -->|No| D[Action 2]
        C --> E[End]
        D --> E
    `;
    const mermaid = await import('mermaid');
    
    const { container } = render(<MermaidDiagram chart={flowchartChart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.initialize).toHaveBeenCalledWith(
      expect.objectContaining({
        flowchart: {
          useMaxWidth: true,
          htmlLabels: true,
          curve: 'basis',
        },
      })
    );
  });

  test('handles sequence diagrams', async () => {
    const sequenceChart = `
      sequenceDiagram
        participant A as User
        participant B as System
        A->>B: Request
        B-->>A: Response
    `;
    const mermaid = await import('mermaid');
    
    const { container } = render(<MermaidDiagram chart={sequenceChart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.initialize).toHaveBeenCalledWith(
      expect.objectContaining({
        sequence: expect.objectContaining({
          diagramMarginX: 50,
          diagramMarginY: 10,
          useMaxWidth: true,
        }),
      })
    );
  });

  test('handles gantt charts', async () => {
    const ganttChart = `
      gantt
        title Project Timeline
        dateFormat  YYYY-MM-DD
        section Phase 1
        Task 1: 2024-01-01, 3d
        Task 2: 2024-01-04, 2d
    `;
    const mermaid = await import('mermaid');
    
    const { container } = render(<MermaidDiagram chart={ganttChart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.initialize).toHaveBeenCalledWith(
      expect.objectContaining({
        gantt: expect.objectContaining({
          titleTopMargin: 25,
          barHeight: 20,
          fontFamily: '"Open Sans", sans-serif',
        }),
      })
    );
  });

  test('handles empty chart gracefully', async () => {
    const emptyChart = '';
    const mermaid = await import('mermaid');
    
    const { container } = render(<MermaidDiagram chart={emptyChart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(diagramContainer).toHaveClass('mermaid-diagram');
    expect(mermaid.default.init).toHaveBeenCalled();
  });

  test('handles complex architecture diagrams', async () => {
    const architectureChart = `
      graph TB
        subgraph "Frontend"
          UI[User Interface]
          API[API Layer]
        end
        
        subgraph "Backend"
          Server[Application Server]
          DB[(Database)]
        end
        
        UI --> API
        API --> Server
        Server --> DB
    `;
    const mermaid = await import('mermaid');
    
    const { container } = render(<MermaidDiagram chart={architectureChart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    expect(mermaid.default.initialize).toHaveBeenCalled();
    expect(mermaid.default.init).toHaveBeenCalled();
  });

  test('maintains accessibility with proper container structure', () => {
    const chart = 'graph TD\n  A-->B';
    
    const { container } = render(<MermaidDiagram chart={chart} />);
    
    const diagramContainer = container.querySelector('.mermaid-diagram');
    
    // Should have proper styling for accessibility
    expect(diagramContainer).toHaveStyle({
      overflow: 'auto', // Ensures scrollability for large diagrams
    });
    
    // Should have identifiable class for styling and testing
    expect(diagramContainer).toHaveClass('mermaid-diagram');
  });

  test('handles mermaid initialization errors gracefully', async () => {
    // Mock console.error to avoid noise in test output
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const mermaid = await import('mermaid');
    
    mermaid.default.initialize.mockImplementation(() => {
      throw new Error('Mermaid initialization failed');
    });
    
    const chart = 'graph TD\n  A-->B';
    
    // Should not throw error even if mermaid fails - should handle gracefully
    const { container } = render(<MermaidDiagram chart={chart} />);
    const diagramContainer = container.querySelector('.mermaid-diagram');
    expect(diagramContainer).toBeInTheDocument();
    
    // Should have logged the error
    expect(consoleSpy).toHaveBeenCalledWith('Error initializing or rendering Mermaid diagram:', expect.any(Error));
    
    consoleSpy.mockRestore();
  });
});