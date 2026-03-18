r"""
Seed data for Community Pattern Library

Creates initial categories, tags, and patterns for launch.
"""
import asyncio
from datetime import datetime
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.base import AsyncSessionLocal
from db.pattern_models import (
    PatternCategory, PatternTag, Pattern, 
    PatternRating, PatternReview
)
from db.pattern_crud import generate_slug


# Sample categories
CATEGORIES = [
    {"name": "UI Components", "description": "User interface components and widgets", "icon": "🖼️", "sort_order": 1},
    {"name": "Data Processing", "description": "Data transformation and manipulation patterns", "icon": "⚙️", "sort_order": 2},
    {"name": "Validation", "description": "Input validation and sanitization patterns", "icon": "✅", "sort_order": 3},
    {"name": "API Integration", "description": "External API communication patterns", "icon": "🔌", "sort_order": 4},
    {"name": "Error Handling", "description": "Error handling and recovery patterns", "icon": "🔄", "sort_order": 5},
    {"name": "Performance", "description": "Optimization and caching patterns", "icon": "🚀", "sort_order": 6},
    {"name": "Security", "description": "Security and authentication patterns", "icon": "🔒", "sort_order": 7},
    {"name": "Testing", "description": "Testing utility patterns", "icon": "🧪", "sort_order": 8},
]

# Sample tags
TAGS = [
    "button", "form", "modal", "dropdown", "input", "table", "card", "list",
    "filter", "sort", "search", "pagination", "lazy-load", "cache", "debounce",
    "throttle", "validation", "auth", "api", "rest", "websocket", "async",
    "optimization", "react", "vue", "angular", "javascript", "typescript"
]

