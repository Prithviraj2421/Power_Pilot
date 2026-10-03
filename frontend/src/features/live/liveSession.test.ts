import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { captureToken, launchedModel } from './liveSession';

function visit(path: string) {
  window.history.replaceState(null, '', path);
}

describe('captureToken', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });
  afterEach(() => {
    visit('/');
  });

  it('reads the token from the URL fragment and removes it from the address bar', () => {
    visit('/live?server=localhost%3A51234&db=abc#token=s3cr%2Bet%3D');

    expect(captureToken()).toBe('s3cr+et=');
    expect(window.location.hash).toBe('');
    expect(window.location.pathname + window.location.search).toBe('/live?server=localhost%3A51234&db=abc');
  });

  it('keeps working after a reload, when the fragment is gone', () => {
    visit('/live#token=abc123');
    captureToken();
    visit('/live');

    expect(captureToken()).toBe('abc123');
  });

  it('never reads a token from the query string, where it could be logged', () => {
    visit('/live?token=leaked');

    expect(captureToken()).toBeNull();
  });

  it('returns null when launched without a token', () => {
    visit('/live');

    expect(captureToken()).toBeNull();
  });
});

describe('launchedModel', () => {
  it('reads the model the launcher attached, for display only', () => {
    visit('/live?server=localhost%3A51234&db=%7BGUID%7D');

    expect(launchedModel()).toEqual({ server: 'localhost:51234', database: '{GUID}' });
    visit('/');
  });
});
