import React, { useCallback, useMemo } from 'react';
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
  InputAdornment,
} from '@mui/material';
import { FormField } from './VisualEditor';

// Helper component to reduce duplicate code in field rendering
const BaseTextField: React.FC<{
  field: FormField;
  value: any;
  onChange: (value: any) => void;
  error?: boolean;
  helperText?: string;
  readOnly: boolean;
  inputProps?: object;
  inputAdornment?: React.ReactNode;
}> = ({
  field,
  value,
  onChange,
  error,
  helperText,
  readOnly,
  inputProps,
  inputAdornment,
}) => (
  <TextField
    key={field.id}
    fullWidth
    label={field.label}
    value={value}
    onChange={(e) => onChange(e.target.value)}
    error={error}
    helperText={helperText}
    required={field.required}
    disabled={readOnly || field.disabled}
    {...inputProps}
    InputProps={inputAdornment ? { startAdornment: inputAdornment } : undefined}
  />
);

export interface FormBuilderProps {
  fields: FormField[];
  data: Record<string, any>;
  onChange: (fieldId: string, value: any) => void;
  getFieldErrors: (
    fieldName: string
  ) => Array<{ message: string; severity: 'error' | 'warning' | 'info' }>;
  readOnly?: boolean;
}

export const FormBuilder: React.FC<FormBuilderProps> = ({
  fields,
  data,
  onChange,
  getFieldErrors,
  readOnly = false,
}) => {
  const handleChange = useCallback(
    (field: FormField, value: any) => {
      onChange(field.name, value);
    },
    [onChange]
  );

  const renderField = useCallback(
    (field: FormField) => {
      const errors = getFieldErrors(field.name);
      const hasError = errors.some((e) => e.severity === 'error');
      const helperText =
        errors.find((e) => e.severity === 'error')?.message ||
        field.description;

      switch (field.type) {
        case 'text':
          return (
            <BaseTextField
              field={field}
              value={data[field.name] || ''}
              onChange={(value) => handleChange(field, value)}
              error={hasError}
              helperText={helperText}
              readOnly={readOnly}
              inputAdornment={
                field.name.includes('url') ? (
                  <InputAdornment position="start">🌐</InputAdornment>
                ) : undefined
              }
            />
          );

        case 'number':
          return (
            <BaseTextField
              field={field}
              value={data[field.name] || ''}
              onChange={(value) => handleChange(field, parseFloat(value) || 0)}
              error={hasError}
              helperText={helperText}
              readOnly={readOnly}
              inputProps={{
                type: 'number',
                min: field.min,
                max: field.max,
                step: field.step || 1,
              }}
            />
          );

        case 'textarea':
          return (
            <BaseTextField
              field={field}
              value={data[field.name] || ''}
              onChange={(value) => handleChange(field, value)}
              error={hasError}
              helperText={helperText}
              readOnly={readOnly}
              inputProps={{ multiline: true, rows: 4 }}
            />
          );

        case 'select':
          return (
            <FormControl
              key={field.id}
              fullWidth
              required={field.required}
              error={hasError}
            >
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
                '& input': {
                  height: 40,
                  cursor:
                    readOnly || field.disabled ? 'not-allowed' : 'pointer',
                },
              }}
            />
          );

        default:
          return (
            <BaseTextField
              field={field}
              value={data[field.name] || ''}
              onChange={(value) => handleChange(field, value)}
              error={hasError}
              helperText={helperText}
              readOnly={readOnly}
            />
          );
      }
    },
    [data, getFieldErrors, handleChange, readOnly]
  );

  const visibleFields = useMemo(
    () => fields.filter((field) => field.visible !== false),
    [fields]
  );

  // ⚡ Bolt optimization: Compute summary metrics in a single O(N) pass
  // instead of multiple O(3N) inline array filters on every render
  const formSummary = useMemo(() => {
    let filled = 0;
    let required = 0;

    for (const f of visibleFields) {
      if (data[f.name] !== undefined && data[f.name] !== '') filled++;
      if (f.required) required++;
    }

    let errors = 0;
    const allErrors = getFieldErrors('all');
    for (const e of allErrors) {
      if (e.severity === 'error') errors++;
    }

    return { filled, required, errors };
  }, [visibleFields, data, getFieldErrors]);

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
  const fieldsByCategory = visibleFields.reduce(
    (acc, field) => {
      const category = field.category || 'general';
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category].push(field);
      return acc;
    },
    {} as Record<string, FormField[]>
  );

  const categories = Object.keys(fieldsByCategory);

  return (
    <Box className="form-builder">
      {categories.map((category) => (
        <Box key={category} sx={{ mb: 3 }}>
          {categories.length > 1 && (
            <Typography variant="h6" gutterBottom>
              {category.charAt(0).toUpperCase() + category.slice(1)}
            </Typography>
          )}

          <Box className="form-fields">
            {fieldsByCategory[category].map((field) => (
              <Box key={field.id} sx={{ mb: 2 }}>
                {renderField(field)}

                {/* Display validation warnings and info */}
                {getFieldErrors(field.name).map((error, index) => (
                  <FormHelperText
                    key={index}
                    error={error.severity === 'error'}
                    sx={{
                      color:
                        error.severity === 'warning'
                          ? 'warning.main'
                          : error.severity === 'info'
                            ? 'info.main'
                            : 'error.main',
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
              label={`${formSummary.filled} fields filled`}
              size="small"
              color="primary"
            />
            <Chip
              label={`${formSummary.required} required fields`}
              size="small"
              color="secondary"
            />
            <Chip
              label={`${formSummary.errors} errors`}
              size="small"
              color="error"
            />
          </Box>
        </Box>
      )}
    </Box>
  );
};
