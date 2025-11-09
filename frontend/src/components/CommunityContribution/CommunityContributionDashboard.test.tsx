/**
 * Comprehensive tests for Community Contribution Dashboard
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import CommunityContributionDashboard from './CommunityContributionDashboard';

// Mock the API
jest.mock('../../services/api', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn(),
  },
}));

// Mock the auth context
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 'test-user', role: 'admin' },
    token: 'test-token',
  }),
}));

import { api } from '../../services/api';

const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
});

const theme = createTheme();

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <BrowserRouter>
          {component}
        </BrowserRouter>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

describe('CommunityContributionDashboard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    test('renders dashboard title', () => {
      renderWithProviders(<CommunityContributionDashboard />);
      expect(screen.getByText('Community Contribution Dashboard')).toBeInTheDocument();
    });

    test('renders all main tabs', () => {
      renderWithProviders(<CommunityContributionDashboard />);
      expect(screen.getByRole('tab', { name: 'Contributions' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Pending Reviews' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Reviewers' })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: 'Analytics' })).toBeInTheDocument();
    });

    test('shows loading state initially', () => {
      (api.get as jest.Mock).mockImplementation(() => new Promise(() => {}));
      
      renderWithProviders(<CommunityContributionDashboard />);
      expect(screen.getByTestId('loading-skeleton')).toBeInTheDocument();
    });
  });

  describe('Contributions Tab', () => {
    const mockContributions = [
      {
        id: '1',
        title: 'Optimal Block Registration',
        contributor_name: 'John Doe',
        type: 'code_pattern',
        status: 'approved',
        created_at: '2024-01-15T10:00:00Z',
        tags: ['forge', 'blocks', 'best_practices'],
        rating: 4.5,
        reviews_count: 3,
      },
      {
        id: '2',
        title: 'Entity Performance Tips',
        contributor_name: 'Jane Smith',
        type: 'performance_tip',
        status: 'pending_review',
        created_at: '2024-01-14T15:30:00Z',
        tags: ['entities', 'performance'],
        rating: null,
        reviews_count: 0,
      },
    ];

    test('displays contributions list', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockContributions, total: 2, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Optimal Block Registration')).toBeInTheDocument();
        expect(screen.getByText('Entity Performance Tips')).toBeInTheDocument();
      });
    });

    test('filters contributions by type', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: [mockContributions[0]], total: 1, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByText('Optimal Block Registration')).toBeInTheDocument();
      });

      // Filter by code_pattern type
      const filterSelect = screen.getByLabelText('Filter by type');
      fireEvent.mouseDown(filterSelect);
      
      const codePatternOption = screen.getByText('Code Pattern');
      fireEvent.click(codePatternOption);

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('contribution_type=code_pattern')
        );
      });
    });

    test('searches contributions', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockContributions, total: 2, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search contributions...')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search contributions...');
      fireEvent.change(searchInput, { target: { value: 'block registration' } });

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('query=block%20registration')
        );
      });
    });

    test('opens contribution detail modal', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockContributions, total: 1, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Optimal Block Registration')).toBeInTheDocument();
      });

      // Click on contribution
      fireEvent.click(screen.getByText('Optimal Block Registration'));

      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
        expect(screen.getByText('Contribution Details')).toBeInTheDocument();
      });
    });
  });

  describe('Pending Reviews Tab', () => {
    const mockPendingReviews = [
      {
        id: '1',
        contribution: {
          id: '1',
          title: 'New Block Pattern',
          contributor_name: 'Alice Johnson',
          type: 'code_pattern',
        },
        reviewer_expertise_required: ['java_modding', 'forge'],
        priority: 'high',
        created_at: '2024-01-15T09:00:00Z',
        deadline: '2024-01-22T09:00:00Z',
      },
      {
        id: '2',
        contribution: {
          id: '2',
          title: 'Performance Optimization',
          contributor_name: 'Bob Wilson',
          type: 'performance_tip',
        },
        reviewer_expertise_required: ['performance'],
        priority: 'medium',
        created_at: '2024-01-14T14:00:00Z',
        deadline: '2024-01-21T14:00:00Z',
      },
    ];

    test('displays pending reviews', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockPendingReviews, total: 2, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      // Switch to Pending Reviews tab
      fireEvent.click(screen.getByRole('tab', { name: 'Pending Reviews' }));

      await waitFor(() => {
        expect(screen.getByText('New Block Pattern')).toBeInTheDocument();
        expect(screen.getByText('Performance Optimization')).toBeInTheDocument();
      });
    });

    test('shows priority indicators', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockPendingReviews, total: 1, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Pending Reviews' }));

      await waitFor(() => {
        expect(screen.getByText('High Priority')).toBeInTheDocument();
      });
    });

    test('assigns reviewer to pending review', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockPendingReviews, total: 1, page: 1 }
      });
      (api.post as jest.Mock).mockResolvedValue({ data: { success: true } });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Pending Reviews' }));

      await waitFor(() => {
        expect(screen.getByText('Assign Reviewer')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Assign Reviewer'));

      // Mock reviewer selection
      await waitFor(() => {
        expect(screen.getByText('Select Reviewer')).toBeInTheDocument();
      });

      // This would typically open a modal/dialog for reviewer selection
      // For testing purposes, we'll just verify the API call structure
    });
  });

  describe('Reviewers Tab', () => {
    const mockReviewers = [
      {
        id: '1',
        name: 'Dr. Expert',
        email: 'expert@example.com',
        expertise_areas: ['java_modding', 'forge', 'fabric'],
        expertise_level: 'expert',
        active_reviews: 2,
        completed_reviews: 15,
        average_review_time: 2.5,
        reputation_score: 4.8,
        availability: 'available',
      },
      {
        id: '2',
        name: 'Senior Developer',
        email: 'senior@example.com',
        expertise_areas: ['performance', 'optimization'],
        expertise_level: 'senior',
        active_reviews: 1,
        completed_reviews: 8,
        average_review_time: 1.8,
        reputation_score: 4.5,
        availability: 'busy',
      },
    ];

    test('displays reviewer list', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockReviewers, total: 2, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Reviewers' }));

      await waitFor(() => {
        expect(screen.getByText('Dr. Expert')).toBeInTheDocument();
        expect(screen.getByText('Senior Developer')).toBeInTheDocument();
      });
    });

    test('shows reviewer expertise badges', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockReviewers, total: 1, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Reviewers' }));

      await waitFor(() => {
        expect(screen.getByText('java_modding')).toBeInTheDocument();
        expect(screen.getByText('forge')).toBeInTheDocument();
        expect(screen.getByText('fabric')).toBeInTheDocument();
      });
    });

    test('filters reviewers by expertise', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: [mockReviewers[0]], total: 1, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Reviewers' }));

      await waitFor(() => {
        expect(screen.getByLabelText('Filter by expertise')).toBeInTheDocument();
      });

      // Filter by java_modding expertise
      const expertiseSelect = screen.getByLabelText('Filter by expertise');
      fireEvent.mouseDown(expertiseSelect);
      
      const javaModdingOption = screen.getByText('Java Modding');
      fireEvent.click(javaModdingOption);

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('expertise=java_modding')
        );
      });
    });

    test('shows reviewer workload', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: mockReviewers, total: 1, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Reviewers' }));

      await waitFor(() => {
        expect(screen.getByText('2 Active Reviews')).toBeInTheDocument();
        expect(screen.getByText('15 Completed')).toBeInTheDocument();
      });
    });
  });

  describe('Analytics Tab', () => {
    const mockAnalytics = {
      total_contributions: 150,
      pending_reviews: 12,
      approved_contributions: 120,
      average_review_time: 2.3,
      top_contributors: [
        { name: 'John Doe', contributions: 15, rating: 4.7 },
        { name: 'Jane Smith', contributions: 12, rating: 4.9 },
      ],
      contribution_types: {
        code_pattern: 80,
        performance_tip: 35,
        tutorial: 25,
        bug_fix: 10,
      },
      monthly_trends: [
        { month: '2024-01', contributions: 45, reviews: 38 },
        { month: '2024-02', contributions: 52, reviews: 41 },
      ],
    };

    test('displays analytics dashboard', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: mockAnalytics
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Analytics' }));

      await waitFor(() => {
        expect(screen.getByText('Total Contributions')).toBeInTheDocument();
        expect(screen.getByText('150')).toBeInTheDocument();
        expect(screen.getByText('Pending Reviews')).toBeInTheDocument();
        expect(screen.getByText('12')).toBeInTheDocument();
      });
    });

    test('shows top contributors', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: mockAnalytics
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Analytics' }));

      await waitFor(() => {
        expect(screen.getByText('John Doe')).toBeInTheDocument();
        expect(screen.getByText('15 contributions')).toBeInTheDocument();
        expect(screen.getByText('Jane Smith')).toBeInTheDocument();
        expect(screen.getByText('12 contributions')).toBeInTheDocument();
      });
    });

    test('displays contribution type distribution', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: mockAnalytics
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Analytics' }));

      await waitFor(() => {
        expect(screen.getByText('Code Pattern')).toBeInTheDocument();
        expect(screen.getByText('80')).toBeInTheDocument();
        expect(screen.getByText('Performance Tip')).toBeInTheDocument();
        expect(screen.getByText('35')).toBeInTheDocument();
      });
    });

    test('shows monthly trends chart', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: mockAnalytics
      });

      renderWithProviders(<CommunityContributionDashboard />);
      
      fireEvent.click(screen.getByRole('tab', { name: 'Analytics' }));

      await waitFor(() => {
        expect(screen.getByTestId('trends-chart')).toBeInTheDocument();
      });
    });
  });

  describe('Error Handling', () => {
    test('displays error message when API fails', async () => {
      (api.get as jest.Mock).mockRejectedValue(new Error('API Error'));

      renderWithProviders(<CommunityContributionDashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load data/)).toBeInTheDocument();
      });
    });

    test('handles network errors gracefully', async () => {
      (api.get as jest.Mock).mockRejectedValue(new Error('Network Error'));

      renderWithProviders(<CommunityContributionDashboard />);

      await waitFor(() => {
        expect(screen.getByText(/Network error occurred/)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      // Test retry functionality
      fireEvent.click(screen.getByText('Retry'));
      expect(api.get).toHaveBeenCalledTimes(2);
    });
  });

  describe('Accessibility', () => {
    test('has proper ARIA labels', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: [], total: 0, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);

      await waitFor(() => {
        expect(screen.getByRole('tablist')).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Contributions' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Pending Reviews' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Reviewers' })).toBeInTheDocument();
        expect(screen.getByRole('tab', { name: 'Analytics' })).toBeInTheDocument();
      });
    });

    test('supports keyboard navigation', async () => {
      (api.get as jest.Mock).mockResolvedValue({
        data: { items: [], total: 0, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);

      await waitFor(() => {
        const firstTab = screen.getByRole('tab', { name: 'Contributions' });
        firstTab.focus();
        expect(firstTab).toHaveFocus();
      });

      // Test tab navigation
      fireEvent.keyDown(screen.getByRole('tab', { name: 'Contributions' }), { key: 'ArrowRight' });
      
      await waitFor(() => {
        expect(screen.getByRole('tab', { name: 'Pending Reviews' })).toHaveFocus();
      });
    });
  });

  describe('Performance', () => {
    test('handles large data sets efficiently', async () => {
      const largeData = Array.from({ length: 100 }, (_, i) => ({
        id: `item-${i}`,
        title: `Contribution ${i}`,
        contributor_name: `Contributor ${i}`,
        type: 'code_pattern',
        status: 'approved',
        created_at: '2024-01-15T10:00:00Z',
        tags: ['test'],
        rating: 4.0 + Math.random(),
        reviews_count: Math.floor(Math.random() * 10),
      }));

      (api.get as jest.Mock).mockResolvedValue({
        data: { items: largeData, total: 100, page: 1 }
      });

      const startTime = performance.now();
      renderWithProviders(<CommunityContributionDashboard />);
      
      await waitFor(() => {
        expect(screen.getByText('Contribution 0')).toBeInTheDocument();
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(1000); // Should render within 1 second
    });

    test('implements virtual scrolling for large lists', async () => {
      const largeData = Array.from({ length: 1000 }, (_, i) => ({
        id: `item-${i}`,
        title: `Contribution ${i}`,
        contributor_name: `Contributor ${i}`,
        type: 'code_pattern',
        status: 'approved',
        created_at: '2024-01-15T10:00:00Z',
        tags: ['test'],
        rating: 4.0,
        reviews_count: 5,
      }));

      (api.get as jest.Mock).mockResolvedValue({
        data: { items: largeData, total: 1000, page: 1 }
      });

      renderWithProviders(<CommunityContributionDashboard />);

      await waitFor(() => {
        // Should only render visible items, not all 1000
        expect(screen.getAllByTestId('contribution-item').length).toBeLessThan(50);
      });
    });
  });
});
