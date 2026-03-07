// ESLint configuration for React 19 with TypeScript
// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from 'eslint-plugin-storybook';

import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default [
  { ignores: ['dist', 'coverage', 'node_modules', 'build', '.vite'] },
  {
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: {
        ...globals.browser,
        ...globals.node,
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
      // React 19 strict rules
      '@typescript-eslint/no-explicit-any': 'off', // Too many any types in codebase
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
      // Disable camelcase - use TypeScript naming-convention instead
      camelcase: 'off',
      '@typescript-eslint/naming-convention': [
        'error',
        {
          // Classes, interfaces, types, enums should be PascalCase
          selector: ['class', 'interface', 'typeAlias', 'enum', 'enumMember'],
          format: ['PascalCase'],
        },
        {
          // Variables can be camelCase, UPPER_CASE, PascalCase, or snake_case (for API responses)
          selector: 'variable',
          format: ['camelCase', 'UPPER_CASE', 'PascalCase', 'snake_case'],
          leadingUnderscore: 'allow',
        },
        {
          // Functions can be camelCase, UPPER_CASE, or PascalCase (for React components)
          selector: 'function',
          format: ['camelCase', 'UPPER_CASE', 'PascalCase'],
          leadingUnderscore: 'allow',
        },
        {
          // Parameters should be camelCase (allow PascalCase for React component parameters)
          selector: 'parameter',
          format: ['camelCase', 'PascalCase'],
          leadingUnderscore: 'allow',
        },
        {
          // Class properties should be camelCase
          selector: 'classProperty',
          format: ['camelCase', 'UPPER_CASE'],
        },
      ],
      // React 19 specific rules
      'react-hooks/set-state-in-effect': 'off',
      '@typescript-eslint/explicit-function-return-type': 'off',
      '@typescript-eslint/explicit-module-boundary-types': 'off',
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
    files: ['**/*.{ts,tsx}'],
    rules: {
      'react-hooks/set-state-in-effect': 'off',
    },
  },
  ...storybook.configs['flat/recommended'],
];
