import { Injectable, signal } from '@angular/core';
import * as L from 'leaflet';
// Importar el JS directo del paquete fuerza la ejecución del side-effect
// (extiende L con markerClusterGroup). El import 'leaflet.markercluster' suelto
// puede ser eliminado por tree-shaking en build de producción.
import 'leaflet.markercluster/dist/leaflet.markercluster.js';
import { Subject } from 'rxjs';

import {
  CENTER_CALLAO,
  CLUSTER_RADIUS,
  TILE_ATTRIBUTION,
  TILE_URL,
  ZOOM_DEFAULT,
  ZOOM_MAX,
  ZOOM_MIN,
} from '../config/map.config';
import type { FiltroChip } from '../models/filtros.model';
import type { Obra, Tramo } from '../models/obra.model';
import { makeIcon } from '../../features/mapa/utils/marker-factory';
import { popupHtml } from '../../features/mapa/utils/popup-html';

@Injectable({ providedIn: 'root' })
export class MapService {
  private map: L.Map | null = null;
  private clusterGroup: L.MarkerClusterGroup | null = null;
  private readonly markersById = new Map<number, L.Marker>();
  private readonly obrasById = new Map<number, Obra>();
  private selectedId: number | null = null;
  private filterChip: FiltroChip = 'todas';

  readonly clickedId$ = new Subject<number>();
  readonly initialized = signal(false);

  init(host: HTMLElement): void {
    if (this.map) return;

    this.map = L.map(host, {
      center: CENTER_CALLAO,
      zoom: ZOOM_DEFAULT,
      minZoom: ZOOM_MIN,
      maxZoom: ZOOM_MAX,
      zoomControl: false,
      attributionControl: true,
    });

    L.tileLayer(TILE_URL, {
      attribution: TILE_ATTRIBUTION,
      maxZoom: ZOOM_MAX,
    }).addTo(this.map);

    this.clusterGroup = L.markerClusterGroup({
      maxClusterRadius: CLUSTER_RADIUS,
      iconCreateFunction: (cluster) => this.createClusterIcon(cluster.getChildCount()),
    });
    this.map.addLayer(this.clusterGroup);

    this.map.on('zoomend moveend layeradd', () => {
      requestAnimationFrame(() => this.applyMarkerSelection());
    });

    this.initialized.set(true);
  }

  destroy(): void {
    if (!this.map) return;
    this.initialized.set(false);
    this.map.off();
    this.map.remove();
    this.map = null;
    this.clusterGroup = null;
    this.markersById.clear();
    this.obrasById.clear();
    this.selectedId = null;
    this.userMarker = null;
    this.radiusCircle = null;
  }

  syncObras(obras: Obra[]): void {
    if (!this.clusterGroup) return;
    this.clusterGroup.clearLayers();
    this.markersById.clear();
    this.obrasById.clear();

    for (const obra of obras) {
      this.obrasById.set(obra.id, obra);

      const marker = L.marker(obra.coords, { icon: makeIcon(obra.estado, obra.titulo) });
      marker.bindPopup(popupHtml(obra), { maxWidth: 280, closeButton: false });
      marker.on('click', () => this.clickedId$.next(obra.id));
      this.markersById.set(obra.id, marker);
    }

    this.applyFilterInternal();
  }

  applyFilter(chip: FiltroChip): void {
    this.filterChip = chip;
    this.applyFilterInternal();
  }

  applySelected(id: number | null): void {
    this.selectedId = id;
    this.applyMarkerSelection();
    this.applyCircleSelection();
  }

  syncTramos(tramos: Tramo[]): void {
    // Fase 4.6: no renderizar overlays SVG en el mapa base.
    // El demo fuente usado para la paridad visual muestra solo markers.
    void tramos;
  }

  flyToCallao(): void {
    this.map?.flyTo(CENTER_CALLAO, ZOOM_DEFAULT, { duration: 1.2 });
  }

  flyTo(lat: number, lon: number, zoom?: number): void {
    this.map?.flyTo([lat, lon], zoom ?? ZOOM_DEFAULT, { duration: 1.0 });
  }

  private userMarker: L.CircleMarker | null = null;
  private radiusCircle: L.Circle | null = null;

  syncRadiusCircle(lat: number, lon: number, radiusM: number): void {
    if (!this.map) return;
    if (this.radiusCircle) {
      this.radiusCircle.setLatLng([lat, lon]);
      this.radiusCircle.setRadius(radiusM);
    } else {
      this.radiusCircle = L.circle([lat, lon], {
        radius: radiusM,
        color: '#0369A1',
        weight: 1.5,
        opacity: 0.55,
        fillOpacity: 0,
        dashArray: '5 5',
        interactive: false,
      }).addTo(this.map);
    }
  }

  removeRadiusCircle(): void {
    this.radiusCircle?.remove();
    this.radiusCircle = null;
  }

  addUserMarker(lat: number, lon: number): void {
    if (!this.map) return;
    if (this.userMarker) {
      this.userMarker.setLatLng([lat, lon]);
      return;
    }
    this.userMarker = L.circleMarker([lat, lon], {
      radius: 9,
      className: 'user-location-marker',
      interactive: false,
    }).addTo(this.map);
  }

  removeUserMarker(): void {
    this.userMarker?.remove();
    this.userMarker = null;
  }

  zoomIn(): void {
    this.map?.zoomIn();
  }

  zoomOut(): void {
    this.map?.zoomOut();
  }

  private applyFilterInternal(): void {
    if (!this.clusterGroup) return;
    this.clusterGroup.clearLayers();
    for (const [id, obra] of this.obrasById) {
      if (!this.matchesFilter(obra)) continue;
      const marker = this.markersById.get(id);
      if (marker) this.clusterGroup.addLayer(marker);
    }
    this.applyMarkerSelection();
  }

  private matchesFilter(obra: Obra): boolean {
    const chip = this.filterChip;
    if (chip === 'todas') return true;
    if (chip === 'con_senal') return obra.conSenal;
    return obra.estado === chip;
  }

  private applyMarkerSelection(): void {
    this.markersById.forEach((marker, id) => {
      const el = marker.getElement();
      const pin = el?.querySelector('.marker-pin');
      pin?.classList.toggle('is-selected', id === this.selectedId);
    });
  }

  private applyCircleSelection(): void {
    // Fase 4.6: no renderizar circles/radios de impacto.
    // La selección se expresa solo con la clase `.marker-pin.is-selected`.
  }

  private createClusterIcon(count: number): L.DivIcon {
    const size = count < 10 ? 40 : count < 30 ? 52 : 64;
    return L.divIcon({
      className: '',
      html: `<div style="width:${size}px;height:${size}px;border-radius:50%;background:#374151;color:var(--surface);font-family:var(--font-sans);font-size:${count > 9 ? 13 : 14}px;font-weight:700;border:2.5px solid var(--surface-raised);display:flex;align-items:center;justify-content:center;box-shadow:0 2px 8px rgba(0,0,0,0.28);">${count}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }
}
