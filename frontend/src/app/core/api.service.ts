import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import {
  Distrito, ObraFicha, ObraListResponse, Senal, Stats, ContratistaFicha,
  VerificacionLive
} from './models';

// Detecta automáticamente la URL base del API según dónde se sirve el frontend:
//   - Si corremos en localhost (dev): backend en http://localhost:8000
//   - Si corremos en cualquier otro host (prod, Vercel, preview): backend en api.<host>
// Se puede sobrescribir vía window.__API_BASE__ si hace falta.
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

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = resolveApiBase();

  stats(): Observable<Stats> {
    return this.http.get<Stats>(`${this.base}/api/stats`);
  }

  distritos(): Observable<Distrito[]> {
    return this.http.get<Distrito[]>(`${this.base}/api/distritos`);
  }

  resumenDistritos(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/distritos/resumen`);
  }

  obras(params: Record<string, any> = {}): Observable<ObraListResponse> {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
    }
    return this.http.get<ObraListResponse>(`${this.base}/api/obras?${qs}`);
  }

  obra(id: number): Observable<ObraFicha> {
    return this.http.get<ObraFicha>(`${this.base}/api/obras/${id}`);
  }

  verificarLive(id: number): Observable<VerificacionLive> {
    return this.http.get<VerificacionLive>(`${this.base}/api/obras/${id}/verificar`);
  }

  explicacion(id: number, refresh = false): Observable<any> {
    return this.http.get(`${this.base}/api/obras/${id}/explicacion?refresh=${refresh}`);
  }

  contratista(ruc: string): Observable<ContratistaFicha> {
    return this.http.get<ContratistaFicha>(`${this.base}/api/contratistas/${ruc}`);
  }

  contratistasSospechosos(): Observable<any[]> {
    return this.http.get<any[]>(`${this.base}/api/contratistas/sospechosos/top`);
  }

  senales(params: Record<string, any> = {}): Observable<Senal[]> {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') qs.set(k, String(v));
    }
    return this.http.get<Senal[]>(`${this.base}/api/senales?${qs}`);
  }
}
