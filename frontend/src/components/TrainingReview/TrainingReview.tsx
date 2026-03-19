/**
 * Training Data Review Queue Component
 * 
 * Manual review interface for approving/rejecting training data
 * for custom model fine-tuning.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { 
  Card, 
  Button, 
  Badge, 
  Table, 
  Modal, 
  Form, 
  Select, 
  Input, 
  message, 
  Space, 
  Tag, 
  Typography, 
  Statistic, 
  Row, 
  Col,
  Empty,
  Spin,
  Alert
} from 'antd';
import { 
  CheckOutlined, 
  CloseOutlined, 
  EyeOutlined, 
  ReloadOutlined, 
  ExclamationCircleOutlined,
  AuditOutlined,
  StarOutlined,
  WarningOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface TrainingDataItem {
  id: string;
  job_id: string;
  input_source: string;
  output_target: string;
  mod_type: string;
  complexity: string;
  automated_score: number;
  review_status?: string;
  manual_score?: number;
  created_at: string;
}

interface ReviewStats {
  pending: number;
  approved: number;
  rejected: number;
  needs_revision: number;
  total: number;
  average_score: number;
}

interface ReviewFormValues {
  status: 'approved' | 'rejected' | 'needs_revision';
  reviewer_notes?: string;
  quality_score?: number;
  issues_found?: string[];
}

const TrainingReview: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [reviewQueue, setReviewQueue] = useState<TrainingDataItem[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [selectedItem, setSelectedItem] = useState<TrainingDataItem | null>(null);
  const [detailModalVisible, setDetailModalVisible] = useState(false);
  const [reviewModalVisible, setReviewModalVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form] = Form.useForm();

  // Fetch review queue
  const fetchReviewQueue = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/v1/ai/training/review/queue?limit=20');
      if (!response.ok) throw new Error('Failed to fetch review queue');
      
      const data = await response.json();
      setReviewQueue(data);
    } catch (error) {
      console.error('Error fetching review queue:', error);
      message.error('Failed to load review queue');
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch stats
  const fetchStats = useCallback(async () => {
    try {
      const response = await fetch('/api/v1/ai/training/review/stats');
      if (!response.ok) throw new Error('Failed to fetch stats');
      
      const data = await response.json();
      setStats(data);
    } catch (error) {
      console.error('Error fetching stats:', error);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchReviewQueue();
    fetchStats();
  }, [fetchReviewQueue, fetchStats]);

  // View item details
  const handleViewDetails = (item: TrainingDataItem) => {
    setSelectedItem(item);
    setDetailModalVisible(true);
  };

  // Submit review
  const handleSubmitReview = async (values: ReviewFormValues) => {
    if (!selectedItem) return;
    
    setSubmitting(true);
    try {
      const response = await fetch('/api/v1/ai/training/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          training_data_id: selectedItem.id,
          status: values.status,
          reviewer_notes: values.reviewer_notes,
          quality_score: values.quality_score,
          issues_found: values.issues_found
        })
      });

      if (!response.ok) throw new Error('Failed to submit review');

      message.success('Review submitted successfully');
      setReviewModalVisible(false);
      form.resetFields();
      fetchReviewQueue();
      fetchStats();
    } catch (error) {
      console.error('Error submitting review:', error);
      message.error('Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  // Quick approve
  const handleQuickApprove = async (item: TrainingDataItem) => {
    try {
      const response = await fetch('/api/v1/ai/training/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          training_data_id: item.id,
          status: 'approved',
          quality_score: item.automated_score
        })
      });

      if (!response.ok) throw new Error('Failed to approve');

      message.success('Item approved');
      fetchReviewQueue();
      fetchStats();
    } catch (error) {
      console.error('Error approving item:', error);
      message.error('Failed to approve item');
    }
  };

  // Quick reject
  const handleQuickReject = async (item: TrainingDataItem) => {
    try {
      const response = await fetch('/api/v1/ai/training/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          training_data_id: item.id,
          status: 'rejected',
          reviewer_notes: 'Rejected via quick action'
        })
      });

      if (!response.ok) throw new Error('Failed to reject');

      message.warning('Item rejected');
      fetchReviewQueue();
      fetchStats();
    } catch (error) {
      console.error('Error rejecting item:', error);
      message.error('Failed to reject item');
    }
  };

  // Open review modal
  const openReviewModal = (item: TrainingDataItem) => {
    setSelectedItem(item);
    form.setFieldsValue({
      status: 'approved',
      quality_score: item.automated_score,
      issues_found: []
    });
    setReviewModalVisible(true);
  };

  // Table columns
  const columns: ColumnsType<TrainingDataItem> = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 100,
      render: (id: string) => <Text copyable>{id.substring(0, 8)}...</Text>
    },
    {
      title: 'Job ID',
      dataIndex: 'job_id',
      key: 'job_id',
      width: 100,
      render: (id: string) => <Text copyable>{id.substring(0, 8)}...</Text>
    },
    {
      title: 'Mod Type',
      dataIndex: 'mod_type',
      key: 'mod_type',
      width: 100,
      render: (type: string) => (
        <Tag color="blue">{type || 'unknown'}</Tag>
      )
    },
    {
      title: 'Complexity',
      dataIndex: 'complexity',
      key: 'complexity',
      width: 100,
      render: (complexity: string) => {
        const color = complexity === 'simple' ? 'green' : 
                      complexity === 'medium' ? 'orange' : 'red';
        return <Tag color={color}>{complexity}</Tag>;
      }
    },
    {
      title: 'Auto Score',
      dataIndex: 'automated_score',
      key: 'automated_score',
      width: 100,
      render: (score: number) => (
        <Space>
          <StarOutlined style={{ color: score >= 0.7 ? '#faad14' : '#d9d9d9' }} />
          <Text>{(score * 100).toFixed(0)}%</Text>
        </Space>
      )
    },
    {
      title: 'Status',
      dataIndex: 'review_status',
      key: 'review_status',
      width: 120,
      render: (status?: string) => {
        if (!status) return <Badge status="default" text="Pending" />;
        
        const statusConfig: Record<string, { status: 'success' | 'error' | 'warning' | 'processing' | 'default'; text: string }> = {
          approved: { status: 'success', text: 'Approved' },
          rejected: { status: 'error', text: 'Rejected' },
          pending: { status: 'processing', text: 'Pending' },
          needs_revision: { status: 'warning', text: 'Needs Revision' }
        };
        
        const config = statusConfig[status] || { status: 'default' as const, text: status };
        return <Badge {...config} />;
      }
    },
    {
      title: 'Actions',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button 
            type="text" 
            icon={<EyeOutlined />} 
            onClick={() => handleViewDetails(record)}
          >
            View
          </Button>
          <Button 
            type="text" 
            icon={<CheckOutlined />} 
            onClick={() => handleQuickApprove(record)}
            style={{ color: '#52c41a' }}
          >
            Approve
          </Button>
          <Button 
            type="text" 
            icon={<CloseOutlined />} 
            onClick={() => handleQuickReject(record)}
            style={{ color: '#ff4d4f' }}
          >
            Reject
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" size="large" style={{ width: '100%' }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <Title level={2} style={{ margin: 0 }}>
              <AuditOutlined /> Training Data Review Queue
            </Title>
            <Text type="secondary">
              Review and approve conversion data for model fine-tuning
            </Text>
          </div>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={() => { fetchReviewQueue(); fetchStats(); }}
            loading={loading}
          >
            Refresh
          </Button>
        </div>

        {/* Stats */}
        {stats && (
          <Row gutter={16}>
            <Col span={6}>
              <Card>
                <Statistic 
                  title="Pending Review" 
                  value={stats.pending} 
                  valueStyle={{ color: '#1890ff' }}
                  prefix={<ExclamationCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic 
                  title="Approved" 
                  value={stats.approved} 
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic 
                  title="Rejected" 
                  value={stats.rejected} 
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix={<CloseOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic 
                  title="Avg Quality Score" 
                  value={stats.average_score * 100} 
                  precision={1}
                  suffix="%"
                  prefix={<StarOutlined />}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* Alert */}
        <Alert
          message="Training Data Review"
          description="Review conversion data to ensure quality before using for model fine-tuning. Approved data with quality scores above 70% will be exported for training."
          type="info"
          showIcon
        />

        {/* Review Queue Table */}
        <Card>
          <Table
            columns={columns}
            dataSource={reviewQueue}
            rowKey="id"
            loading={loading}
            locale={{ emptyText: <Empty description="No items in review queue" /> }}
            pagination={{
              pageSize: 10,
              showSizeChanger: true,
              showTotal: (total) => `Total ${total} items`
            }}
          />
        </Card>
      </Space>

      {/* Detail Modal */}
      <Modal
        title="Training Data Details"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        width={800}
        footer={[
          <Button key="reject" onClick={() => {
            setDetailModalVisible(false);
            openReviewModal(selectedItem!);
          }}>
            <CloseOutlined /> Reject
          </Button>,
          <Button key="approve" type="primary" onClick={() => {
            setDetailModalVisible(false);
            handleQuickApprove(selectedItem!);
          }}>
            <CheckOutlined /> Approve
          </Button>
        ]}
      >
        {selectedItem && (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <Row gutter={16}>
              <Col span={12}>
                <Text type="secondary">Job ID:</Text>
                <Text copyable style={{ display: 'block' }}>{selectedItem.job_id}</Text>
              </Col>
              <Col span={12}>
                <Text type="secondary">Created:</Text>
                <Text style={{ display: 'block' }}>{new Date(selectedItem.created_at).toLocaleString()}</Text>
              </Col>
            </Row>
            
            <Row gutter={16}>
              <Col span={8}>
                <Tag color="blue">{selectedItem.mod_type || 'unknown'}</Tag>
              </Col>
              <Col span={8}>
                <Tag color="orange">{selectedItem.complexity}</Tag>
              </Col>
              <Col span={8}>
                <Text>Auto Score: {(selectedItem.automated_score * 100).toFixed(0)}%</Text>
              </Col>
            </Row>

            <div>
              <Text strong>Input Source Preview:</Text>
              <Card size="small" style={{ marginTop: 8, maxHeight: 200, overflow: 'auto' }}>
                <pre style={{ margin: 0, whiteSpace: 'pre-wrap', fontSize: 12 }}>
                  {selectedItem.input_source}
                </pre>
              </Card>
            </div>
          </Space>
        )}
      </Modal>

      {/* Review Modal */}
      <Modal
        title="Submit Review"
        open={reviewModalVisible}
        onCancel={() => setReviewModalVisible(false)}
        footer={null}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmitReview}
        >
          <Form.Item
            name="status"
            label="Review Decision"
            rules={[{ required: true, message: 'Please select a decision' }]}
          >
            <Select>
              <Select.Option value="approved">
                <Space>
                  <CheckOutlined style={{ color: '#52c41a' }} />
                  Approve for Training
                </Space>
              </Select.Option>
              <Select.Option value="rejected">
                <Space>
                  <CloseOutlined style={{ color: '#ff4d4f' }} />
                  Reject
                </Space>
              </Select.Option>
              <Select.Option value="needs_revision">
                <Space>
                  <WarningOutlined style={{ color: '#faad14' }} />
                  Needs Revision
                </Space>
              </Select.Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="quality_score"
            label="Quality Score Override"
          >
            <Input type="number" min={0} max={100} addonAfter="%" />
          </Form.Item>

          <Form.Item
            name="reviewer_notes"
            label="Reviewer Notes"
          >
            <TextArea rows={3} placeholder="Optional notes about this training data..." />
          </Form.Item>

          <Form.Item>
            <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
              <Button onClick={() => setReviewModalVisible(false)}>Cancel</Button>
              <Button type="primary" htmlType="submit" loading={submitting}>
                Submit Review
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default TrainingReview;
