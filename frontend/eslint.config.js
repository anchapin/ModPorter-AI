// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from 'eslint-plugin-storybook';

import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default [
  { ignores: ['dist', 'coverage'] },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.es2021,
        React: 'readonly',
      },
      parser: tseslint.parser,
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
    },
    plugins: {
      '@typescript-eslint': tseslint.plugin,
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...js.configs.recommended.rules,
      ...tseslint.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': [
        'warn',
        { allowConstantExport: true },
      ],
      '@typescript-eslint/no-explicit-any': 'off',
      // Allow unused variables with underscore prefix
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
          caughtErrorsIgnorePattern: '^_',
        },
      ],
      // Disable base rule to avoid conflicts
      'no-unused-vars': 'off',
      // Disable react-hooks exhaustive-deps rule - too strict for this codebase
      'react-hooks/exhaustive-deps': 'off',
      // Naming conventions - enforce with practical exceptions
      '@typescript-eslint/naming-convention': [
        'error',
        // Variables, functions should use camelCase (default for JS/TS)
        // Allow PascalCase for React components
        {
          selector: 'variable',
          format: ['camelCase', 'UPPER_CASE', 'PascalCase'],
          leadingUnderscore: 'allow',
        },
        {
          selector: 'function',
          format: ['camelCase', 'PascalCase'],
        },
        // Classes, interfaces, types, enums, and React components should use PascalCase
        {
          selector: 'class',
          format: ['PascalCase'],
        },
        {
          selector: 'interface',
          format: ['PascalCase'],
        },
        {
          selector: 'typeAlias',
          format: ['PascalCase'],
        },
        {
          selector: 'enum',
          format: ['PascalCase'],
        },
        // Properties - allow camelCase, UPPER_CASE, snake_case, and special patterns
        {
          selector: 'property',
          format: ['camelCase', 'UPPER_CASE', 'snake_case'],
          leadingUnderscore: 'allow',
        },
        // Allow properties with special characters (HTTP headers, MIME types, paths, namespaces, CSS selectors, numeric keys)
        {
          selector: 'property',
          format: null,
          // Match properties with: hyphens, slashes, colons, ampersands, numeric keys, spaces, or title-case words
          filter: {
            regex: '[-/:&\\s]|^\\d+$|.+:.+$|^[A-Z][a-z]+',
            match: true,
          },
        },
        // Type parameters should use PascalCase
        {
          selector: 'typeParameter',
          format: ['PascalCase'],
        },
        // Ignore destructured variables that might have specific names
        {
          selector: 'variable',
          modifiers: ['destructured'],
          format: null,
        },
        // Allow default exports to have any name (React components)
        {
          selector: 'variable',
          modifiers: ['exported'],
          format: null,
        },
      ],
      camelcase: 'off',
    },
  },
  {
    files: ['**/*.test.{ts,tsx}'],
    languageOptions: {
      globals: {
        ...globals.browser,
        ...globals.node,
        describe: 'readonly',
        test: 'readonly',
        it: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        vi: 'readonly',
        jest: 'readonly',
      },
    },
  },
  {
    files: ['**/*.test.ts', '**/*.test.tsx'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        ...globals.browser,
        ...globals.node,
        describe: 'readonly',
        test: 'readonly',
        it: 'readonly',
        expect: 'readonly',
        beforeEach: 'readonly',
        afterEach: 'readonly',
        vi: 'readonly',
        jest: 'readonly',
      },
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    rules: {
      'react-hooks/set-state-in-effect': 'off', // Allow setState in effects for data fetching patterns
    },
  },
  ...storybook.configs['flat/recommended'],
  {
    files: ['src/services/analytics.ts'],
    rules: {
      'no-redeclare': 'off',
    },
  },
];
