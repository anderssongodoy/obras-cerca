import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { ObraResumen } from '../core/models';

declare const L: any;

@Component({
  selector: 'app-mapa',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="max-w-6xl mx-auto px-6 py-12">
      <div class="mb-8">
        <h1 class="font-serif text-3xl text-stone-900 mb-3">Obras cerca de ti</h1>
        <p class="text-stone-600 max-w-2xl">
          Encuentra obras públicas en Lima Metropolitana y Callao. Los marcadores
          <span class="text-terracotta">en terracota</span> son obras con señales de revisión.
        </p>
      </div>

      <!-- Controles -->
      <div class="flex flex-wrap gap-3 mb-6 items-center">
        <label class="flex items-center gap-2 text-sm text-stone-700 cursor-pointer">
          <input type="checkbox" [checked]="soloParalizadas()" (change)="toggle('paralizadas')" class="accent-terracotta">
          Solo paralizadas WFS
        </label>
        <label class="flex items-center gap-2 text-sm text-stone-700 cursor-pointer">
          <input type="checkbox" [checked]="soloInactivas()" (change)="toggle('inactivas')" class="accent-terracotta">
          Solo desactivadas MEF
        </label>
        <label class="flex items-center gap-2 text-sm text-stone-700 cursor-pointer">
          <input type="checkbox" [checked]="conSaldos()" (change)="toggle('saldos')" class="accent-terracotta">
          Con saldos de obra
        </label>
        <span class="ml-auto text-sm text-stone-500">{{ obras().length }} obras visibles</span>
      </div>

      <!-- Mapa -->
      <div #map class="relative bg-stone-100 rounded-lg overflow-hidden border border-stone-200" style="height: 60vh;"></div>

      <!-- Leyenda -->
      <div class="mt-3 flex items-center gap-6 text-xs text-stone-600">
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-terracotta rounded-full"></div>
          <span>Con señales de revisión</span>
        </div>
        <div class="flex items-center gap-2">
          <div class="w-3 h-3 bg-stone-400 rounded-full"></div>
          <span>Sin alertas</span>
        </div>
        <div class="ml-auto text-stone-400">Mapa: OpenStreetMap · Leaflet</div>
      </div>

      <!-- Lista debajo del mapa -->
      <section *ngIf="obras().length" class="mt-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">Obras visibles</h2>
        <div class="space-y-4">
          <article *ngFor="let o of obras().slice(0, 12)"
                   class="p-4 bg-white border border-stone-200 rounded hover:border-stone-300 transition-colors cursor-pointer"
                   [routerLink]="['/obra', o.id]">
            <h3 class="font-serif text-lg text-stone-900 mb-1">{{ o.nombre_obra || o.nombre_inversion || '(sin nombre)' }}</h3>
            <p class="text-sm text-stone-600 mb-2">
              {{ o.entidad_nombre || '—' }} · {{ o.distrito_nombre }}
            </p>
            <div class="flex flex-wrap gap-2 text-xs">
              <span class="px-2 py-1 rounded"
                    [class.bg-terracotta]="esCritico(o.estado_proyecto_mef)"
                    [class.text-white]="esCritico(o.estado_proyecto_mef)"
                    [class.bg-stone-100]="!esCritico(o.estado_proyecto_mef)"
                    [class.text-stone-700]="!esCritico(o.estado_proyecto_mef)">
                MEF: {{ o.estado_proyecto_mef }}
              </span>
              <span class="px-2 py-1 rounded"
                    [class.bg-terracotta]="o.estado_obra_wfs === 'Paralizada'"
                    [class.text-white]="o.estado_obra_wfs === 'Paralizada'"
                    [class.bg-stone-100]="o.estado_obra_wfs !== 'Paralizada'"
                    [class.text-stone-700]="o.estado_obra_wfs !== 'Paralizada'">
                WFS: {{ o.estado_obra_wfs || '—' }}
              </span>
            </div>
          </article>
        </div>
      </section>
    </main>
  `,
})
export class MapaComponent implements AfterViewInit, OnDestroy {
  @ViewChild('map', { static: true }) mapEl!: ElementRef;
  private api = inject(ApiService);
  private router = inject(Router);
  private map: any;
  private layer: any;

  obras = signal<ObraResumen[]>([]);
  soloParalizadas = signal(false);
  soloInactivas = signal(false);
  conSaldos = signal(false);

  ngAfterViewInit(): void {
    this.map = L.map(this.mapEl.nativeElement).setView([-12.05, -77.03], 11);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '© OpenStreetMap',
    }).addTo(this.map);
    this.layer = L.layerGroup().addTo(this.map);
    this.recargar();
  }

  ngOnDestroy(): void { if (this.map) this.map.remove(); }

  toggle(k: 'paralizadas' | 'inactivas' | 'saldos') {
    if (k === 'paralizadas') this.soloParalizadas.set(!this.soloParalizadas());
    if (k === 'inactivas') this.soloInactivas.set(!this.soloInactivas());
    if (k === 'saldos') this.conSaldos.set(!this.conSaldos());
    this.recargar();
  }

  recargar() {
    const params: any = { limit: 500 };
    if (this.soloParalizadas()) params.paralizadas_wfs = true;
    if (this.soloInactivas()) params.inactivas_mef = true;
    if (this.conSaldos()) params.con_saldos = true;
    this.api.obras(params).subscribe(res => {
      this.obras.set(res.items);
      this.draw(res.items);
    });
  }

  esCritico(estado: string | null | undefined): boolean {
    if (!estado) return false;
    const u = estado.toUpperCase();
    return u.includes('DESACTIVA') || u.includes('PARALIZ');
  }

  private draw(items: ObraResumen[]) {
    this.layer.clearLayers();
    for (const o of items) {
      if (!o.latitud || !o.longitud) continue;
      const critico = o.estado_obra_wfs === 'Paralizada'
                   || (o.estado_proyecto_mef || '').toUpperCase().includes('DESACTIVA');
      const color = critico ? '#9f5442' : '#a8a29e';
      const m = L.circleMarker([o.latitud, o.longitud], {
        radius: critico ? 8 : 6,
        color,
        fillColor: color,
        fillOpacity: 0.75,
        weight: 1.5,
      }).addTo(this.layer);
      const url = `/obra/${o.id}`;
      const popup = `
        <strong style="font-family: 'Source Serif 4', Georgia, serif;">${o.nombre_obra || o.nombre_inversion || '(sin nombre)'}</strong><br>
        <span style="color:#78716c">${o.distrito_nombre || ''} · ${o.entidad_nombre || ''}</span><br>
        <small>MEF: <b>${o.estado_proyecto_mef || '?'}</b> · WFS: <b style="color:${critico ? '#9f5442' : 'inherit'}">${o.estado_obra_wfs || '—'}</b></small><br>
        <a href="${url}" style="color:#9f5442">Ver ficha →</a>
      `;
      m.bindPopup(popup);
    }
  }
}
