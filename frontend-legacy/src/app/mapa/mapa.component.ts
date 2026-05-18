import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  ViewChild,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { MapService } from '../core/map.service';
import { ObraResumen } from '../core/models';

type FiltroChip = 'todas' | 'paralizadas' | 'inactivas' | 'con_senal' | 'saldos' | 'con_informe';

@Component({
  selector: 'app-mapa',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <!-- Mapa fullscreen detrás de todo -->
    <div #mapHost class="map-host"></div>

    <!-- Topbar flotante (search + filtros + ubicación) -->
    <div class="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] flex items-center gap-2 w-[min(720px,calc(100%-2rem))]">
      <div class="relative flex-1">
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 text-stone-400" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7"/><path d="m21 21-4.3-4.3"/>
        </svg>
        <input
          type="search"
          [value]="busqueda()"
          (input)="onBuscar($any($event.target).value)"
          placeholder="Buscar obra, entidad, distrito…"
          class="w-full pl-10 pr-4 h-11 rounded-full border border-stone-300 bg-paper/95 backdrop-blur text-sm placeholder:text-stone-400 focus:outline-none focus:border-stone-900 transition-colors shadow-sm"
          aria-label="Buscar obras"
        />
      </div>

      <button
        type="button"
        (click)="drawerOpen.set(!drawerOpen())"
        [class.bg-stone-900]="hayFiltroActivo()"
        [class.text-stone-50]="hayFiltroActivo()"
        [class.border-stone-900]="hayFiltroActivo()"
        class="inline-flex items-center gap-2 h-11 px-4 rounded-full border border-stone-300 bg-paper/95 backdrop-blur text-sm font-medium text-stone-700 hover:bg-paper transition-colors shadow-sm shrink-0"
        aria-label="Filtros"
        [attr.aria-expanded]="drawerOpen()"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="21" y1="6" x2="3" y2="6"/><line x1="15" y1="12" x2="3" y2="12"/><line x1="11" y1="18" x2="3" y2="18"/>
        </svg>
        <span class="hidden sm:inline">Filtros</span>
        <span *ngIf="hayFiltroActivo()" class="text-xs tabular-nums opacity-90">· {{ obras().length }}</span>
      </button>

      <button
        type="button"
        (click)="onRecenter()"
        class="w-11 h-11 rounded-full border border-stone-300 bg-paper/95 backdrop-blur flex items-center justify-center hover:bg-paper transition-colors shadow-sm shrink-0 text-stone-700"
        aria-label="Centrar mapa"
        title="Centrar en Lima"
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>
        </svg>
      </button>
    </div>

    <!-- Result counter flotante (esquina inferior izquierda) -->
    <div class="absolute bottom-6 left-6 z-[1000] px-3 py-2 rounded-lg border border-stone-300 bg-paper/95 backdrop-blur shadow-sm text-xs text-stone-700">
      <span class="font-medium text-stone-900 tabular-nums">{{ obras().length }}</span>
      <span class="text-stone-500"> obra{{ obras().length === 1 ? '' : 's' }}{{ hayFiltroActivo() ? ' (filtradas)' : '' }}</span>
    </div>

    <!-- Zoom controls (esquina inferior derecha) -->
    <div class="absolute bottom-6 right-6 z-[1000] flex flex-col gap-1.5">
      <button (click)="onZoomIn()" class="w-10 h-10 rounded-lg border border-stone-300 bg-paper/95 backdrop-blur flex items-center justify-center hover:bg-paper transition-colors shadow-sm text-stone-700" aria-label="Acercar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 5v14M5 12h14"/></svg>
      </button>
      <button (click)="onZoomOut()" class="w-10 h-10 rounded-lg border border-stone-300 bg-paper/95 backdrop-blur flex items-center justify-center hover:bg-paper transition-colors shadow-sm text-stone-700" aria-label="Alejar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/></svg>
      </button>
    </div>

    <!-- Drawer de filtros (slide desde la derecha) -->
    <aside
      class="fixed top-[65px] right-0 bottom-0 w-[min(360px,90%)] bg-paper border-l border-stone-200 z-[1001] shadow-2xl transition-transform duration-200 ease-out flex flex-col"
      [class.translate-x-full]="!drawerOpen()"
      [attr.aria-hidden]="!drawerOpen()"
      [attr.inert]="!drawerOpen() ? '' : null"
    >
      <header class="flex items-center justify-between px-5 py-4 border-b border-stone-200">
        <h2 class="font-serif text-xl text-stone-900">Filtros</h2>
        <button (click)="drawerOpen.set(false)" class="text-stone-400 hover:text-stone-700 p-1" aria-label="Cerrar filtros">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
        </button>
      </header>

      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-5">
        <section>
          <p class="text-[10px] uppercase tracking-wide text-stone-500 font-medium mb-2.5">Por fuente oficial</p>
          <div class="flex flex-col gap-1.5">
            <button *ngFor="let f of filtros"
              (click)="toggleChip(f.key)"
              [class.bg-stone-900]="chips().has(f.key)"
              [class.text-stone-50]="chips().has(f.key)"
              [class.border-stone-900]="chips().has(f.key)"
              class="text-left px-3.5 py-2.5 border border-stone-200 rounded-lg text-sm text-stone-700 bg-white hover:border-stone-300 transition-colors flex items-start gap-2">
              <span class="flex-1">
                <span class="block font-medium">{{ f.label }}</span>
                <span class="block text-xs opacity-70 mt-0.5">{{ f.hint }}</span>
              </span>
              <span *ngIf="chips().has(f.key)" class="shrink-0 mt-0.5">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>
              </span>
            </button>
          </div>
        </section>

        <section *ngIf="chips().size > 0">
          <button (click)="limpiarChips()" class="w-full text-center px-3 py-2 text-sm text-stone-600 hover:text-stone-900 transition-colors underline underline-offset-2">
            Limpiar filtros
          </button>
        </section>

        <section class="pt-4 border-t border-stone-200">
          <p class="text-[10px] uppercase tracking-wide text-stone-500 font-medium mb-2">Cómo leer el mapa</p>
          <ul class="text-xs text-stone-600 space-y-1.5">
            <li class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-terracotta"></span>
              <span>Con señal crítica (paralizada o desactivada)</span>
            </li>
            <li class="flex items-center gap-2">
              <span class="w-2.5 h-2.5 rounded-full bg-stone-500"></span>
              <span>Sin alertas registradas</span>
            </li>
          </ul>
        </section>
      </div>
    </aside>

    <!-- Panel de obra seleccionada (slide desde la derecha) -->
    <aside
      class="fixed top-[65px] right-0 bottom-0 w-[min(420px,90%)] bg-paper border-l border-stone-200 z-[1002] shadow-2xl transition-transform duration-200 ease-out flex flex-col"
      [class.translate-x-full]="!seleccionada()"
      [attr.aria-hidden]="!seleccionada()"
      [attr.inert]="!seleccionada() ? '' : null"
    >
      <ng-container *ngIf="seleccionada() as s">
        <!-- Header -->
        <header class="flex items-start justify-between gap-3 px-5 pt-4 pb-3 border-b border-stone-200">
          <div class="flex items-center gap-2 flex-wrap min-w-0">
            <span class="text-[10px] text-stone-500 uppercase tracking-wide font-medium">NOBR {{ s.nobr_id }}</span>
            <span class="text-stone-300 text-xs">·</span>
            <span class="text-[10px] text-stone-500 uppercase tracking-wide font-medium">CUI {{ s.cui }}</span>
            <span *ngIf="s.es_saldo_obra" class="text-[10px] px-1.5 py-0.5 bg-stone-100 text-stone-700 rounded">Saldo</span>
          </div>
          <button (click)="cerrarPanel()" class="text-stone-400 hover:text-stone-700 shrink-0 -mr-1 -mt-1 p-1" aria-label="Cerrar">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </header>

        <!-- Contenido scrollable -->
        <div class="flex-1 overflow-y-auto px-5 py-4">
          <h3 class="font-serif text-lg text-stone-900 leading-tight mb-2">
            {{ s.nombre_obra || s.nombre_inversion || '(sin nombre registrado)' }}
          </h3>
          <p class="text-sm text-stone-600 mb-4">
            <span *ngIf="s.entidad_nombre">{{ s.entidad_nombre }}</span>
            <span *ngIf="s.entidad_nombre" class="text-stone-300"> · </span>
            <span>{{ s.distrito_nombre }}</span>
          </p>

          <!-- 3 estados oficiales -->
          <div class="mb-4">
            <p class="text-[10px] text-stone-500 uppercase tracking-wide font-medium mb-2">Lo que dice cada fuente</p>
            <div class="space-y-1.5">
              <div class="flex items-center justify-between gap-3 text-sm">
                <span class="text-stone-500">MEF</span>
                <span class="font-medium" [class.text-terracotta]="esCritico(s.estado_proyecto_mef)" [class.text-stone-900]="!esCritico(s.estado_proyecto_mef)">
                  {{ s.estado_proyecto_mef || '—' }}
                </span>
              </div>
              <div class="flex items-center justify-between gap-3 text-sm">
                <span class="text-stone-500">Contraloría WFS</span>
                <span class="font-medium" [class.text-terracotta]="s.estado_obra_wfs === 'Paralizada'" [class.text-stone-900]="s.estado_obra_wfs !== 'Paralizada'">
                  {{ s.estado_obra_wfs || '— (sin feature)' }}
                </span>
              </div>
              <div class="flex items-center justify-between gap-3 text-sm">
                <span class="text-stone-500">Infobras</span>
                <span class="font-medium text-stone-900">{{ s.estado_obra_ficha || '—' }}</span>
              </div>
            </div>
          </div>

          <!-- Banner discrepancia -->
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
          <div class="flex flex-wrap gap-1.5">
            <span *ngIf="s.existe_informe_control" class="text-[10px] px-2 py-0.5 bg-stone-900 text-stone-50 rounded">Informe Contraloría</span>
            <span *ngIf="s.existe_paralizacion_mef" class="text-[10px] px-2 py-0.5 bg-terracotta/10 text-terracotta rounded">Paralización MEF</span>
          </div>
        </div>

        <!-- Footer CTA -->
        <div class="px-5 py-3 border-t border-stone-200">
          <a [routerLink]="['/obra', s.id]"
            class="block w-full text-center px-3 py-2 bg-stone-900 text-stone-50 rounded text-sm font-medium hover:bg-stone-800 transition-colors">
            Ver ficha completa →
          </a>
        </div>
      </ng-container>
    </aside>
  `,
  styles: [`
    :host {
      position: fixed;
      top: 65px;
      left: 0;
      right: 0;
      bottom: 0;
      display: block;
      overflow: hidden;
      background: #fafaf9;
    }
    .map-host {
      position: absolute;
      inset: 0;
      z-index: 0;
    }
  `],
})
export class MapaComponent implements AfterViewInit, OnDestroy {
  @ViewChild('mapHost', { static: true }) mapHost!: ElementRef<HTMLDivElement>;
  private api = inject(ApiService);
  private mapService = inject(MapService);

  obras = signal<ObraResumen[]>([]);
  seleccionada = signal<ObraResumen | null>(null);
  busqueda = signal<string>('');
  chips = signal<Set<FiltroChip>>(new Set());
  drawerOpen = signal<boolean>(false);

  hayFiltroActivo = computed(() => this.chips().size > 0 || this.busqueda().trim() !== '');

  filtros = [
    { key: 'paralizadas' as FiltroChip, label: 'Paralizada (Contraloría WFS)', hint: 'estado_obra_wfs = Paralizada' },
    { key: 'inactivas' as FiltroChip, label: 'Desactivada (MEF)', hint: 'estado_proyecto_mef = DESACTIVADO_PERMANENTE' },
    { key: 'con_senal' as FiltroChip, label: 'Con señal activa', hint: 'Algoritmo detectó irregularidad' },
    { key: 'saldos' as FiltroChip, label: 'Tiene saldos de obra', hint: 'Contrato original quebrado, hay continuación pendiente' },
    { key: 'con_informe' as FiltroChip, label: 'Con informe de Contraloría', hint: 'Existe al menos un informe de control' },
  ];

  private debounceId: any = null;

  constructor() {
    // Click en marker → set seleccionada
    this.mapService.clickedId$.subscribe(id => {
      if (id === -1) { this.cerrarPanel(); return; }
      const o = this.obras().find(x => x.id === id);
      if (o) this.seleccionada.set(o);
    });

    // Sincronizar markers cuando obras cambian
    effect(() => {
      if (!this.mapService.initialized()) return;
      this.mapService.syncObras(this.obras());
    });

    // Sincronizar destacado del marker al cambiar selección
    effect(() => {
      if (!this.mapService.initialized()) return;
      const s = this.seleccionada();
      this.mapService.applySelected(s ? s.id : null);
    });
  }

  ngAfterViewInit(): void {
    this.mapService.init(this.mapHost.nativeElement);
    this.recargar();
  }

  ngOnDestroy(): void {
    this.mapService.destroy();
  }

  @HostListener('document:keydown.escape')
  onEscape(): void {
    if (this.seleccionada()) { this.cerrarPanel(); return; }
    if (this.drawerOpen()) { this.drawerOpen.set(false); return; }
  }

  onBuscar(value: string): void {
    this.busqueda.set(value);
    clearTimeout(this.debounceId);
    this.debounceId = setTimeout(() => this.recargar(), 250);
  }

  toggleChip(chip: FiltroChip): void {
    const next = new Set(this.chips());
    if (next.has(chip)) next.delete(chip);
    else next.add(chip);
    this.chips.set(next);
    this.recargar();
  }

  limpiarChips(): void {
    this.chips.set(new Set());
    this.recargar();
  }

  recargar(): void {
    const params: Record<string, any> = { limit: 500 };
    const c = this.chips();
    if (c.has('paralizadas')) params['paralizadas_wfs'] = true;
    if (c.has('inactivas')) params['inactivas_mef'] = true;
    if (c.has('saldos')) params['con_saldos'] = true;
    if (c.has('con_senal')) params['con_senal'] = true;
    if (c.has('con_informe')) params['con_informe'] = true;
    const q = this.busqueda().trim();
    if (q) params['q'] = q;

    this.api.obras(params).subscribe(res => this.obras.set(res.items));
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

  cerrarPanel(): void { this.seleccionada.set(null); }
  onZoomIn(): void { this.mapService.zoomIn(); }
  onZoomOut(): void { this.mapService.zoomOut(); }
  onRecenter(): void { this.mapService.recenter(); }
}
