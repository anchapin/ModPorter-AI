import React, { useCallback } from 'react';
import {
  Box,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormControlLabel,
  Switch,
  Slider,
  Typography,
  FormHelperText,
  Chip,
  InputAdornment
} from '@mui/material';
import { FormField } from './VisualEditor';

export interface FormBuilderProps {
  fields: FormField[];
  data: Record<string, any>;
  onChange: (fieldId: string, value: any) => void;
  getFieldErrors: (fieldName: string) => Array<{ message: string; severity: 'error' | 'warning' | 'info' }>;
  readOnly?: boolean;
}

export const FormBuilder: React.FC<FormBuilderProps> = ({
  fields,
  data,
  onChange,
  getFieldErrors,
  readOnly = false
}) => {
  const handleChange = useCallback((field: FormField, value: any) => {
    onChange(field.name, value);
  }, [onChange]);

  const renderField = useCallback((field: FormField) => {
    const errors = getFieldErrors(field.name);
    const hasError = errors.some(e => e.severity === 'error');
    const helperText = errors.find(e => e.severity === 'error')?.message || field.description;

    switch (field.type) {
      case 'text':
        return (
          <TextField
            key={field.id}
            fullWidth
            label={field.label}
            value={data[field.name] || ''}
            onChange={(e) => handleChange(field, e.target.value)}
            error={hasError}
            helperText={helperText}
            required={field.required}
            disabled={readOnly || field.disabled}
            InputProps={{
              startAdornment: field.name.includes('url') && (
                <InputAdornment position="start">🌐</InputAdornment>
              )
            }}
          />
        );

      case 'number':
        return (
          <TextField
            key={field.id}
            fullWidth
            label={field.label}
            type="number"
            value={data[field.name] || ''}
            onChange={(e) => handleChange(field, parseFloat(e.target.value) || 0)}
            error={hasError}
            helperText={helperText}
            required={field.required}
            disabled={readOnly || field.disabled}
            inputProps={{
              min: field.min,
              max: field.max,
              step: field.step || 1
            }}
          />
        );

      case 'textarea':
        return (
          <TextField
            key={field.id}
            fullWidth
            label={field.label}
            multiline
            rows={4}
            value={data[field.name] || ''}
            onChange={(e) => handleChange(field, e.target.value)}
            error={hasError}
            helperText={helperText}
            required={field.required}
            disabled={readOnly || field.disabled}
          />
        );

      case 'select':
        return (
          <FormControl key={field.id} fullWidth required={field.required} error={hasError}>
            <InputLabel>{field.label}</InputLabel>
            <Select
              value={data[field.name] || ''}
              onChange={(e) => handleChange(field, e.target.value)}
              disabled={readOnly || field.disabled}
            >
              {field.options?.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
            {helperText && <FormHelperText>{helperText}</FormHelperText>}
          </FormControl>
        );

      case 'boolean':
        return (
          <FormControlLabel
            key={field.id}
            control={
              <Switch
                checked={data[field.name] || false}
                onChange={(e) => handleChange(field, e.target.checked)}
                disabled={readOnly || field.disabled}
              />
            }
            label={field.label}
          />
        );

      case 'range':
        return (
          <Box key={field.id}>
            <Typography id={`${field.id}-label`} gutterBottom>
              {field.label}: {data[field.name] || field.min || 0}
            </Typography>
            <Slider
              value={data[field.name] || field.min || 0}
              onChange={(_, value) => handleChange(field, value)}
              min={field.min}
              max={field.max}
              step={field.step}
              disabled={readOnly || field.disabled}
              aria-labelledby={`${field.id}-label`}
            />
            {helperText && <FormHelperText>{helperText}</FormHelperText>}
          </Box>
        );

      case 'color':
        return (
          <TextField
            key={field.id}
            fullWidth
            label={field.label}
            type="color"
            value={data[field.name] || '#000000'}
            onChange={(e) => handleChange(field, e.target.value)}
            error={hasError}
            helperText={helperText}
            required={field.required}
            disabled={readOnly || field.disabled}
            sx={{ 
              '& input': { height: 40, cursor: readOnly || field.disabled ? 'not-allowed' : 'pointer' }
            }}
          />
        );

      default:
        return (
          <TextField
            key={field.id}
            fullWidth
            label={field.label}
            value={data[field.name] || ''}
            onChange={(e) => handleChange(field, e.target.value)}
            error={hasError}
            helperText={helperText}
            required={field.required}
            disabled={readOnly || field.disabled}
          />
        );
    }
  }, [data, getFieldErrors, handleChange, readOnly]);

  const visibleFields = fields.filter(field => field.visible !== false);

  if (visibleFields.length === 0) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography variant="body2" color="text.secondary">
          No fields to display
        </Typography>
      </Box>
    );
  }

  // Group fields by category if specified
  const fieldsByCategory = visibleFields.reduce((acc, field) => {
    const category = field.category || 'general';
    if (!acc[category]) {
      acc[category] = [];
    }
    acc[category].push(field);
    return acc;
  }, {} as Record<string, FormField[]>);

  const categories = Object.keys(fieldsByCategory);

  return (
    <Box className="form-builder">
      {categories.map(category => (
        <Box key={category} sx={{ mb: 3 }}>
          {categories.length > 1 && (
            <Typography variant="h6" gutterBottom>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </Typography>
          )}
          
          <Box className="form-fields">
            {fieldsByCategory[category].map(field => (
              <Box key={field.id} sx={{ mb: 2 }}>
                {renderField(field)}
                
                {/* Display validation warnings and info */}
                {getFieldErrors(field.name).map((error, index) => (
                  <FormHelperText
                    key={index}
                    error={error.severity === 'error'}
                    sx={{
                      color: error.severity === 'warning' ? 'warning.main' :
                             error.severity === 'info' ? 'info.main' : 'error.main'
                    }}
                  >
                    {error.message}
                  </FormHelperText>
                ))}
              </Box>
            ))}
          </Box>
        </Box>
      ))}
      
      {/* Summary of field status */}
      {!readOnly && (
        <Box sx={{ mt: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Form Summary
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            <Chip 
              label={`${visibleFields.filter(f => data[f.name] !== undefined && data[f.name] !== '').length} fields filled`}
              size="small" 
              color="primary" 
            />
            <Chip 
              label={`${visibleFields.filter(f => f.required).length} required fields`}
              size="small" 
              color="secondary" 
            />
            <Chip 
              label={`${getFieldErrors('all').filter(e => e.severity === 'error').length} errors`}
              size="small" 
              color="error"
            />
          </Box>
        </Box>
      )}
    </Box>
  );
};
