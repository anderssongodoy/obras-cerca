import { DOCUMENT } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';

import { GeolocationService } from '../../core/services/geolocation.service';
import { MapService } from '../../core/services/map.service';
import { ObrasService } from '../../core/services/obras.service';
import { FiltrosService } from '../../core/services/filtros.service';
import { SenalesService } from '../../core/services/senales.service';
import { FiltrosDrawer } from './components/filtros-drawer/filtros-drawer';
import { FloatControls } from './components/float-controls/float-controls';
import { LeafletMap } from './components/leaflet-map/leaflet-map';
import { LocationPermissionModal } from './components/location-permission-modal/location-permission-modal';
import { ObraPanel } from './components/obra-panel/obra-panel';
import { ResultCounter } from './components/result-counter/result-counter';
import { Topbar } from './components/topbar/topbar';
import { RadioSelector } from './components/radio-selector/radio-selector';
import { TopbarStrip } from './components/topbar-strip/topbar-strip';
import type { FiltroChip } from '../../core/models/filtros.model';

@Component({
  selector: 'app-mapa-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    LeafletMap,
    Topbar,
    TopbarStrip,
    RadioSelector,
    FloatControls,
    ResultCounter,
    ObraPanel,
    FiltrosDrawer,
    LocationPermissionModal,
  ],
  templateUrl: './mapa.page.html',
  styleUrl: './mapa.page.scss',
  host: {
    '(document:keydown.escape)': 'onEscape()',
  },
})
export class MapaPage {
  private readonly obrasService = inject(ObrasService);
  private readonly senalesService = inject(SenalesService);
  private readonly filtrosService = inject(FiltrosService);
  private readonly mapService = inject(MapService);
  private readonly geolocation = inject(GeolocationService);
  private readonly document = inject(DOCUMENT);
  private focusBeforeDrawer: HTMLElement | null = null;

  protected readonly selectedId = signal<number | null>(null);
  protected readonly drawerOpen = signal<boolean>(false);

  private readonly clickedId = toSignal(this.mapService.clickedId$, { initialValue: null });

  protected readonly obras = this.obrasService.obras;
  protected readonly total = this.obrasService.total;
  protected readonly busqueda = this.filtrosService.texto;
  protected readonly hasActiveFilter = this.filtrosService.hasActiveFilter;
  protected readonly geoStatus = this.geolocation.status;
  protected readonly activeChip = this.filtrosService.estado;

  protected readonly visibleCount = computed(() => {
    const obras = this.obras();
    const chip = this.activeChip();
    if (chip === 'todas') return obras.length;
    if (chip === 'con_senal') return obras.filter((o) => o.conSenal).length;
    return obras.filter((o) => o.estado === chip).length;
  });

  protected readonly selectedObra = computed(() => {
    const id = this.selectedId();
    if (id == null) return null;
    return this.obras().find((o) => o.id === id) ?? null;
  });

  protected readonly chipCounts = computed<Record<FiltroChip, number>>(() => {
    const obras = this.obras();
    return {
      todas: obras.length,
      en_ejecucion: obras.filter((o) => o.estado === 'en_ejecucion').length,
      en_licitacion: obras.filter((o) => o.estado === 'en_licitacion').length,
      verificada: obras.filter((o) => o.estado === 'verificada').length,
      informativo: obras.filter((o) => o.estado === 'informativo').length,
      senal: obras.filter((o) => o.estado === 'senal').length,
      con_senal: obras.filter((o) => o.conSenal).length,
    };
  });

  constructor() {
    effect(() => {
      const id = this.clickedId();
      if (id != null) this.selectedId.set(id);
    });

    effect(() => {
      if (!this.mapService.initialized()) return;
      this.mapService.syncObras(this.obras());
    });

    effect(() => {
      if (!this.mapService.initialized()) return;
      this.mapService.applyFilter(this.activeChip());
    });

    effect(() => {
      if (!this.mapService.initialized()) return;
      this.mapService.applySelected(this.selectedId());
    });

  }

  protected onSearchChanged(value: string): void {
    this.filtrosService.setTexto(value);
    this.obrasService.busqueda.set(value);
  }

  protected onFiltrosOpened(): void {
    const activeElement = this.document.activeElement;
    this.focusBeforeDrawer = activeElement instanceof HTMLElement ? activeElement : null;
    this.drawerOpen.set(true);
  }

  protected onDrawerClosed(): void {
    this.drawerOpen.set(false);
    this.restoreDrawerFocus();
  }

  protected onChipChanged(chip: FiltroChip): void {
    this.filtrosService.setEstado(chip);
  }

  protected onFiltrosReset(): void {
    this.filtrosService.reset();
  }

  protected onLocationCentered(): void {
    this.geolocation.centerOnUser();
  }

  protected onZoomIn(): void {
    this.mapService.zoomIn();
  }

  protected onZoomOut(): void {
    this.mapService.zoomOut();
  }

  protected onLayerToggled(): void {
    /* Fase 7 — tile light/dark toggle. */
  }

  protected onPanelClosed(): void {
    this.selectedId.set(null);
  }

  protected onEscape(): void {
    if (this.drawerOpen()) {
      this.drawerOpen.set(false);
      this.restoreDrawerFocus();
      return;
    }
    if (this.selectedId() != null) this.selectedId.set(null);
  }

  private restoreDrawerFocus(): void {
    const target = this.focusBeforeDrawer;
    this.focusBeforeDrawer = null;
    queueMicrotask(() => target?.focus());
  }
}
