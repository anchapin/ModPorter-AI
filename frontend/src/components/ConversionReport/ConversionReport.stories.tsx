/**
 * Storybook stories for ConversionReport component
 * Visual development for PRD Feature 3: Interactive Conversion Report
 */

import type { Meta, StoryObj } from '@storybook/react-vite';
import { ConversionReport } from './ConversionReport';
import type { InteractiveReport, ModConversionStatus, AssumptionDetail, FeatureConversionDetail, LogEntry } from '../../types/api';

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

// Mock data for stories using InteractiveReport structure
const baseMockReport: Omit<InteractiveReport, 'summary' | 'converted_mods' | 'failed_mods' | 'feature_analysis' | 'smart_assumptions_report' | 'developer_log'> = {
  job_id: 'mock-job-123',
  report_generation_date: new Date().toISOString(),
};

const successfulConversion: InteractiveReport = {
  ...baseMockReport,
  job_id: 'success-123',
  summary: {
    overall_success_rate: 92.5,
    total_features: 20,
    converted_features: 18,
    partially_converted_features: 1,
    failed_features: 1,
    assumptions_applied_count: 1,
    processing_time_seconds: 45.2,
    download_url: 'https://api.modporter.ai/download/success-123.mcaddon',
    quick_statistics: { files_processed: 150, output_size_mb: 12.5 },
  },
  converted_mods: [
    {
      name: 'Iron Chests', version: '1.19.2-14.4.4', status: 'Converted',
      warnings: [], errors: []
    },
    {
      name: 'JEI (Just Enough Items)', version: '1.19.2-11.6.0.1013', status: 'Partially Converted',
      warnings: ['Custom GUI for recipe viewing adapted to a book-based interface.'], errors: []
    },
  ],
  failed_mods: [],
  smart_assumptions_report: {
    assumptions: [
      {
        assumption_id: 'SA001', feature_affected: 'JEI Recipe GUI',
        description: 'Original JEI recipe view used a custom GUI not directly translatable.',
        reasoning: 'Bedrock Edition lacks direct support for such complex custom GUIs from Java mods. A book interface provides a standard, accessible way to view recipe information.',
        impact_level: 'Medium',
        user_explanation: 'The way you look up recipes in JEI has changed. It now uses an in-game book interface.',
        technical_notes: 'Considered using custom UI screens, but book is more robust for initial conversion.'
      } as AssumptionDetail,
    ],
  },
  feature_analysis: {
    per_feature_status: [
      { feature_name: 'Iron Chest Block', status: 'Success', compatibility_notes: 'Fully compatible.', impact_of_assumption: null },
      { feature_name: 'JEI Recipe Viewer', status: 'Partial Success', compatibility_notes: 'Adapted to book interface.', impact_of_assumption: 'Medium - UI changed but functionality preserved.' },
      { feature_name: 'Some Other Feature', status: 'Failed', compatibility_notes: 'Could not convert due to X reason.', impact_of_assumption: null },
    ] as FeatureConversionDetail[],
    compatibility_mapping_summary: 'Most core functionalities mapped. Some UI elements adapted for Bedrock.',
    visual_comparisons_overview: 'Visuals largely preserved for blocks and items. GUI changes noted.',
    impact_assessment_summary: 'Smart assumptions had low to medium impact, primarily affecting UI/UX of specific features.',
  },
  developer_log: {
    code_translation_details: [
      { timestamp: new Date().toISOString(), level: 'INFO', message: 'IronChestsModule.java translated to IronChests.js' } as LogEntry,
    ],
    api_mapping_issues: [
      { timestamp: new Date().toISOString(), level: 'WARNING', message: 'java.awt.Color not available server-side for JEI plugin, used placeholder values.' } as LogEntry,
    ],
    file_processing_log: [
      { timestamp: new Date().toISOString(), level: 'INFO', message: 'Processed 32 textures for Iron Chests.' } as LogEntry,
    ],
    performance_metrics: { total_time_seconds: 45.2, memory_peak_mb: 256, items_processed: 500 },
    error_summary: [],
  },
};

