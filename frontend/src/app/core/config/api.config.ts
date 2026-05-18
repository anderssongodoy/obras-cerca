import { InjectionToken } from '@angular/core';

/**
 * Resuelve la URL del backend automáticamente según dónde se sirve el frontend:
 *   - localhost / 127.0.0.1 / 192.168.* → http://localhost:8000 (dev)
 *   - cualquier otro host (Vercel, etc.) → https://api.obrascerca.trinitylabs.app (prod)
 *
 * Se puede sobrescribir vía window.__API_BASE__ si hace falta para previews.
 */
function resolveApiBase(): string {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  const override = (window as unknown as { __API_BASE__?: string }).__API_BASE__;
  if (override) return override;
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host.startsWith('192.168.')) {
    return 'http://localhost:8000';
  }
  return 'https://api.obrascerca.trinitylabs.app';
}

export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  providedIn: 'root',
  factory: resolveApiBase,
});
