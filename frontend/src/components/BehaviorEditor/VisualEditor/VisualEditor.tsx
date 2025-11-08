import React, { useState, useCallback, useEffect } from 'react';
import { Box, Tabs, Tab, Typography, Alert, CircularProgress } from '@mui/material';
import { FormBuilder } from './FormBuilder';
import { ValidationEngine } from './ValidationEngine';
import './VisualEditor.css';

export interface FormField {
  id: string;
  name: string;
  type: 'text' | 'number' | 'select' | 'boolean' | 'textarea' | 'range' | 'color' | 'file';
  label: string;
  value: any;
  required?: boolean;
  min?: number;
  max?: number;
  step?: number;
  options?: Array<{ value: string; label: string }>;
  validation?: {
    pattern?: string;
    minLength?: number;
    maxLength?: number;
    min?: number;
    max?: number;
    custom?: (value: any) => string | null;
  };
  description?: string;
  category?: string;
  visible?: boolean;
  disabled?: boolean;
}

export interface ValidationRule {
  field: string;
  rule: string;
  message: string;
  severity: 'error' | 'warning' | 'info';
}

export interface VisualEditorProps {
  title: string;
  fields: FormField[];
  initialData?: Record<string, any>;
  onFieldChange?: (fieldId: string, value: any) => void;
  onValidationChange?: (errors: ValidationRule[]) => void;
  onFormSubmit?: (data: Record<string, any>) => void;
  loading?: boolean;
  error?: string | null;
  categories?: Array<{ id: string; label: string; fields: string[] }>;
  layout?: 'tabs' | 'accordion' | 'single';
  validationRules?: Record<string, ValidationRule[]>;
  readOnly?: boolean;
}

export const VisualEditor: React.FC<VisualEditorProps> = ({
  title,
  fields,
  initialData = {},
  onFieldChange,
  onValidationChange,
  onFormSubmit,
  loading = false,
  error = null,
  categories = [],
  layout = 'tabs',
  validationRules = {},
  readOnly = false
}) => {
  const [formData, setFormData] = useState<Record<string, any>>(initialData);
  const [validationErrors, setValidationErrors] = useState<ValidationRule[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [dirtyFields, setDirtyFields] = useState<Set<string>>(new Set());

  // Initialize form data with initial values
  useEffect(() => {
    setFormData(initialData);
  }, [initialData]);

  // Initialize fields with default values
  useEffect(() => {
    const defaultValues: Record<string, any> = {};
    fields.forEach(field => {
      if (formData[field.name] === undefined && field.value !== undefined) {
        defaultValues[field.name] = field.value;
      }
    });
    if (Object.keys(defaultValues).length > 0) {
      setFormData(prev => ({ ...prev, ...defaultValues }));
    }
  }, [fields, formData]);

  // Handle field value changes
  const handleFieldChange = useCallback((fieldId: string, value: any) => {
    setFormData(prev => ({ ...prev, [fieldId]: value }));
    setDirtyFields(prev => new Set(prev).add(fieldId));
    onFieldChange?.(fieldId, value);
  }, [onFieldChange]);

  // Handle validation
  useEffect(() => {
    const engine = new ValidationEngine(validationRules);
    const errors = engine.validate(formData, fields);
    setValidationErrors(errors);
    onValidationChange?.(errors);
  }, [formData, fields, validationRules, onValidationChange]);

  // Get fields for specific category or all fields
  const getFieldsForCategory = useCallback((categoryId?: string): FormField[] => {
    if (!categoryId || categories.length === 0) {
      return fields;
    }
    const category = categories.find(c => c.id === categoryId);
    if (!category) return [];
    return fields.filter(field => category.fields.includes(field.name));
  }, [fields, categories]);

  // Get field errors
  const getFieldErrors = useCallback((fieldName: string): ValidationRule[] => {
    return validationErrors.filter(error => error.field === fieldName);
  }, [validationErrors]);

  // Check if form has unsaved changes
  const hasUnsavedChanges = dirtyFields.size > 0;

  // Render content based on layout
  const renderContent = () => {
    if (loading) {
      return (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
          <CircularProgress />
        </Box>
      );
    }

    if (error) {
      return <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>;
    }

    if (layout === 'single') {
      return (
        <FormBuilder
          fields={fields}
          data={formData}
          onChange={handleFieldChange}
          getFieldErrors={getFieldErrors}
          readOnly={readOnly}
        />
      );
    }

    // Tabs or Accordion layout
    const tabContent = categories.length > 0 ? categories : [{ id: 'all', label: 'All Fields', fields: fields.map(f => f.name) }];
    
    return (
      <>
        <Tabs 
          value={activeTab} 
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
        >
          {tabContent.map((category) => (
            <Tab key={category.id} label={category.label} />
          ))}
        </Tabs>
        
        {tabContent.map((category, index) => (
          <Box
            key={category.id}
            hidden={activeTab !== index}
            sx={{ py: 2 }}
          >
            {activeTab === index && (
              <FormBuilder
                fields={getFieldsForCategory(category.id)}
                data={formData}
                onChange={handleFieldChange}
                getFieldErrors={getFieldErrors}
                readOnly={readOnly}
              />
            )}
          </Box>
        ))}
      </>
    );
  };

  return (
    <Box className="visual-editor">
      <Box className="editor-header">
        <Typography variant="h5" component="h2">
          {title}
        </Typography>
        {hasUnsavedChanges && (
          <Typography variant="caption" color="warning.main">
            Unsaved changes
          </Typography>
        )}
      </Box>
      
      <Box className="editor-content">
        {renderContent()}
      </Box>
      
      {onFormSubmit && (
        <Box className="editor-footer" sx={{ mt: 3, pt: 2, borderTop: 1, borderColor: 'divider' }}>
          <Box className="validation-summary">
            {validationErrors.length > 0 && (
              <Alert 
                severity={validationErrors.some(e => e.severity === 'error') ? 'error' : 'warning'}
                sx={{ mb: 2 }}
              >
                {validationErrors.filter(e => e.severity === 'error').length} errors, 
                {validationErrors.filter(e => e.severity === 'warning').length} warnings
              </Alert>
            )}
          </Box>
        </Box>
      )}
    </Box>
  );
};