# Sample patterns (10+ for launch)
PATTERNS = [
    {
        "name": "Responsive Button Component",
        "description": "A flexible button component that adapts to different screen sizes and supports multiple variants (primary, secondary, outline, ghost).",
        "code": """// Responsive Button Component
const Button = ({
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  icon,
  iconPosition = 'left',
  fullWidth = false,
  onClick,
  ...props
}) => {
  const baseClasses = 'btn';
  const variantClasses = `btn-${variant}`;
  const sizeClasses = `btn-${size}`;
  const widthClass = fullWidth ? 'btn-full' : '';
  
  const iconComponent = loading 
    ? <Spinner size={size} /> 
    : icon && iconPosition === 'left' 
      ? <span className="btn-icon">{icon}</span> 
      : null;
      
  const iconAfter = icon && iconPosition === 'right' 
    ? <span className="btn-icon">{icon}</span> 
    : null;

  return (
    <button
      className={`${baseClasses} ${variantClasses} ${sizeClasses} ${widthClass}`}
      disabled={disabled || loading}
      onClick={onClick}
      {...props}
    >
      {iconComponent}
      <span className="btn-text">{children}</span>
      {iconAfter}
    </button>
  );
};

export default Button;""",
        "code_language": "javascript",
        "category": "UI Components",
        "tags": ["button", "react", "javascript"],
    },
    {
        "name": "Form Input with Validation",
        "description": "A reusable form input component with built-in validation, error display, and label support.",
        "code": """// Form Input with Validation
import { useState } from 'react';

const Input = ({
  label,
  type = 'text',
  name,
  value,
  onChange,
  placeholder,
  required = false,
  minLength,
  maxLength,
  pattern,
  error,
  helperText,
  disabled = false,
  ...props
}) => {
  const [touched, setTouched] = useState(false);
  
  const handleBlur = () => setTouched(true);
  
  const showError = touched && error;
  
  return (
    <div className={`input-wrapper ${showError ? 'has-error' : ''}`}>
      {label && (
        <label htmlFor={name} className="input-label">
          {label}
          {required && <span className="required">*</span>}
        </label>
      )}
      <input
        id={name}
        name={name}
        type={type}
        value={value}
        onChange={onChange}
        onBlur={handleBlur}
        placeholder={placeholder}
        minLength={minLength}
        maxLength={maxLength}
        pattern={pattern}
        disabled={disabled}
        className={`input-field ${showError ? 'error' : ''}`}
        {...props}
      />
      {(showError || helperText) && (
        <span className={`input-helper ${showError ? 'error' : ''}`}>
          {showError ? error : helperText}
        </span>
      )}
    </div>
  );
};

export default Input;""",
        "code_language": "javascript",
        "category": "UI Components",
        "tags": ["form", "input", "validation", "react"],
    },
    {
        "name": "Debounce Function",
        "description": "A utility function to debounce function calls, useful for search inputs and resize handlers.",
        "code": """/**
 * Creates a debounced version of a function
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in milliseconds
 * @returns {Function} Debounced function
 */
export function debounce(fn, delay) {
  let timeoutId;
  
  return function(...args) {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => {
      fn.apply(this, args);
    }, delay);
  };
}

// Usage example:
// const debouncedSearch = debounce((query) => {
//   performSearch(query);
// }, 300);

// In search input:
// onChange={(e) => debouncedSearch(e.target.value)}""",
        "code_language": "javascript",
        "category": "Performance",
        "tags": ["debounce", "optimization", "javascript"],
    },
    {
        "name": "Throttle Function",
        "description": "A utility function to throttle function calls, useful for scroll handlers and window resize events.",
        "code": """/**
 * Creates a throttled version of a function
 * @param {Function} fn - Function to throttle
 * @param {number} limit - Time limit in milliseconds
 * @returns {Function} Throttled function
 */
export function throttle(fn, limit) {
  let inThrottle;
  let lastResult;
  
  return function(...args) {
    if (!inThrottle) {
      lastResult = fn.apply(this, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
    return lastResult;
  };
}

// Usage example:
// const throttledScroll = throttle(() => {
//   console.log('Scroll position:', window.scrollY);
// }, 100);

// window.addEventListener('scroll', throttledScroll);""",
        "code_language": "javascript",
        "category": "Performance",
        "tags": ["throttle", "optimization", "javascript"],
    },
    {
        "name": "REST API Fetch Wrapper",
        "description": "A clean wrapper around fetch for making REST API calls with error handling and automatic JSON parsing.",
        "code": """// REST API Fetch Wrapper

class ApiClient {
  constructor(baseUrl) {
    this.baseUrl = baseUrl;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const config = {
      ...options,
      headers: {
        ...this.defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const error = await response.json().catch(() => ({}));
        throw new ApiError(response.status, error.message || 'Request failed');
      }
      
      return await response.json();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(0, 'Network error');
    }
  }

  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  put(endpoint, data, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export const api = new ApiClient('/api/v1');
export default api;""",
        "code_language": "javascript",
        "category": "API Integration",
        "tags": ["api", "rest", "fetch", "javascript"],
    },
    {
        "name": "Modal Component",
        "description": "A reusable modal dialog component with animation, close on escape, and backdrop click support.",
        "code": """// Modal Component
import { useEffect, useCallback } from 'react';

const Modal = ({
  isOpen,
  onClose,
  title,
  children,
  size = 'medium',
  closeOnOverlayClick = true,
  showCloseButton = true,
}) => {
  // Handle escape key
  const handleEscape = useCallback((e) => {
    if (e.key === 'Escape') onClose();
  }, [onClose]);

  useEffect(() => {
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, handleEscape]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={closeOnOverlayClick ? onClose : undefined}>
      <div 
        className={`modal-container modal-${size}`}
        onClick={(e) => e.stopPropagation()}
      >
        {(title || showCloseButton) && (
          <div className="modal-header">
            {title && <h2 className="modal-title">{title}</h2>}
            {showCloseButton && (
              <button className="modal-close" onClick={onClose}>
                &times;
              </button>
            )}
          </div>
        )}
        <div className="modal-content">
          {children}
        </div>
      </div>
    </div>
  );
};

export default Modal;""",
        "code_language": "javascript",
        "category": "UI Components",
        "tags": ["modal", "react", "javascript"],
    },
    {
        "name": "Email Validation Pattern",
        "description": "A robust email validation pattern that follows RFC 5322 standard.",
        "code": """// Email Validation Pattern

/**
 * Validates email addresses using RFC 5322 compliant regex
 * @param {string} email - Email address to validate
 * @returns {boolean} True if valid email format
 */
export function isValidEmail(email) {
  if (!email || typeof email !== 'string') return false;
  
  // RFC 5322 compliant email regex
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
  
  return emailRegex.test(email.trim().toLowerCase());
}

/**
 * Validates email and returns detailed error message
 * @param {string} email - Email to validate
 * @returns {object} Validation result with isValid and message
 */
export function validateEmail(email) {
  if (!email) {
    return { isValid: false, message: 'Email is required' };
  }
  
  if (!isValidEmail(email)) {
    return { isValid: false, message: 'Please enter a valid email address' };
  }
  
  return { isValid: true, message: '' };
}

// Usage
// const { isValid, message } = validateEmail('user@example.com');""",
        "code_language": "javascript",
        "category": "Validation",
        "tags": ["validation", "email", "javascript"],
    },
    {
        "name": "Error Boundary Component",
        "description": "A React error boundary component that catches JavaScript errors in child components.",
        "code": """// Error Boundary Component
import React from 'react';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
    
    // Optionally report to error tracking service
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback({
          error: this.state.error,
          errorInfo: this.state.errorInfo,
          resetError: this.handleReset,
        });
      }

      return (
        <div className="error-boundary">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={this.handleReset}>Try Again</button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;""",
        "code_language": "javascript",
        "category": "Error Handling",
        "tags": ["error-handling", "react", "javascript"],
    },
    {
        "name": "Local Storage Cache Utility",
        "description": "A utility for caching data in localStorage with expiration support.",
        "code": """// Local Storage Cache Utility

const Cache = {
  /**
   * Set item in cache with optional expiration
   * @param {string} key - Cache key
   * @param {any} value - Value to cache
   * @param {number} expiryMs - Expiration time in milliseconds
   */
  set(key, value, expiryMs = null) {
    const item = {
      value,
      expiry: expiryMs ? Date.now() + expiryMs : null,
    };
    try {
      localStorage.setItem(key, JSON.stringify(item));
    } catch (e) {
      console.warn('Cache set failed:', e);
    }
  },

  /**
   * Get item from cache
   * @param {string} key - Cache key
   * @returns {any} Cached value or null
   */
  get(key) {
    try {
      const item = localStorage.getItem(key);
      if (!item) return null;
      
      const { value, expiry } = JSON.parse(item);
      
      if (expiry && Date.now() > expiry) {
        this.remove(key);
        return null;
      }
      
      return value;
    } catch (e) {
      return null;
    }
  },

  /**
   * Remove item from cache
   * @param {string} key - Cache key
   */
  remove(key) {
    localStorage.removeItem(key);
  },

  /**
   * Clear all cache
   */
  clear() {
    localStorage.clear();
  },
};

export default Cache;""",
        "code_language": "javascript",
        "category": "Performance",
        "tags": ["cache", "localStorage", "javascript"],
    },
    {
        "name": "Dropdown Select Component",
        "description": "A searchable dropdown select component with multi-select support.",
        "code": """// Dropdown Select Component
import { useState, useRef, useEffect } from 'react';

const Dropdown = ({
  options = [],
  value,
  onChange,
  placeholder = 'Select...',
  searchable = false,
  multi = false,
  disabled = false,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef(null);

  const filteredOptions = searchable
    ? options.filter(opt => 
        opt.label.toLowerCase().includes(search.toLowerCase())
      )
    : options;

  const selectedLabels = multi
    ? options.filter(o => value?.includes(o.value)).map(o => o.label).join(', ')
    : options.find(o => o.value === value)?.label;

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (optionValue) => {
    if (multi) {
      const newValue = value?.includes(optionValue)
        ? value.filter(v => v !== optionValue)
        : [...(value || []), optionValue];
      onChange(newValue);
    } else {
      onChange(optionValue);
      setIsOpen(false);
    }
  };

  return (
    <div ref={dropdownRef} className={`dropdown ${isOpen ? 'open' : ''} ${disabled ? 'disabled' : ''}`}>
      <div className="dropdown-trigger" onClick={() => !disabled && setIsOpen(!isOpen)}>
        <span>{selectedLabels || placeholder}</span>
        <span className="dropdown-arrow">▼</span>
      </div>
      {isOpen && (
        <div className="dropdown-menu">
          {searchable && (
            <input
              className="dropdown-search"
              placeholder="Search..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          )}
          <div className="dropdown-options">
            {filteredOptions.map(opt => (
              <div
                key={opt.value}
                className={`dropdown-option ${value?.includes(opt.value) ? 'selected' : ''}`}
                onClick={() => handleSelect(opt.value)}
              >
                {opt.label}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default Dropdown;""",
        "code_language": "javascript",
        "category": "UI Components",
        "tags": ["dropdown", "form", "react", "javascript"],
    },
    {
        "name": "Pagination Component",
        "description": "A reusable pagination component with page numbers, next/previous buttons, and page size selector.",
        "code": """// Pagination Component
import React from 'react';

const Pagination = ({
  currentPage = 1,
  totalPages = 1,
  pageSize = 10,
  pageSizeOptions = [10, 25, 50, 100],
  onPageChange,
  onPageSizeChange,
  showPageSize = true,
}) => {
  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      pages.push(1);
      
      if (currentPage > 3) pages.push('...');
      
      for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
        pages.push(i);
      }
      
      if (currentPage < totalPages - 2) pages.push('...');
      
      pages.push(totalPages);
    }
    
    return pages;
  };

  return (
    <div className="pagination">
      <button
        className="pagination-btn"
        disabled={currentPage === 1}
        onClick={() => onPageChange(currentPage - 1)}
      >
        Previous
      </button>
      
      <div className="pagination-pages">
        {getPageNumbers().map((page, idx) => (
          page === '...' ? (
            <span key={idx} className="pagination-ellipsis">...</span>
          ) : (
            <button
              key={idx}
              className={`pagination-page ${currentPage === page ? 'active' : ''}`}
              onClick={() => onPageChange(page)}
            >
              {page}
            </button>
          )
        ))}
      </div>
      
      <button
        className="pagination-btn"
        disabled={currentPage === totalPages}
        onClick={() => onPageChange(currentPage + 1)}
      >
        Next
      </button>
      
      {showPageSize && (
        <select
          className="pagination-size"
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {pageSizeOptions.map(size => (
            <option key={size} value={size}>{size} per page</option>
          ))}
        </select>
      )}
    </div>
  );
};

export default Pagination;""",
        "code_language": "javascript",
        "category": "UI Components",
        "tags": ["pagination", "react", "javascript"],
    },
    {
        "name": "Fetch with Retry Logic",
        "description": "A fetch wrapper with automatic retry logic for failed requests.",
        "code": """// Fetch with Retry Logic

/**
 * Fetch with automatic retry
 * @param {string} url - URL to fetch
 * @param {object} options - Fetch options
 * @param {number} maxRetries - Maximum retry attempts
 * @param {number} retryDelay - Delay between retries in ms
 * @returns {Promise} Fetch response
 */
export async function fetchWithRetry(url, options = {}, maxRetries = 3, retryDelay = 1000) {
  const { retryableStatuses = [408, 429, 500, 502, 503, 504], ...fetchOptions } = options;
  
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      const response = await fetch(url, fetchOptions);
      
      if (!retryableStatuses.includes(response.status)) {
        return response;
      }
      
      console.warn(`Retry ${attempt + 1}/${maxRetries} for ${url}`);
    } catch (error) {
      if (attempt === maxRetries - 1) throw error;
      console.warn(`Retry ${attempt + 1}/${maxRetries} for ${url}:`, error);
    }
    
    // Exponential backoff
    await new Promise(resolve => 
      setTimeout(resolve, retryDelay * Math.pow(2, attempt))
    );
  }
  
  throw new Error(`Failed after ${maxRetries} retries`);
}

// Usage
// const data = await fetchWithRetry('/api/data', {
//   method: 'GET',
//   retryableStatuses: [500, 502, 503],
//   retries: 3,
// });""",
        "code_language": "javascript",
        "category": "API Integration",
        "tags": ["fetch", "retry", "api", "javascript"],
    },
]


