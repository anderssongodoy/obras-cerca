import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { ChatPeriodistaComponent } from '../../widgets/chat-periodista/chat-periodista.component';

interface ObraFicha {
  id: number;
  nobr_id: number | null;
  cui: number | null;
  nombre_inversion: string | null;
  nombre_obra: string | null;
  entidad_nombre: string | null;
  distrito_nombre: string | null;
  direccion: string | null;
  estado_obra_wfs: string | null;
  estado_obra_ficha: string | null;
  estado_proyecto_mef: string | null;
  avance_fisico_infobras: number | string | null;
  avance_fisico_mef: number | string | null;
  devengado_siaf: number | string | null;
  fecha_ult_avance: string | null;
  fecha_inicio_mef: string | null;
  fecha_fin_mef: string | null;
  mto_viable: number | string | null;
  costo_actualizado: number | string | null;
  monto_contrato: number | string | null;
  sobrecosto_pct: number | string | null;
  existe_paralizacion_mef: boolean;
  existe_informe_control: boolean;
  es_saldo_obra: boolean;
  url_infobras_ficha?: string | null;
  url_mef_ssi?: string | null;
  url_infobras_informes?: string | null;
  informes_control?: Array<{
    anio: number;
    nro_informe: string;
    titulo: string;
    tipo_servicio: string;
    modalidad: string;
    fecha_publicacion?: string | null;
    url_pdf_resumen?: string | null;
    url_pdf_completo?: string | null;
  }>;
  senales?: Array<{
    tipo: string;
    titulo: string;
    resumen: string;
    score?: number | string | null;
    formula?: string;
  }>;
}

function resolveApiBase(): string {
  if (typeof window === 'undefined') return 'http://localhost:8000';
  const host = window.location.hostname;
  if (host === 'localhost' || host === '127.0.0.1' || host.startsWith('192.168.')) {
    return 'http://localhost:8000';
  }
  return 'https://api.obrascerca.trinitylabs.app';
}

