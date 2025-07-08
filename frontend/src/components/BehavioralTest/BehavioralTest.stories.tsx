import type { Meta, StoryObj } from '@storybook/react-vite';
import { BehavioralTest } from './BehavioralTest';

const meta: Meta<typeof BehavioralTest> = {
  title: 'Testing/BehavioralTest',
  component: BehavioralTest,
  parameters: {
    layout: 'padded',
    docs: {
      description: {
        component: 'Behavioral testing component for validating mod conversion behavior preservation.'
      }
    }
  },
  tags: ['autodocs'],
  argTypes: {
    conversionId: {
      description: 'ID of the conversion job to test',
      control: 'text'
    },
    onTestComplete: {
      description: 'Callback fired when behavioral test completes',
      action: 'test-completed'
    }
  }
};

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {
  args: {
    conversionId: 'test-conversion-123',
  },
  parameters: {
    docs: {
      description: {
        story: 'Default behavioral test component ready to start testing.'
      }
    }
  }
};

export const WithCustomConversionId: Story = {
  args: {
    conversionId: 'custom-mod-conversion-456',
  },
  parameters: {
    docs: {
      description: {
        story: 'Behavioral test component with a custom conversion ID.'
      }
    }
  }
};

// Mock component for testing different states
export const TestInProgress: Story = {
  args: {
    conversionId: 'progress-test-789',
  },
  parameters: {
    docs: {
      description: {
        story: 'Behavioral test component showing progress state (requires manual interaction to see).'
      }
    }
  }
};

export const WithCallback: Story = {
  args: {
    conversionId: 'callback-test-101',
    onTestComplete: (results) => {
      console.log('Test completed with results:', results);
    }
  },
  parameters: {
    docs: {
      description: {
        story: 'Behavioral test component with completion callback (check console for results).'
      }
    }
  }
};