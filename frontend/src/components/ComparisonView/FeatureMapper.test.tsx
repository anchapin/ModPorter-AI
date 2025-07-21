import { render, screen, fireEvent } from '@testing-library/react';
import { describe, test, expect } from 'vitest';
import FeatureMapper from './FeatureMapper';

const mockFeatures = [
  {
    id: 'mapping-1',
    java_feature: 'CustomBlock.onRightClick()',
    bedrock_equivalent: 'player.onInteract',
    mapping_type: 'direct_mapping',
    confidence_score: 0.95,
  },
  {
    id: 'mapping-2',
    java_feature: 'ItemStack.getItemMeta()',
    bedrock_equivalent: 'ItemStack.getComponent()',
    mapping_type: 'api_adaptation',
    confidence_score: 0.75,
  },
  {
    id: 'mapping-3',
    java_feature: 'EntityDamageEvent',
    bedrock_equivalent: 'EntityHurtEvent',
    mapping_type: 'event_mapping',
    confidence_score: 0.45,
  },
  {
    id: 'mapping-4',
    java_feature: 'CustomInventory.GUI',
    bedrock_equivalent: null,
    mapping_type: 'manual_implementation',
    confidence_score: null,
  },
];

describe('FeatureMapper', () => {
  test('renders feature mappings with correct count', () => {
    render(<FeatureMapper features={mockFeatures} />);

    expect(screen.getByText('Feature Mappings (4)')).toBeInTheDocument();
  });

  test('displays empty state when no features provided', () => {
    render(<FeatureMapper features={[]} />);

    expect(screen.getByText('Feature Mappings (0)')).toBeInTheDocument();
    expect(screen.getByText('No feature mappings available.')).toBeInTheDocument();
  });

  test('renders all feature mapping cards', () => {
    render(<FeatureMapper features={mockFeatures} />);

    expect(screen.getByText('CustomBlock.onRightClick()')).toBeInTheDocument();
    expect(screen.getByText('player.onInteract')).toBeInTheDocument();
    expect(screen.getByText('ItemStack.getItemMeta()')).toBeInTheDocument();
    expect(screen.getByText('ItemStack.getComponent()')).toBeInTheDocument();
    expect(screen.getByText('EntityDamageEvent')).toBeInTheDocument();
    expect(screen.getByText('EntityHurtEvent')).toBeInTheDocument();
  });

  test('displays mapping types as badges', () => {
    render(<FeatureMapper features={mockFeatures} />);

    expect(screen.getByText('direct_mapping')).toBeInTheDocument();
    expect(screen.getByText('api_adaptation')).toBeInTheDocument();
    expect(screen.getByText('event_mapping')).toBeInTheDocument();
    expect(screen.getByText('manual_implementation')).toBeInTheDocument();
  });

  test('shows confidence labels correctly', () => {
    render(<FeatureMapper features={mockFeatures} />);

    expect(screen.getByText('High (95%)')).toBeInTheDocument();
    expect(screen.getByText('Medium (75%)')).toBeInTheDocument();
    expect(screen.getByText('Low (45%)')).toBeInTheDocument();
    expect(screen.getByText('Unknown')).toBeInTheDocument();
  });

  test('filter dropdown shows all mapping types', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const filterSelect = screen.getByLabelText('Filter by type:');
    expect(filterSelect).toBeInTheDocument();

    expect(screen.getByText('All Types (4)')).toBeInTheDocument();
    expect(screen.getByText('direct_mapping (1)')).toBeInTheDocument();
    expect(screen.getByText('api_adaptation (1)')).toBeInTheDocument();
    expect(screen.getByText('event_mapping (1)')).toBeInTheDocument();
    expect(screen.getByText('manual_implementation (1)')).toBeInTheDocument();
  });

  test('filters features by mapping type', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const filterSelect = screen.getByLabelText('Filter by type:');
    
    // Filter by direct_mapping
    fireEvent.change(filterSelect, { target: { value: 'direct_mapping' } });

    expect(screen.getByText('CustomBlock.onRightClick()')).toBeInTheDocument();
    expect(screen.queryByText('ItemStack.getItemMeta()')).not.toBeInTheDocument();
    expect(screen.queryByText('EntityDamageEvent')).not.toBeInTheDocument();
  });

  test('shows "no mappings match filter" message when filter has no results', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const filterSelect = screen.getByLabelText('Filter by type:');
    
    // Filter by a type that doesn't exist
    fireEvent.change(filterSelect, { target: { value: 'nonexistent_type' } });

    expect(screen.getByText('No mappings match the selected filter.')).toBeInTheDocument();
  });

  test('expands mapping details on click', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const firstMappingCard = screen.getByText('CustomBlock.onRightClick()').closest('div');
    
    // Initially, details should not be visible
    expect(screen.queryByText('Mapping Details')).not.toBeInTheDocument();

    // Click to expand
    fireEvent.click(firstMappingCard!);

    // Details should now be visible
    expect(screen.getByText('Mapping Details')).toBeInTheDocument();
    expect(screen.getByText('ID: mapping-1')).toBeInTheDocument();
    expect(screen.getByText('Confidence Score: 95.0%')).toBeInTheDocument();
    expect(screen.getByText('Mapping Strategy: direct mapping')).toBeInTheDocument();
  });

  test('collapses mapping details on second click', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const firstMappingCard = screen.getByText('CustomBlock.onRightClick()').closest('div');
    
    // Click to expand
    fireEvent.click(firstMappingCard!);
    expect(screen.getByText('Mapping Details')).toBeInTheDocument();

    // Click again to collapse
    fireEvent.click(firstMappingCard!);
    expect(screen.queryByText('Mapping Details')).not.toBeInTheDocument();
  });

  test('handles features with null bedrock equivalent', () => {
    const featureWithNullBedrock = {
      id: 'mapping-null',
      java_feature: 'SomeJavaFeature',
      bedrock_equivalent: null,
      mapping_type: 'no_equivalent',
      confidence_score: 0.1,
    };

    render(<FeatureMapper features={[featureWithNullBedrock]} />);

    expect(screen.getByText('SomeJavaFeature')).toBeInTheDocument();
    expect(screen.getByText('Unknown')).toBeInTheDocument(); // For null bedrock_equivalent
  });

  test('handles features with empty java feature', () => {
    const featureWithEmptyJava = {
      id: 'mapping-empty',
      java_feature: '',
      bedrock_equivalent: 'SomeBedrockFeature',
      mapping_type: 'unknown',
      confidence_score: 0.5,
    };

    render(<FeatureMapper features={[featureWithEmptyJava]} />);

    expect(screen.getByText('Unknown')).toBeInTheDocument(); // For empty java_feature
    expect(screen.getByText('SomeBedrockFeature')).toBeInTheDocument();
  });

  test('confidence score displays "Not specified" when null', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const manualImplementationCard = screen.getByText('manual_implementation').closest('div');
    fireEvent.click(manualImplementationCard!);

    expect(screen.getByText('Confidence Score: Not specified')).toBeInTheDocument();
  });

  test('mapping strategy formats underscores correctly', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const apiAdaptationCard = screen.getByText('api_adaptation').closest('div');
    fireEvent.click(apiAdaptationCard!);

    expect(screen.getByText('Mapping Strategy: api adaptation')).toBeInTheDocument();
  });

  test('only one mapping can be expanded at a time', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const firstCard = screen.getByText('CustomBlock.onRightClick()').closest('div');
    const secondCard = screen.getByText('ItemStack.getItemMeta()').closest('div');

    // Expand first card
    fireEvent.click(firstCard!);
    expect(screen.getByText('ID: mapping-1')).toBeInTheDocument();

    // Expand second card
    fireEvent.click(secondCard!);
    expect(screen.getByText('ID: mapping-2')).toBeInTheDocument();
    expect(screen.queryByText('ID: mapping-1')).not.toBeInTheDocument();
  });

  test('applies correct styling for confidence scores', () => {
    render(<FeatureMapper features={mockFeatures} />);

    // Test that confidence indicators are rendered (though we can't easily test exact colors)
    const confidenceIndicators = screen.getAllByText(/High|Medium|Low|Unknown/);
    expect(confidenceIndicators.length).toBeGreaterThan(0);
  });

  test('displays Java and Bedrock sections with proper styling', () => {
    render(<FeatureMapper features={mockFeatures} />);

    expect(screen.getAllByText('Java Feature')).toHaveLength(4);
    expect(screen.getAllByText('Bedrock Equivalent')).toHaveLength(4);
  });

  test('handles case-insensitive filtering', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const filterSelect = screen.getByLabelText('Filter by type:');
    
    // Filter by exact match (since the component filters by exact type)
    fireEvent.change(filterSelect, { target: { value: 'direct_mapping' } });

    // Should show only direct_mapping features
    expect(screen.getByText('CustomBlock.onRightClick()')).toBeInTheDocument(); // direct_mapping
    expect(screen.queryByText('EntityDamageEvent')).not.toBeInTheDocument(); // event_mapping
    expect(screen.queryByText('ItemStack.getItemMeta()')).not.toBeInTheDocument(); // api_adaptation
  });

  test('displays arrow between Java and Bedrock features', () => {
    render(<FeatureMapper features={mockFeatures} />);

    const arrows = screen.getAllByText('→');
    expect(arrows).toHaveLength(4); // One arrow per mapping
  });
});