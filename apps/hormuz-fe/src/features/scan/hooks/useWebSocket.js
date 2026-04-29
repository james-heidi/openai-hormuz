import { useEffect, useRef, useState, useCallback } from 'react';
import { createMockServer } from '../lib/mockServer';

/**
 * Wraps a WebSocket connection with reconnection and a mock fallback.
 *
 * Mock mode kicks in when:
 *   - `mock === true` (caller forced it), OR
 *   - no `url` is configured, OR
 *   - all real-WS retries have been exhausted.
 *
 * The mock and the real connection use the same wire protocol so the rest
 * of the app doesn't care which is active.
 */

const BACKOFF_MS = [1000, 2000, 4000, 8000, 8000];
const MAX_RETRIES = BACKOFF_MS.length;

const STATUS = Object.freeze({
  CONNECTING: 'connecting',
  OPEN: 'open',
  CLOSED: 'closed',
  MOCK: 'mock',
});

export function useWebSocket({
  url,
  onMessage,
  enabled = true,
  mock = false,
  mockFactory = createMockServer,
}) {
  const [status, setStatus] = useState(
    mock || !url ? STATUS.MOCK : STATUS.CONNECTING,
  );
  const [retryCount, setRetryCount] = useState(0);

  const wsRef = useRef(null);
  const mockRef = useRef(null);
  const retryTimerRef = useRef(null);
  const onMessageRef = useRef(onMessage);
  const mockFactoryRef = useRef(mockFactory);
  const fellBackRef = useRef(false);

  // Keep latest callback without re-running the connect effect.
  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  useEffect(() => {
    mockFactoryRef.current = mockFactory;
  }, [mockFactory]);

  const ensureMock = useCallback(() => {
    if (!mockRef.current) {
      const m = (mockFactoryRef.current ?? createMockServer)();
      m.subscribe((msg) => onMessageRef.current?.(msg));
      mockRef.current = m;
    }
    setStatus(STATUS.MOCK);
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;

    const useMockNow = mock || !url;
    if (useMockNow) {
      fellBackRef.current = true;
      ensureMock();
      return () => {
        mockRef.current?.close();
        mockRef.current = null;
      };
    }

    let cancelled = false;
    let attempt = 0;

    const connect = () => {
      if (cancelled) return;
      setStatus(STATUS.CONNECTING);
      let ws;
      try {
        ws = new WebSocket(url);
      } catch (err) {
        console.warn('[useWebSocket] constructor threw', err);
        scheduleRetry();
        return;
      }
      wsRef.current = ws;

      ws.addEventListener('open', () => {
        if (cancelled) return;
        attempt = 0;
        setRetryCount(0);
        setStatus(STATUS.OPEN);
      });

      ws.addEventListener('message', (ev) => {
        if (cancelled) return;
        try {
          const msg = JSON.parse(ev.data);
          onMessageRef.current?.(msg);
        } catch (err) {
          console.warn('[useWebSocket] non-JSON message dropped', err);
        }
      });

      ws.addEventListener('close', () => {
        if (cancelled) return;
        wsRef.current = null;
        setStatus(STATUS.CLOSED);
        scheduleRetry();
      });

      ws.addEventListener('error', () => {
        // `close` will follow; let it drive the retry.
      });
    };

    const scheduleRetry = () => {
      if (cancelled) return;
      if (attempt >= MAX_RETRIES) {
        fellBackRef.current = true;
        ensureMock();
        return;
      }
      const delay = BACKOFF_MS[attempt];
      attempt += 1;
      setRetryCount(attempt);
      retryTimerRef.current = setTimeout(connect, delay);
    };

    connect();

    return () => {
      cancelled = true;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (wsRef.current) {
        try {
          wsRef.current.close();
        } catch {
          /* ignore */
        }
        wsRef.current = null;
      }
      if (mockRef.current) {
        mockRef.current.close();
        mockRef.current = null;
      }
    };
  }, [url, enabled, mock, ensureMock]);

  const send = useCallback((msg) => {
    if (mockRef.current) {
      mockRef.current.send(msg);
      return;
    }
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('[useWebSocket] send() while not open; dropping', msg?.type);
      return;
    }
    ws.send(JSON.stringify(msg));
  }, []);

  return { status, retryCount, send, maxRetries: MAX_RETRIES };
}

export const WS_STATUS = STATUS;
