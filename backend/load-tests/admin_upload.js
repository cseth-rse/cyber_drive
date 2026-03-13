// load-tests/admin_upload.js
// Cyber Drive — k6 load test: admin document upload stress test.
// Tests the upload pipeline (ClamAV scan queue) under concurrent load.
//
// Requires:
//   A real PDF file at /tmp/test.pdf (any small valid PDF)
//   An ADMIN access token
//
// Run:
//   k6 run -e BASE_URL=http://localhost:3000 \
//           -e ACCESS_TOKEN=your_admin_token \
//           -e COURSE_ID=your_course_uuid \
//           -e LEVEL_ID=1 \
//           load-tests/admin_upload.js

import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { FormData } from 'https://jslib.k6.io/formdata/0.0.2/index.js';
import { randomString } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

const BASE_URL    = __ENV.BASE_URL    || 'http://localhost:3000';
const TOKEN       = __ENV.ACCESS_TOKEN || 'REPLACE_WITH_ADMIN_TOKEN';
const COURSE_ID   = __ENV.COURSE_ID   || 'REPLACE_WITH_COURSE_UUID';
const LEVEL_ID    = __ENV.LEVEL_ID    || '1';

const uploadErrors = new Rate('upload_errors');
const uploadLatency = new Trend('upload_latency_ms', true);
const totalUploads = new Counter('total_uploads');

// Small valid 1-byte PDF-like payload for testing
// (In a real test, replace with an actual binary PDF read via open())
const FAKE_PDF = new Uint8Array([0x25, 0x50, 0x44, 0x46, 0x2d, 0x31, 0x2e, 0x34]);

export const options = {
  scenarios: {
    // Ramp-up: 0 → 20 concurrent uploaders over 1 minute
    ramp_up: {
      executor: 'ramping-vus',
      stages: [
        { duration: '30s', target: 5  },
        { duration: '1m',  target: 20 },
        { duration: '30s', target: 0  },
      ],
    },
  },
  thresholds: {
    http_req_duration:    ['p(95)<5000'],  // uploads can be slower
    http_req_failed:      ['rate<0.05'],   // 5% error tolerance (ClamAV may reject)
    upload_errors:        ['rate<0.05'],
  },
};

export default function () {
  const fd = new FormData();
  fd.append('title', `Load Test Doc ${randomString(8)}`);
  fd.append('course_id', COURSE_ID);
  fd.append('level_id', LEVEL_ID);
  fd.append('description', 'Automated load test upload');
  fd.append('file', http.file(FAKE_PDF, 'test.pdf', 'application/pdf'));

  const start = Date.now();
  const res = http.post(`${BASE_URL}/documents/upload`, fd.body(), {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      'Content-Type': `multipart/form-data; boundary=${fd.boundary}`,
    },
    timeout: '30s',
  });

  const elapsed = Date.now() - start;
  uploadLatency.add(elapsed);
  totalUploads.add(1);

  const ok = check(res, {
    'upload accepted (201 or 409 duplicate)': (r) => [201, 409].includes(r.status),
    'not rate limited': (r) => r.status !== 429,
  });

  uploadErrors.add(!ok && res.status !== 409);  // 409 duplicate is not a real error

  sleep(2);  // realistic think time between uploads
}

export function handleSummary(data) {
  console.log('\n=== Upload Stress Test Summary ===');
  console.log(`Total uploads attempted : ${data.metrics.total_uploads?.values?.count ?? 0}`);
  console.log(`Upload error rate       : ${(data.metrics.upload_errors?.values?.rate ?? 0) * 100}%`);
  console.log(`Upload P95 latency      : ${data.metrics.upload_latency_ms?.values?.['p(95)'] ?? 0}ms`);

  return {
    'load-tests/results/upload-summary.json': JSON.stringify(data, null, 2),
  };
}
