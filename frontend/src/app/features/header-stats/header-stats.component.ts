import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ObrasService } from '../../core/services/obras.service';
import { SolesPipe } from '../../shared/pipes/soles.pipe';

@Component({
  selector: 'app-header-stats',
  standalone: true,
  imports: [CommonModule, SolesPipe],
  template: `
    <header class="header">
      <div class="brand">
        <span class="logo">🏗️</span>
        <div>
          <h1>ObrasCerca</h1>
          <span class="tagline">Obras públicas visibles para todos — Lima &amp; Callao</span>
        </div>
      </div>
      <div class="kpis" *ngIf="stats">
        <div class="kpi">
          <span class="kpi-value">{{ stats.totales.obras | number:'1.0-0' }}</span>
          <span class="kpi-label">obras</span>
        </div>
        <div class="kpi kpi-alert">
          <span class="kpi-value">{{ stats.totales.paralizadas_vigentes }}</span>
          <span class="kpi-label">paralizadas vigentes</span>
        </div>
        <div class="kpi kpi-danger">
          <span class="kpi-value">{{ stats.totales.monto_paralizado | soles }}</span>
          <span class="kpi-label">detenido</span>
        </div>
        <div class="kpi">
          <span class="kpi-value">{{ stats.catalogos.senales_activas }}</span>
          <span class="kpi-label">señales activas</span>
        </div>
        <div class="kpi kpi-verified">
          <span class="kpi-value">{{ stats.totales.confirmadas_contraloria }}</span>
          <span class="kpi-label">con sello Contraloría</span>
        </div>
      </div>
    </header>
  `,
  styles: [`
    .header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      background: #0f172a;
      color: white;
      padding: 10px 20px;
      gap: 20px;
      flex-wrap: wrap;
      box-shadow: 0 2px 8px rgba(0,0,0,.4);
      z-index: 1000;
      position: relative;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .logo { font-size: 2rem; }
    h1 { margin: 0; font-size: 1.4rem; font-weight: 700; letter-spacing: -0.5px; }
    .tagline { font-size: 0.72rem; color: #94a3b8; }
    .kpis { display: flex; gap: 16px; flex-wrap: wrap; }
    .kpi {
      display: flex; flex-direction: column; align-items: center;
      background: rgba(255,255,255,.05);
      border-radius: 8px; padding: 6px 14px;
      min-width: 80px;
    }
    .kpi-value { font-size: 1.25rem; font-weight: 700; }
    .kpi-label { font-size: 0.65rem; color: #94a3b8; text-align: center; }
    .kpi-alert .kpi-value { color: #f59e0b; }
    .kpi-danger .kpi-value { color: #ef4444; }
    .kpi-verified .kpi-value { color: #22d3ee; }
  `],
})
export class HeaderStatsComponent implements OnInit {
  stats: any;
  constructor(private svc: ObrasService) {}
  ngOnInit() { this.svc.getStats().subscribe(s => this.stats = s); }
}