const partialConversion: InteractiveReport = {
  ...baseMockReport,
  job_id: 'partial-456',
  summary: {
    overall_success_rate: 65.0,
    total_features: 30,
    converted_features: 15,
    partially_converted_features: 5,
    failed_features: 10,
    assumptions_applied_count: 3,
    processing_time_seconds: 120.8,
    download_url: 'https://api.modporter.ai/download/partial-456.mcaddon',
    quick_statistics: { files_processed: 250, output_size_mb: 22.5, warnings: 5 },
  },
  converted_mods: [
    {
      name: 'Twilight Forest', version: '1.19.2-4.2.1518', status: 'Partially Converted',
      warnings: ['Custom dimension feature adapted to a large structure in the Overworld due to API limitations.'], errors: []
    } as ModConversionStatus,
  ],
  failed_mods: [
    {
      name: 'OptiFine', version: 'HD U H9', status: 'Failed',
      errors: ['Client-side rendering mods like OptiFine are not supported in Bedrock Edition as add-ons.'], warnings: []
    } as ModConversionStatus,
  ],
  smart_assumptions_report: {
    assumptions: [
      {
        assumption_id: 'SA002', feature_affected: 'Twilight Forest Dimension',
        description: 'The custom dimension "Twilight Forest" was converted into a large, explorable structure within the Overworld.',
        reasoning: 'Bedrock Edition does not allow add-ons to create entirely new custom dimensions in the same way Java mods can. Representing it as a structure preserves a significant amount of the content and exploration experience.',
        impact_level: 'High',
        user_explanation: 'The Twilight Forest is now a special area you can find within your main world, instead of a separate dimension.',
        technical_notes: 'Structure generation uses custom blocks and entities. Biome data approximated.'
      } as AssumptionDetail,
    ],
  },
  feature_analysis: {
    per_feature_status: [
      { feature_name: 'Twilight Portal', status: 'Failed', compatibility_notes: 'Portal mechanics for custom dimension not replicable.', impact_of_assumption: 'High' },
      { feature_name: 'Naga Boss', status: 'Success', compatibility_notes: 'Behavior and model converted.', impact_of_assumption: null },
    ] as FeatureConversionDetail[],
    compatibility_mapping_summary: 'Key content like bosses and blocks from Twilight Forest converted, but the dimension itself is integrated into Overworld.',
    visual_comparisons_overview: 'Visuals for entities and blocks maintained. Overall world experience changed due to dimension integration.',
    impact_assessment_summary: 'High impact assumption regarding dimension handling was necessary to convert core content.',
  },
  developer_log: {
    code_translation_details: [],
    api_mapping_issues: [],
    file_processing_log: [],
    performance_metrics: { total_time_seconds: 120.8, memory_peak_mb: 512 },
    error_summary: [{ error_message: "Could not resolve class 'net.minecraftforge.client.IItemRenderer'", module: 'OptifineStructureAnalyzer' }],
  },
};

const failedConversion: InteractiveReport = {
  ...baseMockReport,
  job_id: 'failed-789',
  summary: {
    overall_success_rate: 5.0, // Still might have some success if one tiny mod converted
    total_features: 50,
    converted_features: 2,
    partially_converted_features: 1,
    failed_features: 47,
    assumptions_applied_count: 0,
    processing_time_seconds: 15.3,
    download_url: null, // No download for failed
    quick_statistics: { files_processed: 30, error_count: 18 },
  },
  converted_mods: [],
  failed_mods: [
    {
      name: 'Complex Tech Mod', version: '3.5.0', status: 'Failed',
      errors: ['Core API hooks missing in Bedrock.', 'Requires rendering features not available.'], warnings: []
    } as ModConversionStatus,
     {
      name: 'Another Large Mod', version: '1.2.0', status: 'Failed',
      errors: ['Dependency on Complex Tech Mod which failed.'], warnings: []
    } as ModConversionStatus,
  ],
  smart_assumptions_report: null, // Or { assumptions: [] }
  feature_analysis: null,
  developer_log: {
    code_translation_details: [],
    api_mapping_issues: [],
    file_processing_log: [],
    performance_metrics: { total_time_seconds: 15.3 },
    error_summary: [
      { error_message: 'Unsupported mod framework detected in ComplexTechMod.jar', details: { framework_id: 'XYZCore' } },
      { error_message: 'Fatal: No compatible features found for conversion in ComplexTechMod.', details: { analyzed_features: 0 } },
    ],
  },
};


export const Successful: Story = {
  args: {
    conversionResult: successfulConversion,
    jobStatus: 'completed'
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
    jobStatus: 'completed'
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
    jobStatus: 'failed'
  },
  parameters: {
    docs: {
      description: {
        story: 'Failed conversion with clear error messaging and suggestions.',
      },
    },
  },
};

// Removed Loading story as ConversionReport now primarily handles final reports.
// Loading/processing state should be managed by a parent component.