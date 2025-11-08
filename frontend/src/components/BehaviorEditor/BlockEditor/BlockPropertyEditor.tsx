import React, { useState, useCallback, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Grid, IconButton, Tooltip } from '@mui/material';
import { 
  VisualEditor, 
  FormField, 
  ValidationRule 
} from '../VisualEditor';
import { Preview3D } from './BlockPreview';
import './BlockPropertyEditor.css';

export interface BlockProperties {
  // Basic Properties
  identifier: string;
  displayName: string;
  description: string;
  category: string;
  
  // Physical Properties
  hardness: number;
  resistance: number;
  friction: number;
  lightEmission: number;
  lightDampening: number;
  
  // Material Properties
  material: string;
  soundGroup: string;
  mapColor: string;
  faceData: string;
  
  // Behavior Properties
  solid: boolean;
  liquid: boolean;
  transparent: boolean;
  walkable: boolean;
  climbable: boolean;
  flammable: boolean;
  
  // Block States
  blockStates: Record<string, any>;
  
  // Events
  onInteract: string;
  onPlace: string;
  onDestroy: string;
  onStepOn: string;
}

export interface BlockPropertyEditorProps {
  blockData?: Partial<BlockProperties>;
  onPropertiesChange: (properties: BlockProperties) => void;
  onValidationChange?: (errors: ValidationRule[]) => void;
  readOnly?: boolean;
}

