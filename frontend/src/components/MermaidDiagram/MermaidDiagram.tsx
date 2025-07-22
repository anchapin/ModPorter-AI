/**
 * MermaidDiagram Component - Interactive Mermaid diagram renderer
 * Displays system architecture and process flow diagrams
 */

import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

interface MermaidDiagramProps {
  chart: string;
  id?: string;
  className?: string;
}

export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({
  chart,
  id = `mermaid-${Math.random().toString(36).substr(2, 9)}`,
  className = '',
}) => {
  const chartRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      // Initialize mermaid with configuration
      mermaid.initialize({
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

      // Render the diagram
      if (chartRef.current) {
        chartRef.current.innerHTML = chart;
        mermaid.init(undefined, chartRef.current);
      }
    } catch (error) {
      console.error('Error initializing or rendering Mermaid diagram:', error);
      // Gracefully handle errors by showing the chart content as plain text
      if (chartRef.current) {
        chartRef.current.innerHTML = chart;
      }
    }
  }, [chart]);

  return (
    <div 
      ref={chartRef}
      id={id}
      className={`mermaid-diagram ${className}`}
      style={{
        display: 'flex',
        justifyContent: 'center',
        padding: '1rem',
        backgroundColor: '#fafafa',
        borderRadius: '8px',
        border: '1px solid #e0e0e0',
        margin: '1rem 0',
        overflow: 'auto',
      }}
    />
  );
};