async def seed_database():
    """Seed the database with initial data"""
    async with AsyncSessionLocal() as db:
        print("Seeding database...")
        
        # Create categories
        category_map = {}
        for cat_data in CATEGORIES:
            # Check if category exists
            result = await db.execute(
                select(PatternCategory).filter(PatternCategory.name == cat_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                category = PatternCategory(
                    id=str(uuid4()),
                    name=cat_data["name"],
                    description=cat_data["description"],
                    icon=cat_data.get("icon"),
                    sort_order=cat_data.get("sort_order", 0),
                    is_active=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                db.add(category)
                await db.flush()
                category_map[cat_data["name"]] = category.id
                print(f"Created category: {cat_data['name']}")
            else:
                category_map[cat_data["name"]] = existing.id
                print(f"Category already exists: {cat_data['name']}")
        
        # Create tags
        tag_map = {}
        for tag_name in TAGS:
            result = await db.execute(
                select(PatternTag).filter(PatternTag.name == tag_name)
            )
            existing = result.scalar_one_or_none()
            
            if not existing:
                tag = PatternTag(
                    id=str(uuid4()),
                    name=tag_name,
                    usage_count=0,
                    created_at=datetime.utcnow(),
                )
                db.add(tag)
                await db.flush()
                tag_map[tag_name] = tag
                print(f"Created tag: {tag_name}")
            else:
                tag_map[tag_name] = existing
                print(f"Tag already exists: {tag_name}")
        
        # Create patterns
        patterns_created = 0
        for pattern_data in PATTERNS:
            # Check if pattern exists
            result = await db.execute(
                select(Pattern).filter(Pattern.name == pattern_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"Pattern already exists: {pattern_data['name']}")
                continue
            
            category_id = category_map.get(pattern_data["category"])
            if not category_id:
                print(f"Category not found for pattern: {pattern_data['name']}")
                continue
            
            # Get tags
            tags = []
            for tag_name in pattern_data.get("tags", []):
                if tag_name in tag_map:
                    tags.append(tag_map[tag_name])
            
            # Generate slug
            slug = await generate_slug(pattern_data["name"], db)
            
            # Create pattern
            pattern = Pattern(
                id=str(uuid4()),
                name=pattern_data["name"],
                slug=slug,
                description=pattern_data["description"],
                code=pattern_data["code"],
                code_language=pattern_data["code_language"],
                category_id=category_id,
                author_id=None,
                author_name="ModPorter Team",
                status="approved",
                version=1,
                view_count=0,
                download_count=0,
                use_count=0,
                avg_rating=0.0,
                rating_count=0,
                is_featured=patterns_created < 3,  # Feature first 3
                published_at=datetime.utcnow(),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            pattern.tags = tags
            db.add(pattern)
            await db.flush()
            
            patterns_created += 1
            print(f"Created pattern: {pattern_data['name']}")
        
        await db.commit()
        print(f"\nSeeding complete! Created {patterns_created} new patterns.")
        print(f"Total categories: {len(category_map)}")
        print(f"Total tags: {len(tag_map)}")


if __name__ == "__main__":
    asyncio.run(seed_database())
