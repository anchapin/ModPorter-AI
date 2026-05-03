/** @type {import('dependency-cruiser').IConfiguration} */
module.exports = {
  forbidden: [
    {
      name: 'no-circular',
      severity: 'error',
      comment: 'Circular dependencies are not allowed',
      from: {},
      to: { circular: true },
    },
    {
      name: 'no-orphans',
      severity: 'warn',
      comment: 'This file has no dependents. Is it dead code?',
      from: {
        pathNot: [
          'src/main.tsx',
          'src/App.tsx',
          'src/vite-env.d.ts',
          '**/*.test.ts',
          '**/*.test.tsx',
          '**/*.stories.tsx',
        ],
      },
      to: {
        numberOfDependentsLessThan: 1,
      },
    },
  ],
  options: {
    doNotFollow: {
      path: 'node_modules',
    },
    tsPreCompilationDeps: true,
    tsConfig: {
      fileName: 'tsconfig.app.json',
    },
  },
};
