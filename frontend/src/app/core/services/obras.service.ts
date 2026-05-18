import { Injectable, computed, inject, signal } from '@angular/core';
import { httpResource } from '@angular/common/http';

import { API_BASE_URL } from '../config/api.config';
import { UBIGEO_CALLAO_DEFAULT } from '../config/map.config';
import type { Obra, ObraApi, ObrasListResponse } from '../models/obra.model';
import {
  derivarEstado,
  derivarFuente,
  formatoMonto,
} from '../../features/mapa/utils/estado-catalog';
import { SenalesService } from './senales.service';

@Injectable({ providedIn: 'root' })
export class ObrasService {
  private readonly apiBase = inject(API_BASE_URL);
  private readonly senales = inject(SenalesService);

  // Filtros server-side — se exponen como signals editables para que la UI escriba aquí.
  readonly ubigeo = signal<string | null>(UBIGEO_CALLAO_DEFAULT);
  readonly userLat = signal<number | null>(null);
  readonly userLon = signal<number | null>(null);
  readonly radioM = signal<number>(50000); // 50 km — cubre Lima Metropolitana + Callao
  readonly busqueda = signal<string>('');
  readonly limit = signal<number>(200);

  readonly resource = httpResource<ObrasListResponse>(() => {
    const lat = this.userLat();
    const lon = this.userLon();
    const hasCoords = lat !== null && lon !== null;
    return {
      url: `${this.apiBase}/api/obras`,
      params: {
        // Si tenemos coords del usuario, usamos proximidad. Si no, ubigeo como fallback.
        ...(hasCoords
          ? { lat, lon, radio_m: this.radioM() }
          : this.ubigeo() ? { ubigeo: this.ubigeo() as string } : {}),
        ...(this.busqueda().trim() ? { q: this.busqueda().trim() } : {}),
        limit: this.limit(),
      },
    };
  });

  // Lista normalizada al shape del demo — cruza ObraApi[] con el Set de señales.
  // Filtra obras sin nombre real (sin nombre_obra ni nombre_inversion).
  readonly obras = computed<Obra[]>(() => {
    const resp = this.resource.value();
    if (!resp) return [];
    const senales = this.senales.obrasConSenal();
    return resp.items
      .filter(tieneCoords)
      .filter(tieneNombre)
      .map((api) => mapApiToObra(api, senales.has(api.id)));
  });

  readonly total = computed(() => this.resource.value()?.total ?? 0);
  readonly isLoading = this.resource.isLoading;
  readonly error = this.resource.error;

  reload(): void {
    this.resource.reload();
  }
}

function tieneCoords(o: ObraApi): boolean {
  return o.latitud != null && o.longitud != null && !isNaN(Number(o.latitud)) && !isNaN(Number(o.longitud));
}

function tieneNombre(o: ObraApi): boolean {
  const n = (o.nombre_obra || o.nombre_inversion || '').trim();
  if (n.length === 0 || n === '—') return false;
  // Rechazar nombres placeholder tipo "(pendiente)" que vienen de obras nuevas sin enriquecer
  const lower = n.toLowerCase();
  if (lower === '(pendiente)' || lower === 'pendiente') return false;
  if (lower.startsWith('(pendiente')) return false;
  return true;
}

function mapApiToObra(api: ObraApi, conSenal: boolean): Obra {
  const monto = formatoMonto(api);
  return {
    id: api.id,
    titulo: api.nombre_obra ?? api.nombre_inversion ?? `Obra #${api.id}`,
    estado: derivarEstado(api, conSenal),
    montoNumerico: monto.numerico,
    montoLabel: monto.label,
    entidad: api.entidad_nombre ?? 'Sin entidad',
    distrito: api.distrito_nombre ?? 'Sin distrito',
    coords: [Number(api.latitud), Number(api.longitud)],
    conSenal,
    fuente: derivarFuente(api, false),
    urlInfobras: api.url_infobras_ficha,
    urlMef: api.url_mef_ssi,
    nobrId: api.nobr_id,
    cui: api.cui,
  };
}
