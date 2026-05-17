import {
  Component, OnInit, AfterViewInit, OnDestroy,
  Output, EventEmitter, Input, OnChanges,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import * as L from 'leaflet';
import { ObrasService } from '../../core/services/obras.service';
import { Obra } from '../../core/mock/mock-obras';

// Fix leaflet default marker icons
const iconDefault = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41], iconAnchor: [12, 41], popupAnchor: [1, -34],
});
L.Marker.prototype.options.icon = iconDefault;

function obraIcon(obra: Obra): L.DivIcon {
  const color = obra.confirmada_contraloria_2025 ? '#22d3ee'
    : obra.clasificacion_paralizacion === 'vigente' ? '#ef4444'
    : obra.existe_paralizacion ? '#f59e0b'
    : '#22c55e';
  const size = obra.monto_contrato > 100_000_000 ? 20 : obra.monto_contrato > 10_000_000 ? 14 : 10;
  return L.divIcon({
    className: '',
    html: `<div style="
      width:${size}px;height:${size}px;
      background:${color};
      border:2px solid rgba(0,0,0,.4);
      border-radius:50%;
      box-shadow:0 0 ${size/2}px ${color}88;
      cursor:pointer;
    "></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

@Component({
  selector: 'app-mapa',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="mapa-container">
      <!-- Barra de filtros -->
      <div class="filtros-bar">
        <input
          class="search-input"
          type="text"
          placeholder="🔍 Buscar obra..."
          [(ngModel)]="busqueda"
          (input)="aplicarFiltros()"
        />
        <select [(ngModel)]="filtroParalizada" (change)="aplicarFiltros()">
          <option value="">Todas las obras</option>
          <option value="true">Solo paralizadas</option>
          <option value="false">Solo en ejecución</option>
        </select>
        <select [(ngModel)]="filtroClasificacion" (change)="aplicarFiltros()">
          <option value="">Todas las clasificaciones</option>
          <option value="vigente">🔴 Vigentes</option>
          <option value="dudosa">🟡 Dudosas</option>
          <option value="zombie">⚫ Zombies</option>
        </select>
        <div class="filtro-total">{{ obrasVisibles }} obras</div>
      </div>

      <!-- Leyenda -->
      <div class="leyenda">
        <span><span class="dot" style="background:#ef4444"></span>Paralizada vigente</span>
        <span><span class="dot" style="background:#22d3ee"></span>Contraloría ✅</span>
        <span><span class="dot" style="background:#f59e0b"></span>Paralizada otra</span>
        <span><span class="dot" style="background:#22c55e"></span>En ejecución</span>
        <span class="size-hint">● tamaño = monto</span>
      </div>

      <!-- Mapa Leaflet -->
      <div id="map" class="leaflet-map"></div>
    </div>
  `,
  styleUrls: ['./mapa.component.scss'],
})
export class MapaComponent implements AfterViewInit, OnDestroy, OnChanges {
  @Output() obraSeleccionada = new EventEmitter<number>();
  @Input() destacarObraId: number | null = null;

  private map!: L.Map;
  private markers: L.Layer[] = [];
  private distritoLayer!: L.LayerGroup;

  busqueda = '';
  filtroParalizada = '';
  filtroClasificacion = '';
  obrasVisibles = 0;

  constructor(private svc: ObrasService) {}

  ngAfterViewInit(): void {
    this.initMap();
    this.cargarDistritos();
    this.aplicarFiltros();
  }

  ngOnChanges(): void {
    if (this.map && this.destacarObraId) this.destacarObra(this.destacarObraId);
  }

  ngOnDestroy(): void {
    this.map?.remove();
  }

  private initMap(): void {
    this.map = L.map('map', {
      center: [-12.046374, -77.042793],
      zoom: 11,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://carto.com/">CARTO</a> &copy; OSM contributors',
      subdomains: 'abcd', maxZoom: 19,
    }).addTo(this.map);

    this.distritoLayer = L.layerGroup().addTo(this.map);

    // Forzar recálculo de tamaño real del contenedor después de render
    setTimeout(() => this.map.invalidateSize(), 100);
  }

  private cargarDistritos(): void {
    this.svc.getDistritosResumen().subscribe(distritos => {
      distritos.forEach(d => {
        const radio = Math.sqrt(d.paralizadas_vigentes || 0) * 8000 + 5000;
        const color = d.paralizadas_vigentes > 4 ? '#ef444460'
          : d.paralizadas_vigentes > 1 ? '#f59e0b40'
          : '#22c55e20';
        L.circle([d.lat, d.lon], {
          radius: radio, color: color.slice(0, 7), fillColor: color, fillOpacity: 0.3,
          weight: 1,
        })
          .bindTooltip(
            `<strong>${d.distrito}</strong><br>` +
            `${d.total_obras} obras · ${d.paralizadas_vigentes} paralizadas vigentes`,
            { sticky: true }
          )
          .addTo(this.distritoLayer);
      });
    });
  }

  aplicarFiltros(): void {
    this.markers.forEach(m => this.map?.removeLayer(m));
    this.markers = [];

    const filtros = {
      paralizadas: this.filtroParalizada === 'true' ? true
        : this.filtroParalizada === 'false' ? false : undefined,
      clasificacion: this.filtroClasificacion || undefined,
      q: this.busqueda || undefined,
    };

    this.svc.getObras(filtros).subscribe(({ items }) => {
      this.obrasVisibles = items.length;
      items.forEach(obra => this.agregarMarker(obra));
    });
  }

  private agregarMarker(obra: Obra): void {
    if (!obra.latitud || !obra.longitud) return;

    const marker = L.marker([obra.latitud, obra.longitud], { icon: obraIcon(obra) });

    marker.bindPopup(this.popupHtml(obra), { maxWidth: 280 });
    marker.on('click', () => this.obraSeleccionada.emit(obra.id));
    marker.addTo(this.map);
    this.markers.push(marker);
  }

  private popupHtml(o: Obra): string {
    const paralTag = o.confirmada_contraloria_2025
      ? '<span style="color:#22d3ee;font-size:.7rem">✅ Contraloría dic-2025</span>'
      : o.clasificacion_paralizacion === 'vigente'
      ? '<span style="color:#ef4444;font-size:.7rem">🔴 Paralizada vigente</span>'
      : '';
    return `
      <div style="font-family:sans-serif;max-width:260px">
        <p style="margin:0 0 4px;font-weight:700;font-size:.85rem;line-height:1.3">${o.nombre}</p>
        ${paralTag}
        <p style="margin:4px 0 0;font-size:.75rem;color:#666">📍 ${o.distrito_nombre}</p>
        <p style="margin:2px 0 0;font-size:.75rem;color:#666">💰 S/ ${(o.monto_contrato / 1e6).toFixed(2)} M</p>
        <p style="margin:2px 0 0;font-size:.75rem;color:#666">📊 ${o.avance_fisico_real}% avance</p>
        ${o.dias_paralizada_real ? `<p style="margin:2px 0 0;font-size:.75rem;color:#ef4444">⏱ ${o.dias_paralizada_real} días paralizada</p>` : ''}
        <button
          onclick="document.dispatchEvent(new CustomEvent('obra-click',{detail:${o.id}}))"
          style="margin-top:8px;width:100%;padding:5px;background:#1e3a5f;color:#7dd3fc;border:none;border-radius:6px;cursor:pointer;font-size:.78rem"
        >Ver ficha completa →</button>
      </div>`;
  }

  private destacarObra(id: number): void {
    // centrar en el marker correspondiente
    this.svc.getObra(id).subscribe(o => {
      if (o?.latitud && o?.longitud) {
        this.map.setView([o.latitud, o.longitud], 15, { animate: true });
      }
    });
  }
}
