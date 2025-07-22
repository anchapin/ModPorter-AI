/**
 * Dashboard Page - Day 5 Enhancement
 * Comprehensive dashboard with conversion, history, and management features
 */

import React, { useState, useCallback } from 'react';
import { ConversionUploadReal } from '../components/ConversionUpload/ConversionUploadReal';
import { ConversionHistory, useConversionHistory } from '../components/ConversionHistory';
import { PerformanceBenchmark } from '../components/PerformanceBenchmark';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'convert' | 'history' | 'performance'>('convert');
  // const [recentConversions, setRecentConversions] = useState<number>(0);
  // const [successRate, setSuccessRate] = useState<number>(0);
  
  const { addConversion, updateConversion, setHistoryRef } = useConversionHistory();

  // Handle conversion start
  const handleConversionStart = useCallback((jobId: string) => {
    console.log('Conversion started:', jobId);
    
    // Add to history
    addConversion({
      job_id: jobId,
      original_filename: 'Unknown', // Will be updated when we have the file info
      status: 'queued',
      created_at: new Date().toISOString(),
      options: {
        smartAssumptions: true,
        includeDependencies: true
      }
    });

    // Update stats
    // setRecentConversions(prev => prev + 1);
  }, [addConversion]);

  // Handle conversion completion
  const handleConversionComplete = useCallback((jobId: string) => {
    console.log('Conversion completed:', jobId);
    
    // Update conversion status
    updateConversion(jobId, {
      status: 'completed',
      completed_at: new Date().toISOString()
    });

    // Update success rate (simplified calculation)
    // setSuccessRate(prev => Math.min(prev + 5, 100));
  }, [updateConversion]);

  // Update conversion file info
  // const updateConversionInfo = useCallback((jobId: string, filename: string, fileSize?: number) => {
  //   updateConversion(jobId, {
  //     original_filename: filename,
  //     file_size: fileSize
  //   });
  // }, [updateConversion]);

  const getDashboardStats = () => {
    const storedHistory = localStorage.getItem('modporter_conversion_history');
    const history = storedHistory ? JSON.parse(storedHistory) : [];
    
    const total = history.length;
    const completed = history.filter((item: any) => item.status === 'completed').length;
    const failed = history.filter((item: any) => item.status === 'failed').length;
    const processing = history.filter((item: any) => item.status === 'processing').length;
    
    const actualSuccessRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    
    return {
      total,
      completed,
      failed,
      processing,
      successRate: actualSuccessRate
    };
  };

  const stats = getDashboardStats();

  return (
    <div className="dashboard">
      {/* Dashboard Header */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>
            <span className="header-icon">🎛️</span>
            ModPorter AI Dashboard
          </h1>
          <p className="header-subtitle">
            Convert, manage, and track your Minecraft mod conversions
          </p>
        </div>
        
        {/* Quick Stats */}
        <div className="quick-stats">
          <div className="stat-card">
            <div className="stat-icon">📊</div>
            <div className="stat-content">
              <div className="stat-number">{stats.total}</div>
              <div className="stat-label">Total Conversions</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon">✅</div>
            <div className="stat-content">
              <div className="stat-number">{stats.completed}</div>
              <div className="stat-label">Completed</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon">📈</div>
            <div className="stat-content">
              <div className="stat-number">{stats.successRate}%</div>
              <div className="stat-label">Success Rate</div>
            </div>
          </div>
          
          <div className="stat-card">
            <div className="stat-icon">⏳</div>
            <div className="stat-content">
              <div className="stat-number">{stats.processing}</div>
              <div className="stat-label">In Progress</div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="dashboard-nav">
        <button
          className={`nav-tab ${activeTab === 'convert' ? 'active' : ''}`}
          onClick={() => setActiveTab('convert')}
        >
          <span className="tab-icon">🚀</span>
          Convert Mods
        </button>
        
        <button
          className={`nav-tab ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <span className="tab-icon">📋</span>
          Conversion History
        </button>
        
        <button
          className={`nav-tab ${activeTab === 'performance' ? 'active' : ''}`}
          onClick={() => setActiveTab('performance')}
        >
          <span className="tab-icon">⚡</span>
          Performance
        </button>
      </div>

      {/* Tab Content */}
      <div className="dashboard-content">
        {activeTab === 'convert' && (
          <div className="convert-tab">
            <div className="tab-header">
              <h2>
                <span className="section-icon">🚀</span>
                Convert Your Mods
              </h2>
              <p className="section-description">
                Upload your Java Edition mods and convert them to Bedrock Edition using AI
              </p>
            </div>
            
            <ConversionUploadReal
              onConversionStart={handleConversionStart}
              onConversionComplete={handleConversionComplete}
            />
            
            {/* Conversion Tips */}
            <div className="conversion-tips">
              <h3>💡 Conversion Tips</h3>
              <div className="tips-grid">
                <div className="tip-card">
                  <div className="tip-icon">📦</div>
                  <div className="tip-content">
                    <h4>File Formats</h4>
                    <p>Supports .jar files and .zip modpack archives. Ensure your files are not corrupted.</p>
                  </div>
                </div>
                
                <div className="tip-card">
                  <div className="tip-icon">🧠</div>
                  <div className="tip-content">
                    <h4>Smart Assumptions</h4>
                    <p>Enable for better conversion rates. AI will make intelligent assumptions for incompatible features.</p>
                  </div>
                </div>
                
                <div className="tip-card">
                  <div className="tip-icon">⚡</div>
                  <div className="tip-content">
                    <h4>Performance</h4>
                    <p>Smaller mods convert faster. Large modpacks may take several minutes to process.</p>
                  </div>
                </div>
                
                <div className="tip-card">
                  <div className="tip-icon">🔧</div>
                  <div className="tip-content">
                    <h4>Dependencies</h4>
                    <p>Include dependencies option will attempt to convert required libraries and APIs.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div className="history-tab">
            <div className="tab-header">
              <h2>
                <span className="section-icon">📋</span>
                Conversion History
              </h2>
              <p className="section-description">
                View, download, and manage your previous conversions
              </p>
            </div>
            
            <ConversionHistory 
              ref={setHistoryRef}
              className="dashboard-history"
              maxItems={100}
            />
          </div>
        )}

        {activeTab === 'performance' && (
          <div className="performance-tab">
            <div className="tab-header">
              <h2>
                <span className="section-icon">⚡</span>
                Performance Benchmarks
              </h2>
              <p className="section-description">
                Monitor system performance and benchmark conversion speed
              </p>
            </div>
            
            <PerformanceBenchmark />
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;