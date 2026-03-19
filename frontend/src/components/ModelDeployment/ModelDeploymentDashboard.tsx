/**
 * Model Deployment Dashboard Component
 * 
 * Dashboard for monitoring model deployments, A/B tests, and performance metrics.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Card, 
  Row, 
  Col, 
  Statistic, 
  Table, 
  Tag, 
  Button, 
  Space, 
  Typography, 
  Badge, 
  Progress, 
  Timeline,
  Select,
  Space as AntSpace,
  Alert
} from 'antd';
import { 
  RocketOutlined, 
  ExperimentOutlined, 
  LineChartOutlined, 
  SwapOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text } = Typography;

interface ModelVersion {
  version: string;
  model_path: string;
  base_model: string;
  status: string;
  created_at: string;
  trained_at?: string;
  metrics: Record<string, number>;
}

interface Deployment {
  deployment_id: string;
  version: string;
  strategy: string;
  status: string;
  canary_percentage: number;
  started_at: string;
}

interface ABTest {
  test_id: string;
  control_version: string;
  treatment_version: string;
  traffic_split: number;
  status: string;
  start_time: string;
  results?: {
    control_avg: number;
    treatment_avg: number;
    improvement_pct: number;
  };
}

const ModelDeploymentDashboard: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelVersion[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [abTests, setABTests] = useState<ABTest[]>([]);
  const [selectedModel, setSelectedModel] = useState<string | null>(null);

  // Fetch models
  const fetchModels = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/ai/models/registry');
      if (!response.ok) throw new Error('Failed to fetch models');
      const data = await response.json();
      setModels(data);
    } catch (error) {
      console.error('Error fetching models:', error);
    }
  }, []);

  // Fetch deployments
  const fetchDeployments = useCallback(async () => {
    // In production, fetch from API
    // For now, use placeholder
    setDeployments([]);
  }, []);

  // Fetch A/B tests
  const fetchABTests = useCallback(async () => {
    // In production, fetch from API
    // For now, use placeholder
    setABTests([]);
  }, []);

  // Initial load
  useEffect(() => {
    fetchModels();
    fetchDeployments();
    fetchABTests();
  }, [fetchModels, fetchDeployments, fetchABTests]);

  // Refresh
  const handleRefresh = () => {
    fetchModels();
    fetchDeployments();
    fetchABTests();
  };

  // Get status color
  const getStatusColor = (status: string) => {
    const colors: Record<string, string> = {
      training: 'processing',
      ready: 'success',
      deployed: 'success',
      testing: 'warning',
      rollback: 'error',
      archived: 'default',
      failed: 'error',
    };
    return colors[status] || 'default';
  };

  // Model columns
  const modelColumns: ColumnsType<ModelVersion> = [
    {
      title: 'Version',
      dataIndex: 'version',
      key: 'version',
      render: (version: string) => <Text strong>{version}</Text>
    },
    {
      title: 'Base Model',
      dataIndex: 'base_model',
      key: 'base_model',
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Badge status={getStatusColor(status) as any} text={status} />
      )
    },
    {
      title: 'Created',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString()
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record) => (
        <Space>
          <Button size="small" onClick={() => setSelectedModel(record.version)}>
            Details
          </Button>
        </Space>
      )
    }
  ];

  // Stats
  const stats = {
    totalModels: models.length,
    deployed: models.filter(m => m.status === 'deployed').length,
    testing: models.filter(m => m.status === 'testing').length,
    ready: models.filter(m => m.status === 'ready').length,
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              <RocketOutlined /> Model Deployment Dashboard
            </Title>
            <Text type="secondary">
              Manage model versions, A/B tests, and deployments
            </Text>
          </div>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={handleRefresh}
            loading={loading}
          >
            Refresh
          </Button>
        </div>

        {/* Stats */}
        <Row gutter={16}>
          <Col span={6}>
            <Card>
              <Statistic 
                title="Total Models" 
                value={stats.totalModels} 
                prefix={<RocketOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="Deployed" 
                value={stats.deployed} 
                valueStyle={{ color: '#52c41a' }}
                prefix={<CheckCircleOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="Testing" 
                value={stats.testing} 
                valueStyle={{ color: '#faad14' }}
                prefix={<ExperimentOutlined />}
              />
            </Card>
          </Col>
          <Col span={6}>
            <Card>
              <Statistic 
                title="Ready" 
                value={stats.ready} 
                valueStyle={{ color: '#1890ff' }}
                prefix={<ClockCircleOutlined />}
              />
            </Card>
          </Col>
        </Row>

        {/* Active Deployments */}
        <Card 
          title={<Space><SwapOutlined /> Active Deployments</Space>}
          extra={
            <Button type="primary">New Deployment</Button>
          }
        >
          {deployments.length > 0 ? (
            <Table
              dataSource={deployments}
              rowKey="deployment_id"
              columns={[
                {
                  title: 'Deployment ID',
                  dataIndex: 'deployment_id',
                  key: 'deployment_id',
                  render: (id: string) => id.substring(0, 8)
                },
                {
                  title: 'Version',
                  dataIndex: 'version',
                  key: 'version',
                  render: (v: string) => <Tag>{v}</Tag>
                },
                {
                  title: 'Strategy',
                  dataIndex: 'strategy',
                  key: 'strategy',
                },
                {
                  title: 'Canary %',
                  dataIndex: 'canary_percentage',
                  key: 'canary_percentage',
                  render: (pct: number) => <Progress percent={pct} size="small" />
                },
                {
                  title: 'Status',
                  dataIndex: 'status',
                  key: 'status',
                  render: (status: string) => (
                    <Badge 
                      status={status === 'running' ? 'processing' : 'success' as any} 
                      text={status} 
                    />
                  )
                },
                {
                  title: 'Actions',
                  key: 'actions',
                  render: () => (
                    <Space>
                      <Button size="small" type="primary">Promote</Button>
                      <Button size="small" danger>Rollback</Button>
                    </Space>
                  )
                }
              ]}
            />
          ) : (
            <Alert
              message="No Active Deployments"
              description="Start a deployment to see canary progress here."
              type="info"
              showIcon
            />
          )}
        </Card>

        {/* A/B Tests */}
        <Card 
          title={<Space><ExperimentOutlined /> A/B Tests</Space>}
          extra={
            <Button type="primary">New A/B Test</Button>
          }
        >
          {abTests.length > 0 ? (
            <Table
              dataSource={abTests}
              rowKey="test_id"
              columns={[
                {
                  title: 'Test ID',
                  dataIndex: 'test_id',
                  key: 'test_id',
                },
                {
                  title: 'Control',
                  dataIndex: 'control_version',
                  key: 'control_version',
                  render: (v: string) => <Tag color="blue">{v}</Tag>
                },
                {
                  title: 'Treatment',
                  dataIndex: 'treatment_version',
                  key: 'treatment_version',
                  render: (v: string) => <Tag color="green">{v}</Tag>
                },
                {
                  title: 'Split',
                  dataIndex: 'traffic_split',
                  key: 'traffic_split',
                  render: (split: number) => `${(split * 100).toFixed(0)}%`
                },
                {
                  title: 'Status',
                  dataIndex: 'status',
                  key: 'status',
                  render: (status: string) => (
                    <Badge 
                      status={status === 'running' ? 'processing' : 'success' as any} 
                      text={status} 
                    />
                  )
                },
                {
                  title: 'Improvement',
                  dataIndex: 'results',
                  key: 'improvement',
                  render: (results?: { improvement_pct: number }) => {
                    if (!results) return '-';
                    const { improvement_pct } = results;
                    return (
                      <Space>
                        {improvement_pct > 0 ? (
                          <ArrowUpOutlined style={{ color: '#52c41a' }} />
                        ) : (
                          <ArrowDownOutlined style={{ color: '#ff4d4f' }} />
                        )}
                        {Math.abs(improvement_pct).toFixed(1)}%
                      </Space>
                    );
                  }
                }
              ]}
            />
          ) : (
            <Alert
              message="No Active A/B Tests"
              description="Create an A/B test to compare model performance."
              type="info"
              showIcon
            />
          )}
        </Card>

        {/* Model Registry */}
        <Card 
          title={<Space><RocketOutlined /> Model Registry</Space>}
        >
          <Table
            dataSource={models}
            columns={modelColumns}
            rowKey="version"
            pagination={{ pageSize: 5 }}
          />
        </Card>
      </Space>
    </div>
  );
};

export default ModelDeploymentDashboard;
