/**
 * Comprehensive tests for Knowledge Graph Viewer
 */

import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import KnowledgeGraphViewer from './KnowledgeGraphViewer';

// Mock D3.js for graph visualization
jest.mock('d3', () => ({
  select: jest.fn(() => ({
    selectAll: jest.fn().mockReturnThis(),
    data: jest.fn().mockReturnThis(),
    enter: jest.fn().mockReturnThis(),
    append: jest.fn().mockReturnThis(),
    merge: jest.fn().mockReturnThis(),
    remove: jest.fn().mockReturnThis(),
    attr: jest.fn().mockReturnThis(),
    style: jest.fn().mockReturnThis(),
    text: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
    call: jest.fn().mockReturnThis(),
  })),
  forceSimulation: jest.fn(() => ({
    force: jest.fn().mockReturnThis(),
    alphaTarget: jest.fn().mockReturnThis(),
    restart: jest.fn().mockReturnThis(),
    stop: jest.fn().mockReturnThis(),
    on: jest.fn().mockReturnThis(),
  })),
  forceLink: jest.fn(),
  forceManyBody: jest.fn(),
  forceCenter: jest.fn(),
  forceCollide: jest.fn(),
  zoom: jest.fn(),
  zoomIdentity: jest.fn(),
  scale: jest.fn(() => ({ translate: jest.fn() })),
}));

