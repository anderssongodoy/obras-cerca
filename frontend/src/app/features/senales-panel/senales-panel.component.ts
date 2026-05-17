import { Component, OnInit, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ObrasService } from '../../core/services/obras.service';
import { Senal } from '../../core/mock/mock-obras';

const TIPO_LABELS: Record<string, string> = {
  paralizacion:            '🔴 Paralización',
  paralizacion_prolongada: '🟡 Prolongada',
  concentracion_menores:   '🟠 Conc. ≤8 UIT',
  monto_atipico:           '⚠️ Monto atípico',
  avance_fisico_estancado: '📉 Estancada',
};

@Component({
  selector: 'app-senales-panel',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="panel">
      <div class="panel-header">
        <h2>🚨 Señales de revisión</h2>
        <span class="badge">{{ senales.length }}</span>
      </div>

      <div class="filters">
        <select [(ngModel)]="tipoFiltro" (change)="cargar()">
          <option value="">Todos los tipos</option>
          <option value="paralizacion">Paralización</option>
          <option value="paralizacion_prolongada">Prolongada</option>
          <option value="concentracion_menores">Conc. ≤8 UIT</option>
        </select>
        <label class="check-label">
          <input type="checkbox" [(ngModel)]="soloConfirmadas" (change)="cargar()" />
          Solo Contraloría
        </label>
      </div>

      <div class="senal-list">
        <div
          *ngFor="let s of senales"
          class="senal-card"
          [class.confirmada]="s.confirmada_contraloria_2025"
          (click)="s.obra_id && seleccionar.emit(s.obra_id)"
        >
          <div class="senal-top">
            <span class="tipo-badge" [class]="'tipo-' + s.tipo">
              {{ tipoLabel(s.tipo) }}
            </span>
            <span class="score">score {{ s.score }}</span>
          </div>
          <p class="senal-titulo">{{ s.titulo }}</p>
          <p class="senal-desc">{{ s.explicacion }}</p>
          <div class="senal-meta" *ngIf="s.entidad_nombre">
            <span>🏛 {{ s.entidad_nombre }}</span>
          </div>
          <div class="senal-meta" *ngIf="s.contratista_nombre">
            <span>🏢 {{ s.contratista_nombre }}</span>
          </div>
          <div class="senal-formula" *ngIf="s.formula">
            <code>{{ s.formula }}</code>
          </div>
          <div class="contraloria-badge" *ngIf="s.confirmada_contraloria_2025">
            ✅ Confirmada Contraloría dic-2025
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    :host { display: flex; flex-direction: column; height: 100%; overflow: hidden; }
    .panel { display: flex; flex-direction: column; height: 100%; background: #0f172a; color: white; overflow: hidden; }    .panel-header { display: flex; align-items: center; gap: 10px; padding: 14px 16px 8px; border-bottom: 1px solid rgba(255,255,255,.1); }
    h2 { margin: 0; font-size: 1rem; font-weight: 700; flex: 1; }
    .badge { background: #ef4444; color: white; border-radius: 20px; padding: 2px 8px; font-size: .75rem; font-weight: 700; }
    .filters { display: flex; align-items: center; gap: 10px; padding: 8px 16px; border-bottom: 1px solid rgba(255,255,255,.08); }
    select { background: #1e293b; color: white; border: 1px solid #334155; border-radius: 6px; padding: 4px 8px; font-size: .8rem; flex: 1; }
    .check-label { font-size: .75rem; color: #94a3b8; display: flex; align-items: center; gap: 4px; cursor: pointer; white-space: nowrap; }
    .senal-list { overflow-y: auto; flex: 1; padding: 10px 12px; display: flex; flex-direction: column; gap: 10px; }
    .senal-card {
      background: #1e293b; border-radius: 10px; padding: 12px;
      border-left: 3px solid #475569; cursor: pointer; transition: all .15s;
    }
    .senal-card:hover { background: #263548; transform: translateX(2px); }
    .senal-card.confirmada { border-left-color: #22d3ee; }
    .senal-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .tipo-badge { font-size: .7rem; font-weight: 600; padding: 2px 8px; border-radius: 20px; background: #334155; }
    .tipo-paralizacion { background: rgba(239,68,68,.2); color: #fca5a5; }
    .tipo-paralizacion_prolongada { background: rgba(245,158,11,.2); color: #fcd34d; }
    .tipo-concentracion_menores { background: rgba(249,115,22,.2); color: #fdba74; }
    .score { font-size: .7rem; color: #64748b; }
    .senal-titulo { margin: 0 0 4px; font-size: .85rem; font-weight: 600; line-height: 1.3; }
    .senal-desc { margin: 0 0 6px; font-size: .75rem; color: #94a3b8; line-height: 1.4; }
    .senal-meta { font-size: .7rem; color: #64748b; margin-bottom: 2px; }
    .senal-formula { margin-top: 6px; }
    code { font-size: .65rem; color: #7dd3fc; background: rgba(0,0,0,.3); padding: 3px 6px; border-radius: 4px; word-break: break-all; }
    .contraloria-badge { margin-top: 6px; font-size: .7rem; color: #22d3ee; font-weight: 600; }
  `],
})
export class SenalesPanelComponent implements OnInit {
  @Output() seleccionar = new EventEmitter<number>();

  senales: Senal[] = [];
  tipoFiltro = '';
  soloConfirmadas = false;

  constructor(private svc: ObrasService) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.svc.getSenales({
      tipo: this.tipoFiltro || undefined,
      solo_confirmadas: this.soloConfirmadas,
    }).subscribe(s => this.senales = s);
  }

  tipoLabel(tipo: string): string {
    return TIPO_LABELS[tipo] ?? tipo;
  }
}
