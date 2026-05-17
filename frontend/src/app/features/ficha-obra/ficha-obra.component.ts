import { Component, Input, Output, EventEmitter, OnChanges } from '@angular/core';
import { CommonModule, DecimalPipe, PercentPipe } from '@angular/common';
import { ObrasService } from '../../core/services/obras.service';
import { Obra } from '../../core/mock/mock-obras';
import { SolesPipe } from '../../shared/pipes/soles.pipe';
import { ClasificacionPipe } from '../../shared/pipes/clasificacion.pipe';

@Component({
  selector: 'app-ficha-obra',
  standalone: true,
  imports: [CommonModule, SolesPipe, ClasificacionPipe, DecimalPipe],
  template: `
    <div class="ficha" *ngIf="obra">
      <div class="ficha-header" [class.paralizada]="obra.existe_paralizacion">
        <div class="estado-badges">
          <span class="badge-estado" [class]="'estado-' + estadoClass(obra.estado_ejecucion)">
            {{ obra.estado_ejecucion }}
          </span>
          <span *ngIf="obra.confirmada_contraloria_2025" class="badge-contraloria">
            ✅ Contraloría dic-2025
          </span>
          <span *ngIf="obra.clasificacion_paralizacion" class="badge-clasif" [class]="'clasif-' + obra.clasificacion_paralizacion">
            {{ obra.clasificacion_paralizacion | clasificacion }}
          </span>
        </div>
        <button class="close-btn" (click)="cerrar.emit()">✕</button>
      </div>

      <div class="ficha-body">
        <h3 class="obra-nombre">{{ obra.nombre }}</h3>

        <div class="info-row">
          <span class="info-icon">📍</span>
          <span>{{ obra.direccion }} — <strong>{{ obra.distrito_nombre }}</strong></span>
        </div>
        <div class="info-row">
          <span class="info-icon">🏛</span>
          <span>{{ obra.entidad_nombre }}</span>
        </div>
        <div class="info-row">
          <span class="info-icon">🏢</span>
          <span>{{ obra.contratista_nombre }} <em>({{ obra.contratista_ruc }})</em></span>
        </div>

        <div class="section-divider">Avance y presupuesto</div>

        <div class="progress-block">
          <div class="progress-labels">
            <span>Avance físico</span>
            <strong [class.danger]="obra.existe_paralizacion">{{ obra.avance_fisico_real | number:'1.1-2' }}%</strong>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" [style.width.%]="obra.avance_fisico_real"
                 [class.fill-danger]="obra.existe_paralizacion"
                 [class.fill-ok]="!obra.existe_paralizacion"></div>
            <div class="progress-prog" [style.width.%]="obra.avance_fisico_programado"></div>
          </div>
          <div class="progress-sub">Programado: {{ obra.avance_fisico_programado | number:'1.0-1' }}%</div>
        </div>

        <div class="montos-grid">
          <div class="monto-item">
            <span class="monto-label">Monto contrato</span>
            <span class="monto-val">{{ obra.monto_contrato | soles }}</span>
          </div>
          <div class="monto-item">
            <span class="monto-label">Ejecutado</span>
            <span class="monto-val">{{ obra.monto_ejecutado | soles }}</span>
          </div>
          <div class="monto-item">
            <span class="monto-label">Ejecución financiera</span>
            <span class="monto-val">{{ obra.porcentaje_ejecucion_financiera | number:'1.1-1' }}%</span>
          </div>
        </div>

        <div class="fechas-grid">
          <div>
            <span class="info-label">Inicio</span>
            <span>{{ obra.fecha_inicio }}</span>
          </div>
          <div>
            <span class="info-label">Fin programado</span>
            <span>{{ obra.fecha_fin_programada }}</span>
          </div>
          <div>
            <span class="info-label">Último avance</span>
            <span>{{ obra.fecha_ultimo_avance }}</span>
          </div>
        </div>

        <!-- Paralización -->
        <ng-container *ngIf="obra.paralizacion">
          <div class="section-divider danger">⚠️ Paralización</div>
          <div class="paralizacion-block">
            <div class="par-row">
              <span>Fecha</span>
              <strong>{{ obra.paralizacion.fecha_paralizacion }}</strong>
            </div>
            <div class="par-row">
              <span>Días paralizada</span>
              <strong class="danger">{{ obra.dias_paralizada_real }} días</strong>
            </div>
            <div class="par-row">
              <span>Causal</span>
              <strong>{{ obra.paralizacion.causal }}</strong>
            </div>
            <p class="par-comentario">{{ obra.paralizacion.comentarios }}</p>
          </div>
        </ng-container>

        <!-- Señales -->
        <ng-container *ngIf="obra.senales && obra.senales.length">
          <div class="section-divider">🚨 Señales ({{ obra.senales.length }})</div>
          <div class="senal-mini" *ngFor="let s of obra.senales">
            <p class="senal-titulo">{{ s.titulo }}</p>
            <p class="senal-exp">{{ s.explicacion }}</p>
            <code class="senal-formula">{{ s.formula }}</code>
          </div>
        </ng-container>

        <div class="actions">
          <a *ngIf="obra.infobras_url" [href]="obra.infobras_url" target="_blank" class="btn-source">
            Ver en Infobras ↗
          </a>
          <button class="btn-export" (click)="exportar()">📥 Exportar evidencia CSV</button>
        </div>
      </div>
    </div>
  `,
  styleUrls: ['./ficha-obra.component.scss'],
})
export class FichaObraComponent implements OnChanges {
  @Input() obraId: number | null = null;
  @Output() cerrar = new EventEmitter<void>();

  obra: Obra | null = null;

  constructor(private svc: ObrasService) {}

  ngOnChanges() {
    if (this.obraId != null) {
      this.svc.getObra(this.obraId).subscribe(o => this.obra = o ?? null);
    } else {
      this.obra = null;
    }
  }

  estadoClass(estado: string): string {
    if (!estado) return '';
    const e = estado.toLowerCase();
    if (e.includes('paraliz')) return 'paralizada';
    if (e.includes('ejecuc')) return 'ejecucion';
    if (e.includes('termin') || e.includes('conclu')) return 'terminada';
    return 'otro';
  }

  exportar() {
    if (!this.obra) return;
    const rows = [
      ['Campo', 'Valor'],
      ['Código Infobras', this.obra.codigo_infobras],
      ['Nombre', this.obra.nombre],
      ['Estado', this.obra.estado_ejecucion],
      ['Entidad', this.obra.entidad_nombre],
      ['Contratista', this.obra.contratista_nombre],
      ['RUC Contratista', this.obra.contratista_ruc],
      ['Distrito', this.obra.distrito_nombre],
      ['Dirección', this.obra.direccion],
      ['Monto contrato', this.obra.monto_contrato],
      ['Monto ejecutado', this.obra.monto_ejecutado],
      ['Avance físico %', this.obra.avance_fisico_real],
      ['Días paralizada', this.obra.dias_paralizada_real ?? ''],
      ['Clasificación', this.obra.clasificacion_paralizacion ?? ''],
      ['Confirmada Contraloría', this.obra.confirmada_contraloria_2025],
      ['Fuente oficial', this.obra.infobras_url ?? ''],
    ];
    const csv = rows.map(r => r.map(v => `"${v}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `obra_${this.obra.codigo_infobras}_evidencia.csv`;
    a.click();
  }
}