export const BlockPropertyEditor: React.FC<BlockPropertyEditorProps> = ({
  blockData = {},
  onPropertiesChange,
  onValidationChange,
  readOnly = false
}) => {
  const [currentProperties, setCurrentProperties] = useState<BlockProperties>({
    // Default values
    identifier: '',
    displayName: '',
    description: '',
    category: 'construction',
    
    hardness: 1.0,
    resistance: 6.0,
    friction: 0.6,
    lightEmission: 0,
    lightDampening: 0,
    
    material: 'stone',
    soundGroup: 'stone',
    mapColor: '#888888',
    faceData: '',
    
    solid: true,
    liquid: false,
    transparent: false,
    walkable: true,
    climbable: false,
    flammable: false,
    
    blockStates: {},
    
    onInteract: '',
    onPlace: '',
    onDestroy: '',
    onStepOn: '',
    ...blockData
  });

  // Form field definitions
  const formFields: FormField[] = [
    // Basic Properties
    {
      id: 'identifier',
      name: 'identifier',
      type: 'text',
      label: 'Block Identifier',
      value: currentProperties.identifier,
      required: true,
      validation: {
        pattern: '^[a-z0-9_:]+$',
        minLength: 3,
        custom: (value: string) => {
          if (!value.match(/^[a-z0-9_:]+$/)) {
            return 'Identifier must contain only lowercase letters, numbers, underscores, and colons';
          }
          return null;
        }
      },
      description: 'Unique identifier for the block (e.g., "minecraft:stone")',
      category: 'basic'
    },
    {
      id: 'displayName',
      name: 'displayName',
      type: 'text',
      label: 'Display Name',
      value: currentProperties.displayName,
      required: true,
      validation: { minLength: 1 },
      description: 'Name displayed in-game',
      category: 'basic'
    },
    {
      id: 'description',
      name: 'description',
      type: 'textarea',
      label: 'Description',
      value: currentProperties.description,
      validation: { maxLength: 256 },
      description: 'Optional description for the block',
      category: 'basic'
    },
    {
      id: 'category',
      name: 'category',
      type: 'select',
      label: 'Category',
      value: currentProperties.category,
      options: [
        { value: 'construction', label: 'Construction' },
        { value: 'nature', label: 'Nature' },
        { value: 'decoration', label: 'Decoration' },
        { value: 'redstone', label: 'Redstone' },
        { value: 'transportation', label: 'Transportation' },
        { value: 'misc', label: 'Miscellaneous' }
      ],
      required: true,
      category: 'basic'
    },

    // Physical Properties
    {
      id: 'hardness',
      name: 'hardness',
      type: 'range',
      label: 'Hardness',
      value: currentProperties.hardness,
      min: 0,
      max: 50,
      step: 0.1,
      validation: { min: 0, max: 50 },
      description: 'Time to break with proper tool (seconds)',
      category: 'physical'
    },
    {
      id: 'resistance',
      name: 'resistance',
      type: 'range',
      label: 'Blast Resistance',
      value: currentProperties.resistance,
      min: 0,
      max: 3600,
      step: 0.5,
      validation: { min: 0, max: 3600 },
      description: 'Resistance to explosions',
      category: 'physical'
    },
    {
      id: 'friction',
      name: 'friction',
      type: 'range',
      label: 'Friction',
      value: currentProperties.friction,
      min: 0,
      max: 1,
      step: 0.05,
      validation: { min: 0, max: 1 },
      description: 'Slipperiness of the block',
      category: 'physical'
    },
    {
      id: 'lightEmission',
      name: 'lightEmission',
      type: 'range',
      label: 'Light Emission',
      value: currentProperties.lightEmission,
      min: 0,
      max: 15,
      step: 1,
      validation: { min: 0, max: 15 },
      description: 'Light level emitted (0-15)',
      category: 'physical'
    },

    // Material Properties
    {
      id: 'material',
      name: 'material',
      type: 'select',
      label: 'Material',
      value: currentProperties.material,
      options: [
        { value: 'stone', label: 'Stone' },
        { value: 'wood', label: 'Wood' },
        { value: 'dirt', label: 'Dirt' },
        { value: 'grass', label: 'Grass' },
        { value: 'sand', label: 'Sand' },
        { value: 'glass', label: 'Glass' },
        { value: 'metal', label: 'Metal' },
        { value: 'cloth', label: 'Cloth' },
        { value: 'water', label: 'Water' },
        { value: 'lava', label: 'Lava' }
      ],
      required: true,
      category: 'material'
    },
    {
      id: 'soundGroup',
      name: 'soundGroup',
      type: 'select',
      label: 'Sound Group',
      value: currentProperties.soundGroup,
      options: [
        { value: 'stone', label: 'Stone' },
        { value: 'wood', label: 'Wood' },
        { value: 'dirt', label: 'Dirt' },
        { value: 'grass', label: 'Grass' },
        { value: 'sand', label: 'Sand' },
        { value: 'glass', label: 'Glass' },
        { value: 'metal', label: 'Metal' },
        { value: 'cloth', label: 'Cloth' },
        { value: 'water', label: 'Water' },
        { value: 'lava', label: 'Lava' }
      ],
      required: true,
      category: 'material'
    },
    {
      id: 'mapColor',
      name: 'mapColor',
      type: 'color',
      label: 'Map Color',
      value: currentProperties.mapColor,
      validation: {
        custom: (value: string) => {
          if (!value.match(/^#[0-9A-Fa-f]{6}$/)) {
            return 'Must be a valid hex color';
          }
          return null;
        }
      },
      description: 'Color shown on maps',
      category: 'material'
    },

    // Behavior Properties
    {
      id: 'solid',
      name: 'solid',
      type: 'boolean',
      label: 'Solid',
      value: currentProperties.solid,
      category: 'behavior'
    },
    {
      id: 'liquid',
      name: 'liquid',
      type: 'boolean',
      label: 'Liquid',
      value: currentProperties.liquid,
      category: 'behavior'
    },
    {
      id: 'transparent',
      name: 'transparent',
      type: 'boolean',
      label: 'Transparent',
      value: currentProperties.transparent,
      category: 'behavior'
    },
    {
      id: 'walkable',
      name: 'walkable',
      type: 'boolean',
      label: 'Walkable',
      value: currentProperties.walkable,
      category: 'behavior'
    },
    {
      id: 'climbable',
      name: 'climbable',
      type: 'boolean',
      label: 'Climbable',
      value: currentProperties.climbable,
      category: 'behavior'
    },
    {
      id: 'flammable',
      name: 'flammable',
      type: 'boolean',
      label: 'Flammable',
      value: currentProperties.flammable,
      category: 'behavior'
    }
  ];

  // Categories for tab organization
  const categories = [
    { id: 'basic', label: 'Basic Properties', fields: ['identifier', 'displayName', 'description', 'category'] },
    { id: 'physical', label: 'Physical Properties', fields: ['hardness', 'resistance', 'friction', 'lightEmission'] },
    { id: 'material', label: 'Material Properties', fields: ['material', 'soundGroup', 'mapColor'] },
    { id: 'behavior', label: 'Behavior', fields: ['solid', 'liquid', 'transparent', 'walkable', 'climbable', 'flammable'] }
  ];

  // Custom validation rules
  const validationRules: Record<string, ValidationRule[]> = {
    hardness: [
      ValidationEngine.warning('Hardness of 0 makes the block instantly breakable')
    ],
    resistance: [
      ValidationEngine.warning('Resistance above 1000 makes the block explosion-proof')
    ],
    lightEmission: [
      ValidationEngine.info('Light level 15 is the maximum in Minecraft')
    ]
  };

  // Handle property changes
  const handleFieldChange = useCallback((fieldId: string, value: any) => {
    const updatedProperties = { ...currentProperties, [fieldId]: value };
    setCurrentProperties(updatedProperties);
    onPropertiesChange(updatedProperties);
  }, [currentProperties, onPropertiesChange]);

  return (
    <Box className="block-property-editor">
      <Grid container spacing={3}>
        {/* Main Editor */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <VisualEditor
                title="Block Properties"
                fields={formFields}
                initialData={currentProperties}
                onFieldChange={handleFieldChange}
                onValidationChange={onValidationChange}
                categories={categories}
                layout="tabs"
                validationRules={validationRules}
                readOnly={readOnly}
              />
            </CardContent>
          </Card>
        </Grid>

        {/* Preview Panel */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Block Preview
              </Typography>
              <Preview3D
                properties={currentProperties}
                onPropertyChange={handleFieldChange}
                readOnly={readOnly}
              />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};
