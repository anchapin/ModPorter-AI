/**
 * portkit Load Test Suite
 * Uses k6 for API load testing
 *
 * Installation:
 *   k6 is a Go binary - download from https://k6.io/docs/getting-started/installation/
 *
 * Run with:
 *   k6 run api-load-test.js
 *
 * Options:
 *   k6 run --vus 10 --duration 30s api-load-test.js
 *   k6 run --vus 50 --duration 5m --rate 10 api-load-test.js
 *   k6 run -e BASE_URL=https://api.example.com api-load-test.js
 */

// import { check, sleep } from 'k6';
// import { Rate, Trend } from 'k6/metrics';

export const options = {
  scenarios: {
    // Smoke test - verify basic functionality
    smoke: {
      executor: 'constant-vus',
      vus: 1,
      duration: '30s',
      tags: { test_type: 'smoke' },
    },
    // Load test - normal expected load
    load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 20 },
        { duration: '5m', target: 20 },
        { duration: '2m', target: 0 },
      ],
      tags: { test_type: 'load' },
    },
    // Stress test - find breaking point
    stress: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: 50 },
        { duration: '5m', target: 50 },
        { duration: '2m', target: 0 },
      ],
      tags: { test_type: 'stress' },
    },
    // Spike test - sudden increase
    spike: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 5 },
        { duration: '1m', target: 50 },
        { duration: '30s', target: 5 },
      ],
      tags: { test_type: 'spike' },
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests under 500ms
    http_req_failed: ['rate<0.05'], // Less than 5% error rate
    health_check_duration: ['p(95)<100'],
    upload_duration: ['p(95)<2000'],
    conversion_duration: ['p(95)<30000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';

// Test configuration
const CONFIG = {
  // Test user credentials
  testEmail: __ENV.TEST_EMAIL || 'test@example.com',
  testPassword: __ENV.TEST_PASSWORD || 'testpassword123',
  // File upload settings
  testFileSizeKB: parseInt(__ENV.TEST_FILE_SIZE_KB) || 100,
};

export default function () {
  // Health check
  const healthRes = http.get(`${BASE_URL}/api/v1/health`);
  check(healthRes, {
    'health check status is 200': (r) => r.status === 200,
    'health check has status field': (r) => r.json('status') !== undefined,
  });

  // Rate limit headers check
  check(healthRes, {
    'rate limit headers present': (r) =>
      r.headers['X-RateLimit-Limit'] !== undefined ||
      r.headers['X-RateLimit-Remaining'] !== undefined,
  });

  // Metrics endpoint
  const metricsRes = http.get(`${BASE_URL}/api/v1/metrics`);
  check(metricsRes, {
    'metrics status is 200': (r) => r.status === 200,
  });

  // Occasional file upload test
  if (__ITER % 5 === 0) {
    const testData = generateTestFile();
    const uploadRes = http.post(`${BASE_URL}/api/v1/upload`, testData, {
      headers: {
        'Content-Type': 'application/java-archive',
        'X-File-Name': 'test_mod.jar',
      },
    });
    check(uploadRes, {
      'upload status is 200 or 201': (r) => r.status === 200 || r.status === 201,
      'upload returns file_id': (r) => r.json('file_id') !== undefined,
    });
  }

  // Occasional conversion test
  if (__VU % 3 === 0) {
    const convertRes = http.post(
      `${BASE_URL}/api/v1/convert`,
      JSON.stringify({
        file_url: `${BASE_URL}/api/v1/test-file.jar`,
        conversion_type: 'java_to_bedrock',
        options: {
          preserve_entities: true,
          convert_recipes: true,
        },
      }),
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
    check(convertRes, {
      'conversion create status is 200 or 202': (r) => r.status === 200 || r.status === 202,
      'conversion returns job_id': (r) => r.json('job_id') !== undefined,
    });
  }
}

function generateTestFile() {
  // Generate minimal JAR-like content
  const jarHeader = [0x50, 0x4b, 0x03, 0x04]; // PK\x04\x04
  const size = CONFIG.testFileSizeKB * 1024;
  const buffer = new Uint8Array(size);
  // Add JAR header
  for (let i = 0; i < 4; i++) {
    buffer[i] = jarHeader[i];
  }
  // Fill rest with zeros
  for (let i = 4; i < size; i++) {
    buffer[i] = 0;
  }
  return buffer;
}

export function setup() {
  console.log(`Starting load test against ${BASE_URL}`);
  const healthRes = http.get(`${BASE_URL}/api/v1/health`);
  if (healthRes.status !== 200) {
    throw new Error(`API health check failed: ${healthRes.status}`);
  }
  return { startTime: Date.now() };
}

export function teardown(data) {
  console.log(`Load test completed. Duration: ${Date.now() - data.startTime}ms`);
}