@Component({
  selector: 'app-obra-detalle-page',
  standalone: true,
  imports: [CommonModule, RouterLink, ChatPeriodistaComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <main class="page">
      <a routerLink="/mapa" class="back">← Volver al mapa</a>

      @if (loading()) {
        <p class="loading">Cargando ficha…</p>
      } @else if (error()) {
        <p class="error">{{ error() }}</p>
      } @else if (obra(); as o) {

        <header class="header">
          <div class="ids">
            <span class="id-tag">NOBR {{ o.nobr_id }}</span>
            <span class="id-tag">CUI {{ o.cui }}</span>
            @if (o.es_saldo_obra) { <span class="id-tag saldo">Saldo</span> }
          </div>
          <h1>{{ o.nombre_obra || o.nombre_inversion }}</h1>
          <p class="subtitle">
            {{ o.entidad_nombre || 'Entidad sin registrar' }} · {{ o.distrito_nombre }}
          </p>
        </header>

        @if (hayDiscrepancia(o)) {
          <div class="banner-discrepancia">
            <strong>⚠ Las fuentes oficiales no coinciden.</strong> Revisa el detalle abajo.
          </div>
        }

        <section class="estados">
          <h2>Lo que dice cada fuente oficial</h2>
          <div class="estados-grid">
            <div class="estado-card" [class.critico]="esCritico(o.estado_proyecto_mef)">
              <div class="estado-titulo">MEF / Invierte.pe</div>
              <div class="estado-valor">{{ o.estado_proyecto_mef || '—' }}</div>
              @if (o.avance_fisico_mef != null) {
                <div class="estado-detalle">Avance: {{ o.avance_fisico_mef }}%</div>
              }
              @if (o.url_mef_ssi) {
                <a [href]="o.url_mef_ssi" target="_blank" rel="noopener" class="estado-link">Verificar →</a>
              }
            </div>

            <div class="estado-card" [class.critico]="o.estado_obra_wfs === 'Paralizada'">
              <div class="estado-titulo">Contraloría WFS</div>
              <div class="estado-valor">{{ o.estado_obra_wfs || '— (sin feature)' }}</div>
              <div class="estado-detalle">Coordenadas oficiales</div>
              @if (o.url_infobras_informes) {
                <a [href]="o.url_infobras_informes" target="_blank" rel="noopener" class="estado-link">Ver informes →</a>
              }
            </div>

            <div class="estado-card">
              <div class="estado-titulo">Infobras (ficha)</div>
              <div class="estado-valor">{{ o.estado_obra_ficha || '—' }}</div>
              @if (o.avance_fisico_infobras != null) {
                <div class="estado-detalle">Avance: {{ o.avance_fisico_infobras }}%</div>
              }
              @if (o.url_infobras_ficha) {
                <a [href]="o.url_infobras_ficha" target="_blank" rel="noopener" class="estado-link">Verificar →</a>
              }
            </div>
          </div>
        </section>

        <section class="metricas">
          <h2>Métricas financieras</h2>
          <div class="metricas-grid">
            @if (o.mto_viable) {
              <div class="metrica">
                <div class="metrica-label">Monto viable</div>
                <div class="metrica-valor">S/ {{ fmtMonto(o.mto_viable) }}</div>
              </div>
            }
            @if (o.costo_actualizado) {
              <div class="metrica">
                <div class="metrica-label">Costo actualizado</div>
                <div class="metrica-valor">S/ {{ fmtMonto(o.costo_actualizado) }}</div>
              </div>
            }
            @if (o.sobrecosto_pct != null && +o.sobrecosto_pct > 0) {
              <div class="metrica" [class.critico]="+(o.sobrecosto_pct || 0) > 30">
                <div class="metrica-label">Sobrecosto</div>
                <div class="metrica-valor">{{ o.sobrecosto_pct }}%</div>
              </div>
            }
            @if (o.devengado_siaf) {
              <div class="metrica">
                <div class="metrica-label">Devengado SIAF</div>
                <div class="metrica-valor">S/ {{ fmtMonto(o.devengado_siaf) }}</div>
              </div>
            }
          </div>
        </section>

        @if (o.informes_control && o.informes_control.length > 0) {
          <section class="informes">
            <h2>Informes de Contraloría ({{ o.informes_control.length }})</h2>
            <ul>
              @for (inf of o.informes_control; track inf.nro_informe) {
                <li>
                  <strong>{{ inf.nro_informe }}</strong>
                  <span>{{ inf.tipo_servicio }} · {{ inf.modalidad }}</span>
                  @if (inf.url_pdf_completo) {
                    <a [href]="inf.url_pdf_completo" target="_blank" rel="noopener">Ver PDF →</a>
                  }
                </li>
              }
            </ul>
          </section>
        }

        @if (o.senales && o.senales.length > 0) {
          <section class="senales">
            <h2>Señales detectadas</h2>
            @for (s of o.senales; track s.tipo) {
              <article class="senal">
                <h3>{{ s.titulo }}</h3>
                <p>{{ s.resumen }}</p>
                @if (s.formula) {
                  <details><summary>Fórmula auditable</summary><code>{{ s.formula }}</code></details>
                }
              </article>
            }
          </section>
        }

      }
    </main>

    <!-- FAB flotante del chat (se muestra solo si hay obra cargada) -->
    @if (obra(); as o) {
      <app-chat-periodista [obraId]="o.id" />
    }
  `,
  styles: `
    .page { max-width: 920px; margin: 0 auto; padding: 24px 20px 60px; }
    .back { display: inline-block; margin-bottom: 24px; color: var(--ink-2, #555); text-decoration: none; font-size: 14px; }
    .back:hover { color: var(--terracotta, #9f5442); }
    .loading, .error { padding: 40px 0; text-align: center; color: var(--ink-2, #666); }
    .error { color: #b00; }

    .header { margin-bottom: 24px; padding-bottom: 20px; border-bottom: 1px solid #e5e5e5; }
    .ids { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
    .id-tag { font-size: 10px; padding: 3px 8px; background: #f5f5f4; color: #555; border-radius: 4px; font-weight: 500; letter-spacing: .04em; }
    .id-tag.saldo { background: #fef3c7; color: #92400e; }
    .header h1 { font-family: var(--font-serif, Georgia), serif; font-size: 26px; line-height: 1.2; color: #1c1917; margin: 0 0 8px; font-weight: 600; }
    .subtitle { color: #57534e; font-size: 14px; margin: 0; }

    .banner-discrepancia { background: rgba(159, 84, 66, 0.08); border: 1px solid rgba(159, 84, 66, 0.25); padding: 12px 16px; border-radius: 8px; color: #4a2d24; font-size: 14px; margin-bottom: 24px; }

    h2 { font-family: var(--font-serif, Georgia), serif; font-size: 18px; color: #1c1917; margin: 32px 0 14px; font-weight: 600; }

    .estados-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .estado-card { padding: 14px 16px; border: 1px solid #e5e5e5; border-radius: 8px; background: #fff; }
    .estado-card.critico { border-color: #9f5442; background: rgba(159, 84, 66, 0.05); }
    .estado-titulo { font-size: 11px; text-transform: uppercase; letter-spacing: .06em; color: #78716c; margin-bottom: 6px; font-weight: 600; }
    .estado-valor { font-size: 16px; color: #1c1917; font-weight: 600; }
    .estado-card.critico .estado-valor { color: #9f5442; }
    .estado-detalle { font-size: 12px; color: #57534e; margin-top: 4px; }
    .estado-link { display: inline-block; margin-top: 8px; font-size: 12px; color: #57534e; text-decoration: none; border-bottom: 1px solid transparent; }
    .estado-link:hover { color: #9f5442; border-bottom-color: #9f5442; }

    .metricas-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; }
    .metrica { padding: 14px 16px; border: 1px solid #e5e5e5; border-radius: 8px; background: #fafaf9; }
    .metrica.critico { background: #9f5442; color: #fafaf9; border-color: #9f5442; }
    .metrica-label { font-size: 10px; text-transform: uppercase; letter-spacing: .06em; opacity: 0.7; margin-bottom: 4px; font-weight: 600; }
    .metrica-valor { font-family: var(--font-serif, Georgia), serif; font-size: 18px; font-weight: 600; }

    .informes ul { list-style: none; padding: 0; margin: 0; }
    .informes li { padding: 10px 0; border-top: 1px solid #f5f5f4; display: flex; gap: 14px; align-items: baseline; flex-wrap: wrap; font-size: 13px; }
    .informes li strong { color: #1c1917; min-width: 180px; }
    .informes li span { color: #78716c; flex: 1; }
    .informes li a { color: #9f5442; text-decoration: none; }
    .informes li a:hover { text-decoration: underline; }

    .senal { padding: 12px 14px; border-left: 3px solid #9f5442; background: rgba(159, 84, 66, 0.04); border-radius: 0 6px 6px 0; margin-bottom: 10px; }
    .senal h3 { font-size: 14px; color: #1c1917; margin: 0 0 4px; font-weight: 600; }
    .senal p { font-size: 13px; color: #57534e; margin: 0; }
    .senal details { margin-top: 6px; font-size: 12px; }
    .senal code { font-size: 11px; color: #57534e; background: #f5f5f4; padding: 2px 6px; border-radius: 3px; }

    .chat-section { margin-top: 40px; padding-top: 24px; border-top: 2px solid #f5f5f4; }
    .chat-intro { font-size: 13px; color: #78716c; margin: 0 0 16px; }
  `,
})
export class ObraDetallePage {
  private readonly route = inject(ActivatedRoute);
  private readonly http = inject(HttpClient);
  private readonly apiBase = resolveApiBase();

  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly obra = signal<ObraFicha | null>(null);

  constructor() {
    this.route.paramMap.subscribe(params => {
      const id = Number(params.get('id'));
      if (!id) {
        this.error.set('ID de obra inválido');
        this.loading.set(false);
        return;
      }
      this.cargar(id);
    });
  }

  private cargar(id: number) {
    this.loading.set(true);
    this.error.set(null);
    this.http.get<ObraFicha>(`${this.apiBase}/api/obras/${id}`).subscribe({
      next: (o) => {
        this.obra.set(o);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('No se pudo cargar la obra. Intenta de nuevo.');
        this.loading.set(false);
      },
    });
  }

  protected esCritico(estado: string | null | undefined): boolean {
    if (!estado) return false;
    const u = estado.toUpperCase();
    return u.includes('DESACTIVA') || u.includes('PARALIZ');
  }

  protected hayDiscrepancia(o: ObraFicha): boolean {
    const mef = (o.estado_proyecto_mef || '').toUpperCase();
    const wfs = (o.estado_obra_wfs || '').toUpperCase();
    if (mef === 'ACTIVO' && wfs.includes('PARALIZ')) return true;
    if (mef.includes('DESACTIVA') && wfs.includes('EJECUCI')) return true;
    if (o.avance_fisico_mef != null && o.avance_fisico_infobras != null) {
      if (Math.abs(+o.avance_fisico_mef - +o.avance_fisico_infobras) > 10) return true;
    }
    return false;
  }

  protected fmtMonto(v: number | string | null | undefined): string {
    if (v == null) return '—';
    const n = typeof v === 'string' ? parseFloat(v) : v;
    return n.toLocaleString('es-PE', { maximumFractionDigits: 0 });
  }
}
