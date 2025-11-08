import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Grid,
  Chip,
  Divider
} from '@mui/material';
import {
  Refresh,
  Lightbulb,
  Opacity,
  FitnessCenter,
  LocalFireDepartment
} from '@mui/icons-material';
import { BlockProperties } from './BlockPropertyEditor';
import './BlockPreview.css';

export interface Preview3DProps {
  properties: BlockProperties;
  onPropertyChange: (fieldId: string, value: any) => void;
  readOnly?: boolean;
}

export const Preview3D: React.FC<Preview3DProps> = ({
  properties,
  onPropertyChange,
  readOnly = false
}) => {
  const [rotation, setRotation] = useState({ x: 0, y: 0 });

  // Handle rotation for 3D preview
  const handleRotation = (axis: 'x' | 'y', value: number) => {
    setRotation(prev => ({ ...prev, [axis]: value }));
  };

  // Generate preview style based on properties
  const getBlockStyle = () => {
    return {
      backgroundColor: properties.mapColor,
      opacity: properties.transparent ? 0.7 : 1,
      boxShadow: properties.lightEmission > 0 
        ? `0 0 ${properties.lightEmission * 2}px ${properties.mapColor}` 
        : 'none',
      border: properties.solid ? '2px solid #333' : '1px dashed #666',
      borderRadius: properties.material === 'stone' ? '4px' : 
                   properties.material === 'wood' ? '8px' : '0px',
      transform: `rotateX(${rotation.x}deg) rotateY(${rotation.y}deg)`,
      transition: 'all 0.3s ease'
    };
  };

  // Get material icon
  const getMaterialIcon = () => {
    switch (properties.material) {
      case 'water':
      case 'lava':
        return <Opacity />;
      case 'metal':
        return <FitnessCenter />;
      case 'wood':
        return <LocalFireDepartment />;
      default:
        return <Lightbulb />;
    }
  };

  // Calculate preview statistics
  const getStats = () => {
    return {
      breakTime: properties.hardness > 0 ? `${properties.hardness.toFixed(1)}s` : 'Instant',
      lightLevel: `${properties.lightEmission}/15`,
      blastResistance: properties.resistance >= 1000 ? 'Immune' : `${properties.resistance.toFixed(1)}`,
      slipperiness: properties.friction < 0.6 ? 'Low' : 
                   properties.friction > 0.8 ? 'High' : 'Normal'
    };
  };

  const stats = getStats();

  return (
    <Box className="block-preview">
      {/* 3D Preview */}
      <Box className="preview-container" sx={{ mb: 3 }}>
        <Box className="preview-controls">
          <Tooltip title="Reset View">
            <IconButton 
              size="small" 
              onClick={() => setRotation({ x: 0, y: 0 })}
              disabled={readOnly}
            >
              <Refresh />
            </IconButton>
          </Tooltip>
        </Box>
        
        <Box className="block-3d" sx={{ p: 3 }}>
          <Box className="preview-block" sx={getBlockStyle()}>
            <Box className="block-face front" />
            <Box className="block-face back" />
            <Box className="block-face left" />
            <Box className="block-face right" />
            <Box className="block-face top" />
            <Box className="block-face bottom" />
          </Box>
        </Box>
        
        {/* Rotation Controls */}
        <Box className="rotation-controls" sx={{ mt: 2 }}>
          <Typography variant="caption" display="block" gutterBottom>
            Rotation:
          </Typography>
          <Grid container spacing={1}>
            <Grid item xs={6}>
              <Typography variant="caption">X: {rotation.x}°</Typography>
            </Grid>
            <Grid item xs={6}>
              <Typography variant="caption">Y: {rotation.y}°</Typography>
            </Grid>
          </Grid>
        </Box>
      </Box>

      {/* Properties Summary */}
      <Divider sx={{ my: 2 }} />
      
      <Typography variant="subtitle2" gutterBottom>
        Properties Summary
      </Typography>
      
      <Grid container spacing={1} sx={{ mb: 2 }}>
        <Grid item xs={12}>
          <Box className="property-group">
            <Typography variant="caption" color="text.secondary">
              Material:
            </Typography>
            <Chip 
              size="small" 
              label={properties.material}
              icon={getMaterialIcon()}
              variant="outlined"
            />
          </Box>
        </Grid>
        
        <Grid item xs={12}>
          <Box className="property-group">
            <Typography variant="caption" color="text.secondary">
              Category:
            </Typography>
            <Chip 
              size="small" 
              label={properties.category}
              variant="outlined"
            />
          </Box>
        </Grid>
      </Grid>

      {/* Stats */}
      <Typography variant="subtitle2" gutterBottom>
        Statistics
      </Typography>
      
      <Grid container spacing={1}>
        <Grid item xs={6}>
          <Box className="stat-item">
            <Typography variant="caption" color="text.secondary">
              Break Time:
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {stats.breakTime}
            </Typography>
          </Box>
        </Grid>
        
        <Grid item xs={6}>
          <Box className="stat-item">
            <Typography variant="caption" color="text.secondary">
              Light Level:
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {stats.lightLevel}
            </Typography>
          </Box>
        </Grid>
        
        <Grid item xs={6}>
          <Box className="stat-item">
            <Typography variant="caption" color="text.secondary">
              Blast Resistance:
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {stats.blastResistance}
            </Typography>
          </Box>
        </Grid>
        
        <Grid item xs={6}>
          <Box className="stat-item">
            <Typography variant="caption" color="text.secondary">
              Slipperiness:
            </Typography>
            <Typography variant="body2" fontWeight="bold">
              {stats.slipperiness}
            </Typography>
          </Box>
        </Grid>
      </Grid>

      {/* Behavior Indicators */}
      <Divider sx={{ my: 2 }} />
      
      <Typography variant="subtitle2" gutterBottom>
        Behavior Traits
      </Typography>
      
      <Box className="behavior-traits">
        {properties.solid && (
          <Chip size="small" label="Solid" color="primary" variant="outlined" />
        )}
        {properties.transparent && (
          <Chip size="small" label="Transparent" color="info" variant="outlined" />
        )}
        {properties.liquid && (
          <Chip size="small" label="Liquid" color="info" variant="outlined" />
        )}
        {properties.walkable && (
          <Chip size="small" label="Walkable" color="success" variant="outlined" />
        )}
        {properties.climbable && (
          <Chip size="small" label="Climbable" color="warning" variant="outlined" />
        )}
        {properties.flammable && (
          <Chip size="small" label="Flammable" color="error" variant="outlined" />
        )}
      </Box>

      {/* Warnings and Info */}
      {properties.hardness === 0 && (
        <Box className="warning-box" sx={{ mt: 2, p: 1, bgcolor: 'warning.light', borderRadius: 1 }}>
          <Typography variant="caption">
            ⚠️ Block has zero hardness - will break instantly
          </Typography>
        </Box>
      )}
      
      {properties.lightEmission > 10 && (
        <Box className="info-box" sx={{ mt: 2, p: 1, bgcolor: 'info.light', borderRadius: 1 }}>
          <Typography variant="caption">
            💡 High light emission level
          </Typography>
        </Box>
      )}
    </Box>
  );
};
