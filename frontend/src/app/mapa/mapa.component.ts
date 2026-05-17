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

      <!-- Mapa + panel flotante -->
      <div class="relative">
        <div #map class="bg-stone-100 rounded-lg overflow-hidden border border-stone-200" style="height: 65vh;"></div>

        <!-- Panel flotante de obra seleccionada -->
        <aside *ngIf="seleccionada() as s"
               class="absolute top-4 right-4 w-[min(380px,calc(100%-2rem))] bg-paper border border-stone-300 rounded-lg shadow-xl overflow-hidden z-[1000]"
               style="max-height: calc(65vh - 2rem); display: flex; flex-direction: column;">

          <!-- Header del panel -->
          <div class="flex items-start justify-between gap-3 px-5 pt-4 pb-3 border-b border-stone-200 bg-white">
            <div class="flex items-center gap-2 flex-wrap min-w-0">
              <span class="text-[10px] text-stone-500 uppercase tracking-wide font-medium">
                NOBR {{ s.nobr_id }}
              </span>
              <span class="text-stone-300 text-xs">·</span>
              <span class="text-[10px] text-stone-500 uppercase tracking-wide font-medium">
                CUI {{ s.cui }}
              </span>
              <span *ngIf="s.es_saldo_obra" class="text-[10px] px-1.5 py-0.5 bg-stone-100 text-stone-700 rounded">
                Saldo
              </span>
            </div>
            <button (click)="cerrarPanel()" class="text-stone-400 hover:text-stone-700 shrink-0 -mr-1 -mt-1 p-1" aria-label="Cerrar">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          <!-- Contenido scrollable -->
          <div class="px-5 py-4 overflow-y-auto" style="flex: 1; min-height: 0;">
            <h3 class="font-serif text-lg text-stone-900 leading-tight mb-2">
              {{ s.nombre_obra || s.nombre_inversion || '(sin nombre registrado)' }}
            </h3>
            <p class="text-sm text-stone-600 mb-4">
              <span *ngIf="s.entidad_nombre">{{ s.entidad_nombre }}</span>
              <span *ngIf="s.entidad_nombre" class="text-stone-300"> · </span>
              <span>{{ s.distrito_nombre }}</span>
            </p>

            <!-- 3 estados oficiales lado a lado (versión compacta) -->
            <div class="mb-4">
              <p class="text-[10px] text-stone-500 uppercase tracking-wide font-medium mb-2">
                Lo que dice cada fuente
              </p>
              <div class="space-y-1.5">
                <div class="flex items-center justify-between gap-3 text-sm">
                  <span class="text-stone-500">MEF</span>
                  <span class="font-medium" [class.text-terracotta]="esCritico(s.estado_proyecto_mef)"
                                              [class.text-stone-900]="!esCritico(s.estado_proyecto_mef)">
                    {{ s.estado_proyecto_mef || '—' }}
                  </span>
                </div>
                <div class="flex items-center justify-between gap-3 text-sm">
                  <span class="text-stone-500">Contraloría WFS</span>
                  <span class="font-medium" [class.text-terracotta]="s.estado_obra_wfs === 'Paralizada'"
                                              [class.text-stone-900]="s.estado_obra_wfs !== 'Paralizada'">
                    {{ s.estado_obra_wfs || '— (sin feature)' }}
                  </span>
                </div>
                <div class="flex items-center justify-between gap-3 text-sm">
                  <span class="text-stone-500">Infobras</span>
                  <span class="font-medium text-stone-900">{{ s.estado_obra_ficha || '—' }}</span>
                </div>
              </div>
            </div>

            <!-- Indicador de discrepancia -->
            <div *ngIf="hayDiscrepancia(s)" class="mb-4 p-2.5 bg-terracotta/5 border border-terracotta/20 rounded text-xs text-stone-700">
              <strong class="text-terracotta">⚠ Las fuentes no coinciden.</strong> Revisa la ficha completa.
            </div>

            <!-- Métricas -->
            <div class="grid grid-cols-2 gap-3 mb-4">
              <div class="bg-stone-50 border border-stone-200 rounded p-2.5">
                <p class="text-[10px] text-stone-500 uppercase tracking-wide mb-0.5">Avance MEF</p>
                <p class="font-serif text-lg text-stone-900">{{ s.avance_fisico_mef ?? '—' }}<span class="text-sm text-stone-400">{{ s.avance_fisico_mef !== null ? '%' : '' }}</span></p>
              </div>
              <div class="bg-stone-50 border border-stone-200 rounded p-2.5">
                <p class="text-[10px] text-stone-500 uppercase tracking-wide mb-0.5">Avance Infobras</p>
                <p class="font-serif text-lg text-stone-900">{{ s.avance_fisico_infobras ?? '—' }}<span class="text-sm text-stone-400">{{ s.avance_fisico_infobras !== null ? '%' : '' }}</span></p>
              </div>
              <div *ngIf="s.costo_actualizado" class="bg-stone-50 border border-stone-200 rounded p-2.5">
                <p class="text-[10px] text-stone-500 uppercase tracking-wide mb-0.5">Costo actualizado</p>
                <p class="font-serif text-sm text-stone-900">S/ {{ s.costo_actualizado | number:'1.0-0' }}</p>
              </div>
              <div *ngIf="s.sobrecosto_pct !== null"
                   class="border rounded p-2.5"
                   [class.bg-terracotta]="(s.sobrecosto_pct ?? 0) > 30"
                   [class.text-white]="(s.sobrecosto_pct ?? 0) > 30"
                   [class.border-terracotta]="(s.sobrecosto_pct ?? 0) > 30"
                   [class.bg-stone-50]="(s.sobrecosto_pct ?? 0) <= 30"
                   [class.border-stone-200]="(s.sobrecosto_pct ?? 0) <= 30">
                <p class="text-[10px] uppercase tracking-wide mb-0.5"
                   [class.text-white]="(s.sobrecosto_pct ?? 0) > 30"
                   [class.text-stone-500]="(s.sobrecosto_pct ?? 0) <= 30">Sobrecosto</p>
                <p class="font-serif text-lg">{{ s.sobrecosto_pct }}%</p>
              </div>
            </div>

            <!-- Badges -->
            <div class="flex flex-wrap gap-1.5 mb-4">
              <span *ngIf="s.existe_informe_control" class="text-[10px] px-2 py-0.5 bg-stone-900 text-stone-50 rounded">
                Informe Contraloría
              </span>
              <span *ngIf="s.existe_paralizacion_mef" class="text-[10px] px-2 py-0.5 bg-terracotta/10 text-terracotta rounded">
                Paralización MEF
              </span>
            </div>
          </div>

          <!-- Footer del panel: CTA -->
          <div class="px-5 py-3 border-t border-stone-200 bg-white">
            <a [routerLink]="['/obra', s.id]"
               class="block w-full text-center px-3 py-2 bg-stone-900 text-stone-50 rounded text-sm font-medium hover:bg-stone-800 transition-colors">
              Ver ficha completa →
            </a>
          </div>
        </aside>
      </div>

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
  seleccionada = signal<ObraResumen | null>(null);
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
    // Cerrar panel al clickear fuera de un marker
    this.map.on('click', () => this.cerrarPanel());
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

  hayDiscrepancia(o: ObraResumen): boolean {
    const mef = (o.estado_proyecto_mef || '').toUpperCase();
    const wfs = (o.estado_obra_wfs || '').toUpperCase();
    const inf = (o.estado_obra_ficha || '').toUpperCase();
    if (mef === 'ACTIVO' && wfs.includes('PARALIZ')) return true;
    if (mef.includes('DESACTIVA') && (inf.includes('EJECUCI') || wfs.includes('EJECUCI'))) return true;
    if (o.avance_fisico_mef !== null && o.avance_fisico_infobras !== null) {
      if (Math.abs(Number(o.avance_fisico_mef) - Number(o.avance_fisico_infobras)) > 10) return true;
    }
    return false;
  }

  abrirPanel(obra: ObraResumen) {
    this.seleccionada.set(obra);
  }

  cerrarPanel() {
    this.seleccionada.set(null);
  }

  private draw(items: ObraResumen[]) {
    this.layer.clearLayers();
    for (const o of items) {
      if (!o.latitud || !o.longitud) continue;
      const critico = o.estado_obra_wfs === 'Paralizada'
                   || (o.estado_proyecto_mef || '').toUpperCase().includes('DESACTIVA');
      const color = critico ? '#9f5442' : '#a8a29e';
      const m = L.circleMarker([Number(o.latitud), Number(o.longitud)], {
        radius: critico ? 8 : 6,
        color,
        fillColor: color,
        fillOpacity: 0.75,
        weight: 1.5,
      }).addTo(this.layer);
      m.on('click', (e: any) => {
        L.DomEvent.stopPropagation(e);  // evita que el click del mapa cierre el panel
        this.abrirPanel(o);
      });
    }
  }
}