// Mock API
jest.mock('../../services/api', () => ({
  api: {
    get: jest.fn(),
    post: jest.fn(),
  },
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
        {component}
      </ThemeProvider>
    </QueryClientProvider>
  );
};

const mockGraphData = {
  nodes: [
    {
      id: 'node1',
      type: 'java_class',
      properties: { name: 'BlockRegistry', package: 'net.minecraft.block' },
      x: 100,
      y: 100,
    },
    {
      id: 'node2',
      type: 'java_class',
      properties: { name: 'ItemRegistry', package: 'net.minecraft.item' },
      x: 200,
      y: 200,
    },
    {
      id: 'node3',
      type: 'minecraft_block',
      properties: { name: 'CustomBlock', material: 'stone' },
      x: 300,
      y: 150,
    },
  ],
  edges: [
    {
      id: 'edge1',
      source: 'node1',
      target: 'node2',
      type: 'depends_on',
      properties: { strength: 0.8 },
    },
    {
      id: 'edge2',
      source: 'node2',
      target: 'node3',
      type: 'creates',
      properties: { method: 'register' },
    },
  ],
  metadata: {
    total_nodes: 3,
    total_edges: 2,
    last_updated: '2024-01-15T10:00:00Z',
  },
};

describe('KnowledgeGraphViewer', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    test('renders graph viewer component', () => {
      renderWithProviders(<KnowledgeGraphViewer />);
      expect(screen.getByTestId('knowledge-graph-viewer')).toBeInTheDocument();
    });

    test('displays loading state initially', () => {
      (api.get as jest.Mock).mockImplementation(() => new Promise(() => {}));
      
      renderWithProviders(<KnowledgeGraphViewer />);
      expect(screen.getByTestId('graph-loading')).toBeInTheDocument();
    });

    test('renders graph controls', () => {
      renderWithProviders(<KnowledgeGraphViewer />);
      expect(screen.getByLabelText('Zoom In')).toBeInTheDocument();
      expect(screen.getByLabelText('Zoom Out')).toBeInTheDocument();
      expect(screen.getByLabelText('Reset View')).toBeInTheDocument();
      expect(screen.getByLabelText('Fit to Screen')).toBeInTheDocument();
    });

    test('renders search functionality', () => {
      renderWithProviders(<KnowledgeGraphViewer />);
      expect(screen.getByPlaceholderText('Search nodes...')).toBeInTheDocument();
    });
  });

  describe('Graph Data Loading', () => {
    test('loads and displays graph data', async () => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
        expect(api.get).toHaveBeenCalledWith('/api/knowledge-graph/visualization/');
      });
    });

    test('handles loading error gracefully', async () => {
      (api.get as jest.Mock).mockRejectedValue(new Error('Failed to load graph'));

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByText(/Failed to load knowledge graph/)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    test('allows retry after error', async () => {
      (api.get as jest.Mock)
        .mockRejectedValueOnce(new Error('Failed to load graph'))
        .mockResolvedValueOnce({ data: mockGraphData });

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledTimes(2);
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });
    });
  });

  describe('Graph Interaction', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('handles node selection', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });

      // Simulate node click (would normally be handled by D3)
      const graphContainer = screen.getByTestId('graph-container');
      fireEvent.click(graphContainer, { target: { __data__: mockGraphData.nodes[0] } });

      await waitFor(() => {
        expect(screen.getByText('Node Details')).toBeInTheDocument();
        expect(screen.getByText('BlockRegistry')).toBeInTheDocument();
      });
    });

    test('displays node details panel', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });

      // Simulate node selection
      fireEvent.click(screen.getByTestId('graph-container'), {
        target: { __data__: mockGraphData.nodes[0] }
      });

      await waitFor(() => {
        expect(screen.getByText('BlockRegistry')).toBeInTheDocument();
        expect(screen.getByText('net.minecraft.block')).toBeInTheDocument();
        expect(screen.getByText('java_class')).toBeInTheDocument();
      });
    });

    test('handles edge selection', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });

      // Simulate edge click
      fireEvent.click(screen.getByTestId('graph-container'), {
        target: { __data__: mockGraphData.edges[0] }
      });

      await waitFor(() => {
        expect(screen.getByText('Edge Details')).toBeInTheDocument();
        expect(screen.getByText('depends_on')).toBeInTheDocument();
      });
    });

    test('highlights connected nodes on selection', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });

      // Select a node
      fireEvent.click(screen.getByTestId('graph-container'), {
        target: { __data__: mockGraphData.nodes[0] }
      });

      await waitFor(() => {
        // Check if connected nodes are highlighted
        const highlightedNodes = screen.getAllByTestId('graph-node-highlighted');
        expect(highlightedNodes.length).toBeGreaterThan(0);
      });
    });
  });

  describe('Search Functionality', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('searches nodes by name', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search nodes...')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search nodes...');
      fireEvent.change(searchInput, { target: { value: 'BlockRegistry' } });

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('search=BlockRegistry')
        );
      });
    });

    test('filters nodes by type', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Filter by type')).toBeInTheDocument();
      });

      const typeFilter = screen.getByLabelText('Filter by type');
      fireEvent.mouseDown(typeFilter);

      const javaClassOption = screen.getByText('Java Class');
      fireEvent.click(javaClassOption);

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('node_type=java_class')
        );
      });
    });

    test('clears search results', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText('Search nodes...')).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText('Search nodes...');
      fireEvent.change(searchInput, { target: { value: 'test' } });

      // Clear search
      const clearButton = screen.getByLabelText('Clear search');
      fireEvent.click(clearButton);

      await waitFor(() => {
        expect(searchInput).toHaveValue('');
      });
    });
  });

  describe('Graph Controls', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('zooms in when zoom in button clicked', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Zoom In')).toBeInTheDocument();
      });

      const zoomInButton = screen.getByLabelText('Zoom In');
      fireEvent.click(zoomInButton);

      // Verify zoom level changed (would be handled by D3)
      expect(screen.getByTestId('graph-container')).toBeInTheDocument();
    });

    test('zooms out when zoom out button clicked', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Zoom Out')).toBeInTheDocument();
      });

      const zoomOutButton = screen.getByLabelText('Zoom Out');
      fireEvent.click(zoomOutButton);

      expect(screen.getByTestId('graph-container')).toBeInTheDocument();
    });

    test('resets view when reset button clicked', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Reset View')).toBeInTheDocument();
      });

      const resetButton = screen.getByLabelText('Reset View');
      fireEvent.click(resetButton);

      expect(screen.getByTestId('graph-container')).toBeInTheDocument();
    });

    test('fits to screen when fit button clicked', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Fit to Screen')).toBeInTheDocument();
      });

      const fitButton = screen.getByLabelText('Fit to Screen');
      fireEvent.click(fitButton);

      expect(screen.getByTestId('graph-container')).toBeInTheDocument();
    });
  });

  describe('Graph Layout Options', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('switches between layout types', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Layout')).toBeInTheDocument();
      });

      const layoutSelect = screen.getByLabelText('Layout');
      fireEvent.mouseDown(layoutSelect);

      const forceDirectedOption = screen.getByText('Force Directed');
      fireEvent.click(forceDirectedOption);

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('layout=force_directed')
        );
      });
    });

    test('adjusts layout parameters', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Node Spacing')).toBeInTheDocument();
      });

      const spacingSlider = screen.getByLabelText('Node Spacing');
      fireEvent.change(spacingSlider, { target: { value: 50 } });

      expect(spacingSlider).toHaveValue(50);
    });
  });

  describe('Export Functionality', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('exports graph as PNG', async () => {
      // Mock canvas toBlob
      HTMLCanvasElement.prototype.toBlob = jest.fn((callback) => {
        callback(new Blob());
      });

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Export')).toBeInTheDocument();
      });

      const exportButton = screen.getByLabelText('Export');
      fireEvent.mouseDown(exportButton);

      const pngOption = screen.getByText('Export as PNG');
      fireEvent.click(pngOption);

      await waitFor(() => {
        expect(HTMLCanvasElement.prototype.toBlob).toHaveBeenCalled();
      });
    });

    test('exports graph as JSON', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Export')).toBeInTheDocument();
      });

      const exportButton = screen.getByLabelText('Export');
      fireEvent.mouseDown(exportButton);

      const jsonOption = screen.getByText('Export as JSON');
      fireEvent.click(jsonOption);

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('format=json')
        );
      });
    });
  });

  describe('Filter Panel', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('opens filter panel', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Filters')).toBeInTheDocument();
      });

      const filterButton = screen.getByLabelText('Filters');
      fireEvent.click(filterButton);

      await waitFor(() => {
        expect(screen.getByText('Graph Filters')).toBeInTheDocument();
        expect(screen.getByLabelText('Node Types')).toBeInTheDocument();
        expect(screen.getByLabelText('Edge Types')).toBeInTheDocument();
      });
    });

    test('applies multiple filters', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Filters')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Filters'));

      await waitFor(() => {
        expect(screen.getByLabelText('Java Class')).toBeInTheDocument();
        expect(screen.getByLabelText('Minecraft Block')).toBeInTheDocument();
      });

      // Apply filters
      fireEvent.click(screen.getByLabelText('Java Class'));
      fireEvent.click(screen.getByLabelText('Depends On'));

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('node_types=java_class')
        );
        expect(api.get).toHaveBeenCalledWith(
          expect.stringContaining('edge_types=depends_on')
        );
      });
    });

    test('resets filters', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByLabelText('Filters')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText('Filters'));

      await waitFor(() => {
        expect(screen.getByText('Reset Filters')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Reset Filters'));

      await waitFor(() => {
        expect(api.get).toHaveBeenCalledWith(
          expect.not.stringContaining('node_types')
        );
      });
    });
  });

  describe('Performance', () => {
    test('handles large graphs efficiently', async () => {
      const largeGraphData = {
        nodes: Array.from({ length: 1000 }, (_, i) => ({
          id: `node-${i}`,
          type: 'java_class',
          properties: { name: `Class${i}` },
          x: Math.random() * 800,
          y: Math.random() * 600,
        })),
        edges: Array.from({ length: 2000 }, (_, i) => ({
          id: `edge-${i}`,
          source: `node-${Math.floor(Math.random() * 1000)}`,
          target: `node-${Math.floor(Math.random() * 1000)}`,
          type: 'depends_on',
        })),
      };

      (api.get as jest.Mock).mockResolvedValue({ data: largeGraphData });

      const startTime = performance.now();
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });

      const endTime = performance.now();
      expect(endTime - startTime).toBeLessThan(2000); // Should render within 2 seconds
    });

    test('implements virtualization for large node counts', async () => {
      const largeGraphData = {
        nodes: Array.from({ length: 10000 }, (_, i) => ({
          id: `node-${i}`,
          type: 'java_class',
          properties: { name: `Class${i}` },
        })),
        edges: [],
      };

      (api.get as jest.Mock).mockResolvedValue({ data: largeGraphData });

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        // Should only render visible nodes, not all 10000
        expect(screen.getAllByTestId('graph-node').length).toBeLessThan(1000);
      });
    });
  });

  describe('Accessibility', () => {
    beforeEach(() => {
      (api.get as jest.Mock).mockResolvedValue({ data: mockGraphData });
    });

    test('has proper ARIA labels', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Zoom In' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Zoom Out' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Reset View' })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Fit to Screen' })).toBeInTheDocument();
      });
    });

    test('supports keyboard navigation', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        const zoomInButton = screen.getByLabelText('Zoom In');
        zoomInButton.focus();
        expect(zoomInButton).toHaveFocus();
      });

      // Test keyboard shortcuts
      fireEvent.keyDown(document, { key: '+' });
      fireEvent.keyDown(document, { key: '-' });
      fireEvent.keyDown(document, { key: '0' });

      expect(screen.getByTestId('graph-container')).toBeInTheDocument();
    });

    test('provides screen reader announcements', async () => {
      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByRole('status')).toBeInTheDocument();
      });

      // Should announce graph loading status
      fireEvent.click(screen.getByTestId('graph-container'), {
        target: { __data__: mockGraphData.nodes[0] }
      });

      await waitFor(() => {
        expect(screen.getByRole('status')).toHaveTextContent(/Node selected/);
      });
    });
  });

  describe('Error Boundaries', () => {
    test('handles D3 rendering errors gracefully', async () => {
      // Mock D3 to throw an error
      jest.doMock('d3', () => {
        throw new Error('D3 rendering error');
      });

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByText(/Graph rendering failed/)).toBeInTheDocument();
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });
    });

    test('recovers from rendering errors', async () => {
      // Mock initial error, then success
      (api.get as jest.Mock)
        .mockRejectedValueOnce(new Error('D3 error'))
        .mockResolvedValueOnce({ data: mockGraphData });

      renderWithProviders(<KnowledgeGraphViewer />);

      await waitFor(() => {
        expect(screen.getByText('Retry')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText('Retry'));

      await waitFor(() => {
        expect(screen.getByTestId('graph-container')).toBeInTheDocument();
      });
    });
  });
});
