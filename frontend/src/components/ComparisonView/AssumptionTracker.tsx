import React, { useState } from 'react';

interface SmartAssumption {
  id: string;
  description: string;
  impact?: string;
  confidence?: string;
}

interface AssumptionTrackerProps {
  assumptions: SmartAssumption[];
}

const AssumptionTracker: React.FC<AssumptionTrackerProps> = ({ assumptions }) => {
  const [expandedAssumption, setExpandedAssumption] = useState<string | null>(null);

  const getImpactColor = (impact?: string) => {
    if (!impact) return '#6b7280';
    if (impact.toLowerCase().includes('high')) return '#dc2626';
    if (impact.toLowerCase().includes('medium')) return '#d97706';
    return '#059669';
  };

  const getImpactIcon = (impact?: string) => {
    if (!impact) return '?';
    if (impact.toLowerCase().includes('high')) return '⚠️';
    if (impact.toLowerCase().includes('medium')) return '⚡';
    return '✅';
  };

  const getConfidenceIcon = (confidence?: string) => {
    if (!confidence) return '❓';
    const conf = parseFloat(confidence);
    if (conf >= 0.8) return '🎯';
    if (conf >= 0.6) return '🎲';
    return '❌';
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #e5e7eb', borderRadius: '8px', margin: '20px 0' }}>
      <h2 style={{ marginBottom: '20px', color: '#1f2937' }}>Smart Assumptions Applied ({assumptions.length})</h2>
      
      {assumptions.length === 0 ? (
        <div style={{ 
          textAlign: 'center', 
          padding: '40px 20px',
          backgroundColor: '#f9fafb',
          borderRadius: '8px',
          border: '2px dashed #d1d5db'
        }}>
          <div style={{ fontSize: '48px', marginBottom: '10px' }}>🎯</div>
          <p style={{ color: '#6b7280', fontStyle: 'italic', margin: 0 }}>
            No smart assumptions were needed for this conversion.
          </p>
          <p style={{ color: '#9ca3af', fontSize: '14px', margin: '5px 0 0 0' }}>
            This indicates a high-fidelity conversion with minimal compromises.
          </p>
        </div>
      ) : (
        <>
          <div style={{ 
            backgroundColor: '#fef3c7', 
            border: '1px solid #f59e0b', 
            borderRadius: '6px', 
            padding: '12px',
            marginBottom: '20px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '20px' }}>💡</span>
              <strong style={{ color: '#92400e' }}>What are Smart Assumptions?</strong>
            </div>
            <p style={{ margin: 0, color: '#92400e', fontSize: '14px' }}>
              Smart assumptions are intelligent decisions made during conversion when direct Java-to-Bedrock equivalents don't exist. 
              They preserve the mod's core functionality while adapting to Bedrock's capabilities.
            </p>
          </div>

          <div style={{ display: 'grid', gap: '12px' }}>
            {assumptions.map((assumption) => (
              <div 
                key={assumption.id}
                style={{ 
                  border: '1px solid #e5e7eb', 
                  borderRadius: '8px', 
                  overflow: 'hidden',
                  backgroundColor: '#ffffff'
                }}
              >
                <div 
                  style={{ 
                    padding: '15px',
                    cursor: 'pointer',
                    backgroundColor: expandedAssumption === assumption.id ? '#f9fafb' : '#ffffff',
                    borderBottom: expandedAssumption === assumption.id ? '1px solid #e5e7eb' : 'none',
                    transition: 'background-color 0.2s'
                  }}
                  onClick={() => setExpandedAssumption(
                    expandedAssumption === assumption.id ? null : assumption.id
                  )}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                        <span style={{ 
                          backgroundColor: '#ddd6fe', 
                          color: '#5b21b6',
                          padding: '4px 8px', 
                          borderRadius: '4px', 
                          fontSize: '12px',
                          fontWeight: 'bold',
                          fontFamily: 'monospace'
                        }}>
                          {assumption.id}
                        </span>
                        {assumption.impact && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span>{getImpactIcon(assumption.impact)}</span>
                            <span style={{ 
                              fontSize: '12px', 
                              color: getImpactColor(assumption.impact),
                              fontWeight: 'bold'
                            }}>
                              {assumption.impact.split(' - ')[0]} Impact
                            </span>
                          </div>
                        )}
                        {assumption.confidence && (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                            <span>{getConfidenceIcon(assumption.confidence)}</span>
                            <span style={{ fontSize: '12px', color: '#6b7280' }}>
                              {(parseFloat(assumption.confidence) * 100).toFixed(0)}% confidence
                            </span>
                          </div>
                        )}
                      </div>
                      <p style={{ 
                        margin: 0, 
                        color: '#374151',
                        fontSize: '14px',
                        lineHeight: '1.5'
                      }}>
                        {assumption.description}
                      </p>
                    </div>
                    <div style={{ 
                      marginLeft: '10px',
                      color: '#9ca3af',
                      fontSize: '12px',
                      transform: expandedAssumption === assumption.id ? 'rotate(180deg)' : 'rotate(0deg)',
                      transition: 'transform 0.2s'
                    }}>
                      ▼
                    </div>
                  </div>
                </div>
                
                {expandedAssumption === assumption.id && (
                  <div style={{ padding: '15px', backgroundColor: '#f9fafb' }}>
                    <h4 style={{ margin: '0 0 10px 0', color: '#374151', fontSize: '14px' }}>
                      Detailed Impact Analysis
                    </h4>
                    <div style={{ fontSize: '13px', color: '#6b7280', lineHeight: '1.5' }}>
                      {assumption.impact ? (
                        <div style={{ marginBottom: '10px' }}>
                          <strong>Impact:</strong> {assumption.impact}
                        </div>
                      ) : null}
                      
                      <div style={{ 
                        backgroundColor: '#ffffff',
                        border: '1px solid #e5e7eb',
                        borderRadius: '4px',
                        padding: '10px'
                      }}>
                        <strong>Why this assumption was needed:</strong>
                        <br />
                        This conversion choice was made because Bedrock Edition has different capabilities 
                        and limitations compared to Java Edition modding. The assumption ensures the 
                        mod's core functionality is preserved while working within Bedrock's constraints.
                      </div>
                      
                      {assumption.confidence && (
                        <div style={{ marginTop: '10px' }}>
                          <strong>Confidence Level:</strong> {(parseFloat(assumption.confidence) * 100).toFixed(1)}%
                          <br />
                          <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                            Higher confidence indicates more reliable conversion accuracy.
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          
          <div style={{ 
            marginTop: '20px',
            padding: '15px',
            backgroundColor: '#f0f9ff',
            border: '1px solid #0ea5e9',
            borderRadius: '6px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <span style={{ fontSize: '18px' }}>💡</span>
              <strong style={{ color: '#0369a1' }}>Pro Tip</strong>
            </div>
            <p style={{ margin: 0, color: '#0369a1', fontSize: '14px' }}>
              Review these assumptions carefully to understand how your mod's behavior might differ in Bedrock Edition. 
              Consider testing the converted add-on to ensure it meets your expectations.
            </p>
          </div>
        </>
      )}
    </div>
  );
};

export default AssumptionTracker;
