/**
 * Storybook stories for ConversionReport component
 * Visual development for PRD Feature 3: Interactive Conversion Report
 */

import type { Meta, StoryObj } from '@storybook/react-vite';
import { ConversionReport } from './ConversionReport';
import type { ConversionResponse } from '../../types/api';

const meta: Meta<typeof ConversionReport> = {
  title: 'Features/ConversionReport',
  component: ConversionReport,
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: `
## PRD Feature 3: Interactive Conversion Report

Visual, comprehensive reporting of conversion results with smart assumptions transparency.

### Features:
- High-level summary for non-technical users
- Technical details for developers
- Smart assumptions applied with visual explanations
- Success/failure breakdown with visual indicators
- Download links and installation instructions
        `,
      },
    },
  },
  tags: ['autodocs'],
};

export default meta;
type Story = StoryObj<typeof meta>;

// Mock data for stories
const successfulConversion: ConversionResponse = {
  conversionId: 'success-123',
  status: 'completed',
  overallSuccessRate: 92.5,
  convertedMods: [
    {
      name: 'Iron Chests',
      version: '1.19.2-14.4.4',
      status: 'success',
      features: [
        { name: 'Iron Chest Block', type: 'block', converted: true },
        { name: 'Golden Chest Block', type: 'block', converted: true },
        { name: 'Diamond Chest Block', type: 'block', converted: true },
      ],
      warnings: [],
    },
    {
      name: 'JEI (Just Enough Items)',
      version: '1.19.2-11.6.0.1013',
      status: 'partial',
      features: [
        { name: 'Recipe Viewer', type: 'gui', converted: false, changes: 'Converted to book interface' },
        { name: 'Item Search', type: 'gui', converted: true },
      ],
      warnings: ['Custom GUI converted to book interface'],
    },
  ],
  failedMods: [],
  smartAssumptionsApplied: [
    {
      originalFeature: 'Custom Recipe GUI',
      assumptionApplied: 'Converted to book interface',
      impact: 'medium',
      description: 'Recipe viewing interface converted to in-game book for information access',
    },
  ],
  downloadUrl: 'https://api.modporter.ai/download/success-123.mcaddon',
  detailedReport: {
    stage: 'completed',
    progress: 100,
    logs: ['Analysis completed', 'Conversion successful', 'Package created'],
    technicalDetails: {
      processingTime: 45.2,
      agentsUsed: ['java_analyzer', 'bedrock_architect', 'logic_translator'],
    },
  },
};

const partialConversion: ConversionResponse = {
  conversionId: 'partial-456',
  status: 'completed',
  overallSuccessRate: 65.0,
  convertedMods: [
    {
      name: 'Twilight Forest',
      version: '1.19.2-4.2.1518',
      status: 'partial',
      features: [
        { name: 'Twilight Forest Dimension', type: 'dimension', converted: false, changes: 'Converted to large structure in Overworld' },
        { name: 'Twilight Mobs', type: 'entity', converted: true },
        { name: 'Twilight Blocks', type: 'block', converted: true },
      ],
      warnings: ['Custom dimension converted to structure'],
    },
  ],
  failedMods: [
    {
      name: 'OptiFine',
      reason: 'Client-side rendering mod not supported in Bedrock',
      suggestions: ['Use Bedrock render settings', 'Check Marketplace for similar add-ons'],
    },
  ],
  smartAssumptionsApplied: [
    {
      originalFeature: 'Custom Dimension: Twilight Forest',
      assumptionApplied: 'Converted to large structure in Overworld',
      impact: 'high',
      description: 'Dimension recreated as explorable structure due to Bedrock API limitations',
    },
  ],
  downloadUrl: 'https://api.modporter.ai/download/partial-456.mcaddon',
  detailedReport: {
    stage: 'completed',
    progress: 100,
    logs: ['Analysis completed', 'Smart assumptions applied', 'Partial conversion completed'],
    technicalDetails: {
      processingTime: 120.8,
      agentsUsed: ['java_analyzer', 'bedrock_architect', 'logic_translator', 'asset_converter'],
    },
  },
};

const failedConversion: ConversionResponse = {
  conversionId: 'failed-789',
  status: 'failed',
  overallSuccessRate: 0,
  convertedMods: [],
  failedMods: [
    {
      name: 'Complex Tech Mod',
      reason: 'Too many incompatible features',
      suggestions: ['Manual porting required', 'Consider simpler alternatives'],
    },
  ],
  smartAssumptionsApplied: [],
  detailedReport: {
    stage: 'analysis',
    progress: 25,
    logs: ['Analysis started', 'Incompatible features detected', 'Conversion failed'],
    technicalDetails: {
      processingTime: 15.3,
      errors: ['Unsupported mod framework', 'No compatible features found'],
    },
  },
};

export const Successful: Story = {
  args: {
    conversionResult: successfulConversion,
  },
  parameters: {
    docs: {
      description: {
        story: 'Successful conversion with high success rate and minimal smart assumptions.',
      },
    },
  },
};

export const PartialSuccess: Story = {
  args: {
    conversionResult: partialConversion,
  },
  parameters: {
    docs: {
      description: {
        story: 'Partial conversion showing smart assumptions applied and some failed components.',
      },
    },
  },
};

export const Failed: Story = {
  args: {
    conversionResult: failedConversion,
  },
  parameters: {
    docs: {
      description: {
        story: 'Failed conversion with clear error messaging and suggestions.',
      },
    },
  },
};

export const Loading: Story = {
  args: {
    conversionResult: {
      ...successfulConversion,
      status: 'processing',
      overallSuccessRate: 0,
      detailedReport: {
        stage: 'analysis',
        progress: 45,
        logs: ['Analysis in progress...'],
      },
    },
  },
  parameters: {
    docs: {
      description: {
        story: 'Loading state during active conversion process.',
      },
    },
  },
};