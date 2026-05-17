import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { Obra, Senal, MOCK_OBRAS } from '../mock/mock-obras';
import { MOCK_SENALES } from '../mock/mock-senales';
import { MOCK_STATS } from '../mock/mock-stats';
import { MOCK_DISTRITOS } from '../mock/mock-distritos';

@Injectable({ providedIn: 'root' })
export class ObrasService {

  getStats(): Observable<any> {
    return of(MOCK_STATS);
  }

  getDistritosResumen(): Observable<any[]> {
    return of(MOCK_DISTRITOS);
  }

  getObras(filtros: {
    paralizadas?: boolean;
    clasificacion?: string;
    ubigeo?: string;
    q?: string;
  } = {}): Observable<{ total: number; items: Obra[] }> {
    let items = [...MOCK_OBRAS];
    if (filtros.paralizadas === true)  items = items.filter(o => o.existe_paralizacion);
    if (filtros.paralizadas === false) items = items.filter(o => !o.existe_paralizacion);
    if (filtros.clasificacion) items = items.filter(o => o.clasificacion_paralizacion === filtros.clasificacion);
    if (filtros.ubigeo)        items = items.filter(o => o.distrito_ubigeo === filtros.ubigeo);
    if (filtros.q)             items = items.filter(o => o.nombre.toLowerCase().includes(filtros.q!.toLowerCase()));
    return of({ total: items.length, items });
  }

  getObra(id: number): Observable<Obra | undefined> {
    return of(MOCK_OBRAS.find(o => o.id === id));
  }

  getSenales(filtros: { tipo?: string; solo_confirmadas?: boolean } = {}): Observable<Senal[]> {
    let items = [...MOCK_SENALES];
    if (filtros.tipo)             items = items.filter(s => s.tipo === filtros.tipo);
    if (filtros.solo_confirmadas) items = items.filter(s => s.confirmada_contraloria_2025);
    return of(items.sort((a, b) => b.score - a.score));
  }
}
