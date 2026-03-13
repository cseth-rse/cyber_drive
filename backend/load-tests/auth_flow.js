// load-tests/auth_flow.js
// Cyber Drive — k6 load test: register → (manual OTP step) → verify
// Stress tests the auth rate limiting.
//
// Run: k6 run --vus 20 --duration 1m load-tests/auth_flow.js

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:3000';
const errorRate = new Rate('errors');

export const options = {
  vus: 20,
  duration: '1m',
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed:   ['rate<0.05'],
  },
};

export default function () {
  // Register (sends OTP) — rate-limited to 10/min per IP
  const email = `loadtest_${__VU}_${Date.now()}@test.cyber`;
  const registerRes = http.post(
    `${BASE_URL}/auth/register`,
    JSON.stringify({ email }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  const ok = check(registerRes, {
    'register 200 or 429 (rate limited)': (r) => [200, 429].includes(r.status),
  });
  errorRate.add(!ok);

  sleep(2);

  // Verify OTP — deliberately wrong code to test rejection rate
  const verifyRes = http.post(
    `${BASE_URL}/auth/verify-otp`,
    JSON.stringify({ email, otp: '000000' }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  check(verifyRes, {
    'bad OTP returns 401 or 429': (r) => [401, 400, 429].includes(r.status),
  });

  sleep(1);
}
