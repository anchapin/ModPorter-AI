import { FormField, ValidationRule } from './VisualEditor';

export class ValidationEngine {
  private rules: Record<string, ValidationRule[]>;

  constructor(rules: Record<string, ValidationRule[]> = {}) {
    this.rules = rules;
  }

  validate(
    data: Record<string, any>,
    fields: FormField[]
  ): ValidationRule[] {
    const errors: ValidationRule[] = [];

    // Validate each field
    fields.forEach(field => {
      const value = data[field.name];
      const fieldErrors = this.validateField(field, value);
      errors.push(...fieldErrors);

      // Apply custom validation rules
      const customRules = this.rules[field.name] || [];
      customRules.forEach(rule => {
        if (this.shouldApplyRule(rule, value, data)) {
          errors.push(rule);
        }
      });
    });

    return errors;
  }

  private validateField(field: FormField, value: any): ValidationRule[] {
    const errors: ValidationRule[] = [];

    // Required field validation
    if (field.required && this.isEmpty(value)) {
      errors.push({
        field: field.name,
        rule: 'required',
        message: `${field.label} is required`,
        severity: 'error'
      });
      return errors;
    }

    // Skip further validation if field is empty and not required
    if (this.isEmpty(value)) {
      return errors;
    }

    // Type-specific validation
    switch (field.type) {
      case 'number':
        if (isNaN(Number(value))) {
          errors.push({
            field: field.name,
            rule: 'type',
            message: `${field.label} must be a valid number`,
            severity: 'error'
          });
        } else {
          const numValue = Number(value);
          if (field.min !== undefined && numValue < field.min) {
            errors.push({
              field: field.name,
              rule: 'min',
              message: `${field.label} must be at least ${field.min}`,
              severity: 'error'
            });
          }
          if (field.max !== undefined && numValue > field.max) {
            errors.push({
              field: field.name,
              rule: 'max',
              message: `${field.label} must not exceed ${field.max}`,
              severity: 'error'
            });
          }
        }
        break;

      case 'text': {
        const strValue = String(value);
        if (field.validation?.minLength && strValue.length < field.validation.minLength) {
          errors.push({
            field: field.name,
            rule: 'minLength',
            message: `${field.label} must be at least ${field.validation.minLength} characters long`,
            severity: 'error'
          });
        }
        if (field.validation?.maxLength && strValue.length > field.validation.maxLength) {
          errors.push({
            field: field.name,
            rule: 'maxLength',
            message: `${field.label} must not exceed ${field.validation.maxLength} characters`,
            severity: 'error'
          });
        }
        if (field.validation?.pattern && !new RegExp(field.validation.pattern).test(strValue)) {
          errors.push({
            field: field.name,
            rule: 'pattern',
            message: `${field.label} has an invalid format`,
            severity: 'error'
          });
        }
        break;
      }

      case 'select': {
        const validOptions = field.options?.map(opt => opt.value) || [];
        if (!validOptions.includes(value)) {
          errors.push({
            field: field.name,
            rule: 'invalidOption',
            message: `${field.label} has an invalid option selected`,
            severity: 'error'
          });
        }
        break;
      }
    }

    // Custom validation
    if (field.validation?.custom) {
      const customError = field.validation.custom(value);
      if (customError) {
        errors.push({
          field: field.name,
          rule: 'custom',
          message: customError,
          severity: 'error'
        });
      }
    }

    return errors;
  }

  private shouldApplyRule(rule: ValidationRule, value: any): boolean {
    // This is a simplified implementation - you can extend this with more complex logic
    switch (rule.rule) {
      case 'required':
        return this.isEmpty(value);
      case 'positive':
        return Number(value) <= 0;
      case 'percentage':
        return Number(value) < 0 || Number(value) > 100;
      default:
        return true;
    }
  }

  private isEmpty(value: any): boolean {
    return value === null || value === undefined || value === '';
  }

  // Helper method to add validation rules dynamically
  addRule(fieldName: string, rule: ValidationRule): void {
    if (!this.rules[fieldName]) {
      this.rules[fieldName] = [];
    }
    this.rules[fieldName].push(rule);
  }

  // Helper method to remove validation rules
  removeRule(fieldName: string, ruleType?: string): void {
    if (ruleType) {
      this.rules[fieldName] = this.rules[fieldName]?.filter(
        rule => rule.rule !== ruleType
      ) || [];
    } else {
      delete this.rules[fieldName];
    }
  }

  // Helper method to validate a single field
  validateFieldOnly(field: FormField, value: any): ValidationRule[] {
    return this.validateField(field, value);
  }

  // Helper method to get validation summary
  getValidationSummary(errors: ValidationRule[]): {
    errors: number;
    warnings: number;
    info: number;
    fields: string[];
  } {
    const summary = {
      errors: errors.filter(e => e.severity === 'error').length,
      warnings: errors.filter(e => e.severity === 'warning').length,
      info: errors.filter(e => e.severity === 'info').length,
      fields: [...new Set(errors.map(e => e.field))]
    };

    return summary;
  }

  // Static helper methods for common validations
  static required(message?: string): ValidationRule {
    return {
      field: '',
      rule: 'required',
      message: message || 'This field is required',
      severity: 'error'
    };
  }

  static min(min: number, message?: string): ValidationRule {
    return {
      field: '',
      rule: 'min',
      message: message || `Value must be at least ${min}`,
      severity: 'error'
    };
  }

  static max(max: number, message?: string): ValidationRule {
    return {
      field: '',
      rule: 'max',
      message: message || `Value must not exceed ${max}`,
      severity: 'error'
    };
  }

  static positive(message?: string): ValidationRule {
    return {
      field: '',
      rule: 'positive',
      message: message || 'Value must be positive',
      severity: 'error'
    };
  }

  static percentage(message?: string): ValidationRule {
    return {
      field: '',
      rule: 'percentage',
      message: message || 'Value must be between 0 and 100',
      severity: 'error'
    };
  }

  static warning(message: string): ValidationRule {
    return {
      field: '',
      rule: 'warning',
      message: message,
      severity: 'warning'
    };
  }

  static info(message: string): ValidationRule {
    return {
      field: '',
      rule: 'info',
      message: message,
      severity: 'info'
    };
  }
}
