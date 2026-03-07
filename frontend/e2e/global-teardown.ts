async function globalTeardown() {
  console.log('🧹 Starting E2E test teardown...');

  // Clean up any test data here
  // For example: delete test users, clean database, etc.

  console.log('✅ E2E test teardown completed');
}

export default globalTeardown;
