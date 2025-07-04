/**
 * Storybook stories for ConversionUpload component
 * Visual development and testing for PRD Feature 1
 */

import type { Meta, StoryObj } from '@storybook/react';
import { ConversionUpload } from './ConversionUpload';

const meta: Meta<typeof ConversionUpload> = {
  title: 'Features/ConversionUpload',
  component: ConversionUpload,
  parameters: {
    layout: 'centered',
    docs: {
      description: {
        component: `
## PRD Feature 1: One-Click Modpack Ingestion

The ConversionUpload component implements the core user interface for uploading Java mods and modpacks for conversion to Bedrock add-ons.

### Key Features:
- Drag & drop file upload for .jar and .zip files
- URL input for CurseForge and Modrinth repositories
- Smart assumptions configuration
- Visual feedback and validation
- Progress indication during conversion

### User Stories:
- "As a player, I want to simply drag and drop my CurseForge modpack zip file into the tool and click 'Convert' to start the process."
- "As a user, I want the tool to intelligently analyze the mods and generate all necessary files without me needing to know how it works."
        `,
      },
    },
  },
  tags: ['autodocs'],
  argTypes: {
    onConversionStart: {
      description: 'Callback fired when conversion begins',
      action: 'onConversionStart',
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

// Default story
export const Default: Story = {
  args: {
    onConversionStart: () => console.log('conversion-started'),
  },
  parameters: {
    docs: {
      description: {
        story: 'Default state of the conversion upload component with all features visible.',
      },
    },
  },
};

// Mobile viewport
export const Mobile: Story = {
  args: {
    onConversionStart: () => console.log('conversion-started'),
  },
  parameters: {
    viewport: {
      defaultViewport: 'mobile',
    },
    docs: {
      description: {
        story: 'Component optimized for mobile devices.',
      },
    },
  },
};

// Dark theme
export const DarkTheme: Story = {
  args: {
    onConversionStart: () => console.log('conversion-started'),
  },
  parameters: {
    backgrounds: { default: 'dark' },
    docs: {
      description: {
        story: 'Component in dark theme for better visual accessibility.',
      },
    },
  },
};