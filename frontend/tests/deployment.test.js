import test from 'node:test';
import assert from 'node:assert/strict';
import axios from 'axios';
import { API_TIMEOUT_MS, apiErrorMessage, normalizeApiBaseUrl } from '../src/api/apiConfig.js';
import { startResultPolling } from '../src/utils/resultPolling.js';

function clock() {
  const jobs = new Map();
  let id = 0;
  return {
    jobs,
    schedule(callback, delay) {
      assert.equal(delay, 2000);
      jobs.set(++id, callback);
      return id;
    },
    cancel(timer) { jobs.delete(timer); },
    next() {
      const [key, callback] = jobs.entries().next().value;
      jobs.delete(key);
      return callback();
    },
  };
}

test('API URLs join production and local paths correctly', () => {
  for (const [value, expected] of [
    [' https://api.onrender.com/// ', 'https://api.onrender.com/upload'],
    [undefined, '/api/upload'], ['', '/api/upload'], ['/api/', '/api/upload'],
  ]) {
    const client = axios.create({ baseURL: normalizeApiBaseUrl(value) });
    assert.equal(client.getUri({ url: '/upload' }), expected);
  }
  assert.equal(API_TIMEOUT_MS, 120000);
});

test('cold-start and network failures have actionable messages', () => {
  assert.match(apiErrorMessage({ code: 'ECONNABORTED' }), /waking up/);
  assert.match(apiErrorMessage({ code: 'ERR_NETWORK' }), /Cannot reach the backend/);
  assert.equal(apiErrorMessage({ response: { data: { detail: 'Only PDFs allowed' } } }), 'Only PDFs allowed');
});

test('slow requests never overlap and terminal results stop polling', async () => {
  const timers = clock();
  let resolve;
  let calls = 0;
  const stop = startResultPolling(() => {
    calls++;
    return new Promise(done => { resolve = done; });
  }, data => data.status !== 'completed', assert.fail, timers);
  const pending = timers.next();
  assert.equal(calls, 1);
  assert.equal(timers.jobs.size, 0);
  resolve({ status: 'processing' });
  await pending;
  assert.equal(timers.jobs.size, 1);
  const final = timers.next();
  resolve({ status: 'completed' });
  await final;
  assert.equal(calls, 2);
  assert.equal(timers.jobs.size, 0);
  stop();
});

test('reset/unmount aborts a pending request and ignores its result', async () => {
  const timers = clock();
  let resolve;
  let signal;
  const stop = startResultPolling(value => {
    signal = value;
    return new Promise(done => { resolve = done; });
  }, () => assert.fail('stale result'), assert.fail, timers);
  const pending = timers.next();
  stop();
  assert.equal(signal.aborted, true);
  resolve({ status: 'completed' });
  await pending;
  assert.equal(timers.jobs.size, 0);
});

test('failed request reports once without an automatic retry loop', async () => {
  const timers = clock();
  let failures = 0;
  startResultPolling(async () => { throw new Error('offline'); }, assert.fail, error => {
    assert.equal(error.message, 'offline');
    failures++;
  }, timers);
  await timers.next();
  assert.equal(failures, 1);
  assert.equal(timers.jobs.size, 0);
});
