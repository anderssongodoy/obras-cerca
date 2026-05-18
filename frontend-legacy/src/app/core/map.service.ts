import { Injectable, signal } from '@angular/core';
import { Subject } from 'rxjs';
import { ObraResumen } from './models';

declare const L: any;

@Injectable({ providedIn: 'root' })
export class MapService {
  private map: any = null;
  private clusterGroup: any = null;
  private markersById = new Map<number, any>();
  private obrasById = new Map<number, ObraResumen>();
  private selectedId: number | null = null;

  readonly clickedId$ = new Subject<number>();
  readonly initialized = signal(false);

  init(host: HTMLElement): void {
    if (this.map) return;

    this.map = L.map(host, {
      center: [-12.05, -77.03],
      zoom: 11,
      minZoom: 9,
      maxZoom: 19,
      zoomControl: false,
      attributionControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(this.map);

    this.clusterGroup = L.markerClusterGroup({
      maxClusterRadius: 50,
      iconCreateFunction: (cluster: any) => this.clusterIcon(cluster.getChildCount()),
    });
    this.map.addLayer(this.clusterGroup);

    this.map.on('click', () => this.clickedId$.next(-1));

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
  }

  syncObras(obras: ObraResumen[]): void {
    if (!this.clusterGroup) return;
    this.clusterGroup.clearLayers();
    this.markersById.clear();
    this.obrasById.clear();

    for (const o of obras) {
      if (o.latitud == null || o.longitud == null) continue;
      this.obrasById.set(o.id, o);

      const critico = this.esCritica(o);
      const marker = L.marker([Number(o.latitud), Number(o.longitud)], {
        icon: this.pinIcon(critico, o.id === this.selectedId),
      });
      marker.on('click', (e: any) => {
        L.DomEvent.stopPropagation(e);
        this.clickedId$.next(o.id);
      });
      this.markersById.set(o.id, marker);
      this.clusterGroup.addLayer(marker);
    }
  }

  applySelected(id: number | null): void {
    this.selectedId = id;
    this.markersById.forEach((marker, mid) => {
      const obra = this.obrasById.get(mid);
      if (!obra) return;
      marker.setIcon(this.pinIcon(this.esCritica(obra), mid === id));
    });
    if (id != null) {
      const obra = this.obrasById.get(id);
      if (obra && obra.latitud != null && obra.longitud != null) {
        this.map?.panTo([Number(obra.latitud), Number(obra.longitud)], { animate: true });
      }
    }
  }

  zoomIn(): void { this.map?.zoomIn(); }
  zoomOut(): void { this.map?.zoomOut(); }
  recenter(): void { this.map?.flyTo([-12.05, -77.03], 11, { duration: 1.0 }); }

  private esCritica(o: ObraResumen): boolean {
    if (o.estado_obra_wfs === 'Paralizada') return true;
    const mef = (o.estado_proyecto_mef || '').toUpperCase();
    return mef.includes('DESACTIVA');
  }

  private pinIcon(critico: boolean, selected: boolean): any {
    const color = critico ? '#9f5442' : '#78716c';
    const ring = selected ? '#1c1917' : '#fafaf9';
    const size = selected ? 22 : 18;
    const html = `
      <div style="
        width:${size}px;height:${size}px;border-radius:50%;
        background:${color};
        border:2.5px solid ${ring};
        box-shadow:0 2px 6px rgba(0,0,0,0.28);
        transition:width 0.15s,height 0.15s;
      "></div>`;
    return L.divIcon({
      className: 'obra-pin',
      html,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }

  private clusterIcon(count: number): any {
    const size = count < 10 ? 38 : count < 30 ? 48 : 60;
    const html = `
      <div style="
        width:${size}px;height:${size}px;border-radius:50%;
        background:#1c1917;color:#fafaf9;
        font-family:Inter,sans-serif;font-size:13px;font-weight:700;
        border:2.5px solid #fafaf9;
        display:flex;align-items:center;justify-content:center;
        box-shadow:0 2px 8px rgba(0,0,0,0.32);
      ">${count}</div>`;
    return L.divIcon({
      className: 'obra-cluster',
      html,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    });
  }
}
