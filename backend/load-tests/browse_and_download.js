// load-tests/browse_and_download.js
// Cyber Drive — k6 load test: browse levels, list documents, download
//
// Install k6: https://k6.io/docs/getting-started/installation
// Run:
//   k6 run --vus 100 --duration 2m load-tests/browse_and_download.js
//   k6 run --stage 0:0,30s:100,2m:100,30s:0 load-tests/browse_and_download.js

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';

// Custom metrics
const errorRate = new Rate('errors');
const downloadLatency = new Trend('download_latency', true);

// Ramping load profile (adjust to your target)
export const options = {
  stages: [
    { duration: '30s', target: 50   },  // ramp up
    { duration: '1m',  target: 100  },  // stay at 100 VUs
    { duration: '1m',  target: 250  },  // stress
    { duration: '30s', target: 500  },  // spike
    { duration: '30s', target: 0    },  // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],  // 95th < 1s, 99th < 2s
    http_req_failed:   ['rate<0.01'],                  // <1% errors
    errors:            ['rate<0.01'],
  },
};

// Shared auth token (replace with a real student token for your test env)
const ACCESS_TOKEN = __ENV.ACCESS_TOKEN || 'REPLACE_WITH_STUDENT_TOKEN';
const HEADERS = {
  Authorization: `Bearer ${ACCESS_TOKEN}`,
  'Content-Type': 'application/json',
};

export default function () {
  group('Browse levels', () => {
    const res = http.get(`${BASE_URL}/levels`, { headers: HEADERS });
    const ok = check(res, {
      'levels status 200': (r) => r.status === 200,
      'levels has items': (r) => {
        try { return JSON.parse(r.body).length > 0; } catch { return false; }
      },
    });
    errorRate.add(!ok);
  });

  sleep(0.5);

  group('List documents', () => {
    const res = http.get(`${BASE_URL}/documents?page=1&limit=20`, { headers: HEADERS });
    const ok = check(res, {
      'list status 200': (r) => r.status === 200,
    });
    errorRate.add(!ok);
  });

  sleep(0.5);

  group('Get document detail', () => {
    // Use a real doc ID from your test data, or derive from list response
    const docId = __ENV.SAMPLE_DOC_ID || 'REPLACE_WITH_REAL_DOC_ID';
    const res = http.get(`${BASE_URL}/documents/${docId}`, { headers: HEADERS });
    const ok = check(res, {
      'detail status 200 or 404': (r) => [200, 404].includes(r.status),
    });
    errorRate.add(!ok);
  });

  sleep(0.5);

  group('View document (presigned redirect)', () => {
    const docId = __ENV.SAMPLE_DOC_ID || 'REPLACE_WITH_REAL_DOC_ID';
    const start = Date.now();
    const res = http.get(`${BASE_URL}/documents/${docId}/view`, {
      headers: HEADERS,
      redirects: 0,  // don't follow S3 redirect — measure API latency only
    });
    downloadLatency.add(Date.now() - start);
    const ok = check(res, {
      'view redirects to S3 (307) or returns PDF (200)': (r) =>
        [200, 307, 404].includes(r.status),
    });
    errorRate.add(!ok);
  });

  sleep(1);
}
