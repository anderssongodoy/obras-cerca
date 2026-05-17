import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { ApiService } from '../core/api.service';
import { ObraFicha, VerificacionLive } from '../core/models';

@Component({
  selector: 'app-obra',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main *ngIf="obra() as o" class="max-w-4xl mx-auto px-6 py-12">

      <!-- Breadcrumb -->
      <nav class="text-sm text-stone-500 mb-6">
        <a routerLink="/" class="hover:text-stone-700">Inicio</a>
        <span class="mx-2">›</span>
        <a routerLink="/mapa" class="hover:text-stone-700">Mapa</a>
        <span class="mx-2">›</span>
        <span class="text-stone-700">{{ o.distrito_nombre }}</span>
      </nav>

      <!-- Cabecera -->
      <header class="mb-10">
        <div class="flex items-center gap-2 mb-3 flex-wrap">
          <span class="text-xs text-stone-500 uppercase tracking-wide">
            CUI {{ o.cui }} · NOBR {{ o.nobr_id }}
          </span>
          <span *ngIf="o.senales?.length" class="text-xs px-2 py-0.5 bg-terracotta/10 text-terracotta rounded">
            {{ o.senales!.length }} {{ o.senales!.length === 1 ? 'señal' : 'señales' }}
          </span>
          <span *ngIf="o.es_saldo_obra" class="text-xs px-2 py-0.5 bg-stone-100 text-stone-700 rounded">
            Saldo de obra
          </span>
        </div>

        <h1 class="font-serif text-3xl md:text-4xl text-stone-900 leading-tight mb-4">
          {{ o.nombre_obra || o.nombre_inversion || '(Obra sin nombre registrado)' }}
        </h1>

        <div class="flex flex-wrap items-center gap-x-4 gap-y-2 text-stone-600">
          <span *ngIf="o.entidad_nombre">{{ o.entidad_nombre }}</span>
          <span class="text-stone-300" *ngIf="o.entidad_nombre">·</span>
          <span>{{ o.distrito_nombre }}<span *ngIf="o.provincia">, {{ o.provincia }}</span></span>
          <span *ngIf="o.fecha_inicio_mef" class="text-stone-300">·</span>
          <span *ngIf="o.fecha_inicio_mef">Inicio: {{ formatDate(o.fecha_inicio_mef) }}</span>
        </div>
      </header>

      <!-- Narrativa principal -->
      <section class="prose prose-stone max-w-none mb-10">
        <p class="text-lg leading-relaxed text-stone-700">{{ narrativa() }}</p>
      </section>

      <!-- ⭐ Panel de Contradicciones — lo que dice CADA fuente oficial -->
      <section class="mb-10 bg-stone-50 border border-stone-200 rounded-lg p-6">
        <h3 class="font-serif text-lg text-stone-900 mb-4">Lo que dice cada fuente oficial</h3>
        <p class="text-sm text-stone-600 mb-6">
          Tres sistemas del Estado peruano, posiblemente tres versiones distintas.
          Las contradicciones no son errores nuestros — son lo que el gobierno publica.
        </p>

        <div class="grid md:grid-cols-3 gap-4">
          <!-- MEF -->
          <div class="bg-white border rounded p-4"
               [class.border-terracotta]="esContradictorio(o.estado_proyecto_mef)"
               [class.border-stone-200]="!esContradictorio(o.estado_proyecto_mef)">
            <div class="flex items-center gap-2 mb-3">
              <div class="w-2 h-2 rounded-full"
                   [class.bg-terracotta]="esContradictorio(o.estado_proyecto_mef)"
                   [class.bg-stone-400]="!esContradictorio(o.estado_proyecto_mef)"></div>
              <span class="text-xs font-medium text-stone-500 uppercase tracking-wide">MEF / Invierte.pe</span>
            </div>
            <p class="font-serif text-lg mb-2"
               [class.text-terracotta]="esContradictorio(o.estado_proyecto_mef)"
               [class.text-stone-900]="!esContradictorio(o.estado_proyecto_mef)">
              {{ o.estado_proyecto_mef || '—' }}
            </p>
            <div class="space-y-1 text-sm text-stone-600">
              <p *ngIf="o.avance_fisico_mef !== null">Avance físico: {{ o.avance_fisico_mef }}%</p>
              <p *ngIf="o.devengado_siaf">Devengado SIAF: S/ {{ o.devengado_siaf | number:'1.0-0' }}</p>
            </div>
            <a [href]="o.url_mef_ssi" target="_blank" rel="noopener" class="inline-block mt-3 text-xs text-terracotta hover:underline">
              Verificar en MEF →
            </a>
          </div>

          <!-- Contraloría WFS -->
          <div class="bg-white border rounded p-4"
               [class.border-terracotta]="o.estado_obra_wfs === 'Paralizada'"
               [class.border-stone-200]="o.estado_obra_wfs !== 'Paralizada'">
            <div class="flex items-center gap-2 mb-3">
              <div class="w-2 h-2 rounded-full"
                   [class.bg-terracotta]="o.estado_obra_wfs === 'Paralizada'"
                   [class.bg-stone-400]="o.estado_obra_wfs !== 'Paralizada'"></div>
              <span class="text-xs font-medium text-stone-500 uppercase tracking-wide">Contraloría WFS</span>
            </div>
            <p class="font-serif text-lg mb-2"
               [class.text-terracotta]="o.estado_obra_wfs === 'Paralizada'"
               [class.text-stone-900]="o.estado_obra_wfs !== 'Paralizada'">
              {{ o.estado_obra_wfs || '— (sin feature)' }}
            </p>
            <div class="space-y-1 text-sm text-stone-600">
              <p *ngIf="o.geom_fuente === 'wfs_infobras'" class="text-xs">
                Coordenadas oficiales Contraloría
              </p>
            </div>
            <a [href]="o.url_infobras_informes" target="_blank" rel="noopener" class="inline-block mt-3 text-xs text-terracotta hover:underline">
              Ver informes de control →
            </a>
          </div>

          <!-- Infobras Ficha -->
          <div class="bg-white border border-stone-200 rounded p-4">
            <div class="flex items-center gap-2 mb-3">
              <div class="w-2 h-2 rounded-full bg-stone-400"></div>
              <span class="text-xs font-medium text-stone-500 uppercase tracking-wide">Infobras ficha pública</span>
            </div>
            <p class="font-serif text-lg text-stone-900 mb-2">{{ o.estado_obra_ficha || '—' }}</p>
            <div class="space-y-1 text-sm text-stone-600">
              <p *ngIf="o.avance_fisico_infobras !== null">Avance físico: {{ o.avance_fisico_infobras }}%</p>
              <p *ngIf="o.fecha_ult_avance">Último avance: {{ formatDate(o.fecha_ult_avance) }}</p>
            </div>
            <a [href]="o.url_infobras_ficha" target="_blank" rel="noopener" class="inline-block mt-3 text-xs text-terracotta hover:underline">
              Verificar en Infobras →
            </a>
          </div>
        </div>

        <div *ngIf="hayDiscrepancia()" class="mt-6 p-4 bg-terracotta/5 border border-terracotta/20 rounded">
          <p class="text-sm text-stone-700">
            <strong class="text-terracotta">Discrepancia detectada:</strong>
            {{ describeDiscrepancia() }}
          </p>
        </div>
      </section>

      <!-- Botón verificación LIVE -->
      <div class="mb-10">
        <button (click)="abrirVerificacion()"
                class="inline-flex items-center gap-2 px-4 py-2 border border-stone-300 rounded text-stone-700 hover:bg-stone-100 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
          Verificar ahora (consulta en vivo a MEF + Contraloría)
        </button>
        <p class="text-xs text-stone-500 mt-2">
          Consulta las APIs oficiales en tiempo real para confirmar que estos datos siguen vigentes.
        </p>
      </div>

      <!-- KPI grid -->
      <section class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-10">
        <div class="bg-white border border-stone-200 rounded p-5">
          <p class="text-xs text-stone-500 uppercase tracking-wide mb-2">Monto Viable</p>
          <p class="font-serif text-2xl text-stone-900">{{ o.mto_viable ? ('S/ ' + (o.mto_viable | number:'1.0-0')) : '—' }}</p>
        </div>
        <div class="bg-white border border-stone-200 rounded p-5">
          <p class="text-xs text-stone-500 uppercase tracking-wide mb-2">Costo Actualizado</p>
          <p class="font-serif text-2xl text-stone-900">{{ o.costo_actualizado ? ('S/ ' + (o.costo_actualizado | number:'1.0-0')) : '—' }}</p>
        </div>
        <div class="bg-white border rounded p-5"
             [class.border-terracotta]="(o.sobrecosto_pct ?? 0) > 30"
             [class.border-stone-200]="(o.sobrecosto_pct ?? 0) <= 30">
          <p class="text-xs text-stone-500 uppercase tracking-wide mb-2">Sobrecosto</p>
          <p class="font-serif text-2xl"
             [class.text-terracotta]="(o.sobrecosto_pct ?? 0) > 30"
             [class.text-stone-900]="(o.sobrecosto_pct ?? 0) <= 30">
            {{ o.sobrecosto_pct !== null ? (o.sobrecosto_pct + '%') : '—' }}
          </p>
        </div>
      </section>

      <!-- Saldos de obra -->
      <section *ngIf="o.saldos_hijos?.length" class="mb-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">Saldos de obra pendientes</h2>
        <p class="text-stone-600 mb-6">
          Cuando un contrato se resuelve, la obra queda dividida en "saldos" que deben licitarse de nuevo.
          Esta obra tiene {{ o.saldos_hijos!.length }} {{ o.saldos_hijos!.length === 1 ? 'saldo' : 'saldos' }}.
        </p>
        <div class="space-y-3">
          <div *ngFor="let s of o.saldos_hijos" class="p-4 bg-stone-50 border border-stone-200 rounded hover:border-stone-300 cursor-pointer"
               [routerLink]="['/obra', s.id]">
            <div class="flex items-start justify-between">
              <div>
                <p class="font-medium text-stone-900">{{ (s.descripcion || 'Saldo de obra').slice(0, 80) }}</p>
                <p class="text-sm text-stone-500">NOBR {{ s.nobr_id }}</p>
              </div>
              <div class="text-right">
                <p class="font-medium text-stone-900" *ngIf="s.monto_contrato">S/ {{ s.monto_contrato | number:'1.0-0' }}</p>
                <p class="text-sm text-terracotta">{{ s.avance_fisico_infobras ?? 0 }}% avance</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Informes Contraloría -->
      <section *ngIf="o.informes_control?.length" class="mb-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">
          Informes de Contraloría ({{ o.informes_control!.length }})
        </h2>
        <div class="space-y-3">
          <a *ngFor="let inf of o.informes_control" [href]="inf.url_pdf_completo || inf.url_pdf_resumen" target="_blank" rel="noopener"
             class="flex items-center justify-between p-4 bg-white border border-stone-200 rounded hover:border-stone-300 transition-colors">
            <div>
              <p class="font-medium text-stone-900">{{ inf.nro_informe }}</p>
              <p class="text-sm text-stone-500">{{ inf.tipo_servicio }} · {{ inf.modalidad }}</p>
            </div>
            <div class="flex items-center gap-3">
              <span class="text-sm text-stone-500" *ngIf="inf.fecha_publicacion">{{ formatDate(inf.fecha_publicacion) }}</span>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="text-stone-400">
                <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                <path d="M15 3h6v6" /><path d="M10 14L21 3" />
              </svg>
            </div>
          </a>
        </div>
      </section>

      <!-- Procedimientos SEACE -->
      <section *ngIf="o.procedimientos?.length" class="mb-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">Contratos SEACE</h2>
        <div class="space-y-3">
          <div *ngFor="let p of o.procedimientos" class="p-4 bg-white border border-stone-200 rounded">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1">
                <p class="text-sm text-stone-500 mb-1">{{ p.nomenclatura || '(sin nomenclatura)' }}</p>
                <a *ngIf="p.contratista_ruc" [routerLink]="['/contratista', p.contratista_ruc]" class="font-medium text-stone-900 hover:text-terracotta">
                  {{ p.contratista }}
                </a>
                <p *ngIf="!p.contratista_ruc" class="font-medium text-stone-900">{{ p.contratista || '—' }}</p>
                <p class="text-sm text-stone-500 mt-1" *ngIf="p.fecha_buena_pro">Buena pro: {{ formatDate(p.fecha_buena_pro) }}</p>
              </div>
              <div class="text-right">
                <p class="font-serif text-lg text-stone-900" *ngIf="p.monto_contratado">S/ {{ p.monto_contratado | number:'1.0-0' }}</p>
                <a *ngIf="p.url_contrato_pdf" [href]="p.url_contrato_pdf" target="_blank" rel="noopener" class="text-xs text-terracotta hover:underline">
                  Ver PDF →
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Señales con fórmula -->
      <section *ngIf="o.senales?.length" class="mb-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">Señales detectadas</h2>
        <div class="space-y-4">
          <div *ngFor="let s of o.senales" class="p-4 bg-terracotta/5 border border-terracotta/20 rounded">
            <p class="font-medium text-stone-900 mb-1">{{ s.titulo }}</p>
            <p class="text-stone-700 mb-2">{{ s.resumen }}</p>
            <details>
              <summary class="text-xs text-terracotta hover:underline cursor-pointer">Ver fórmula auditable</summary>
              <p class="mt-2 text-xs text-stone-600 font-mono bg-white border border-stone-200 px-3 py-2 rounded">
                {{ s.formula }}
              </p>
            </details>
          </div>
        </div>
      </section>

      <!-- Acciones de salida -->
      <section class="flex flex-wrap gap-3 pt-6 border-t border-stone-200">
        <a [href]="exportarCsvUrl()" class="inline-flex items-center gap-2 px-4 py-2 bg-stone-900 text-stone-50 rounded hover:bg-stone-800 transition-colors">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
            <path d="M7 10l5 5 5-5" /><path d="M12 15V3" />
          </svg>
          Exportar evidencia (CSV)
        </a>
      </section>
    </main>

    <!-- Modal Verificación LIVE -->
    <div *ngIf="verifiOpen()" class="fixed inset-0 bg-stone-900/50 flex items-center justify-center z-50 p-4" (click)="cerrarVerificacion()">
      <div class="bg-white rounded-lg max-w-md w-full p-6" (click)="$event.stopPropagation()">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-serif text-lg text-stone-900">Verificación en tiempo real</h3>
          <button (click)="cerrarVerificacion()" class="text-stone-400 hover:text-stone-600">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
        <p class="text-sm text-stone-600 mb-6">
          Consultando las APIs oficiales del Estado peruano. <strong>No es caché</strong> — viene directo de los servidores oficiales.
        </p>

        <div class="space-y-3">
          <div class="flex items-center gap-3">
            <div class="w-4 h-4 rounded-full flex items-center justify-center"
                 [class.bg-emerald-500]="verifResultados()?.mef_invierte_pe"
                 [class.bg-stone-200]="!verifResultados()?.mef_invierte_pe">
              <svg *ngIf="verifResultados()?.mef_invierte_pe" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <span class="text-sm text-stone-700">MEF / Invierte.pe</span>
            <span class="text-xs text-stone-500 ml-auto" *ngIf="verifResultados()?.mef_invierte_pe?.ESTADO">
              {{ verifResultados()!.mef_invierte_pe.ESTADO }}
            </span>
          </div>

          <div class="flex items-center gap-3">
            <div class="w-4 h-4 rounded-full flex items-center justify-center"
                 [class.bg-terracotta]="verifResultados()?.infobras_wfs"
                 [class.bg-stone-200]="!verifResultados()?.infobras_wfs">
              <svg *ngIf="verifResultados()?.infobras_wfs" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <span class="text-sm text-stone-700">Contraloría WFS</span>
            <span class="text-xs text-terracotta ml-auto" *ngIf="verifResultados()?.infobras_wfs?.estado">
              {{ verifResultados()!.infobras_wfs.estado }}
            </span>
          </div>

          <div class="flex items-center gap-3">
            <div class="w-4 h-4 rounded-full flex items-center justify-center"
                 [class.bg-emerald-500]="verifResultados()?.infobras_ficha_publica"
                 [class.bg-stone-200]="!verifResultados()?.infobras_ficha_publica">
              <svg *ngIf="verifResultados()?.infobras_ficha_publica" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3">
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <span class="text-sm text-stone-700">Infobras ficha pública</span>
            <span class="text-xs text-stone-500 ml-auto" *ngIf="verifResultados()?.infobras_ficha_publica?.['ESTADO DE OBRA']">
              {{ verifResultados()!.infobras_ficha_publica['ESTADO DE OBRA'] }}
            </span>
          </div>
        </div>

        <div *ngIf="verifEstado() === 'done'" class="mt-6 p-4 bg-terracotta/5 border border-terracotta/20 rounded">
          <p class="text-sm text-stone-700">
            <strong class="text-terracotta">Confirmado:</strong> verificado a las {{ verifTimestamp() }} contra los servidores oficiales.
          </p>
        </div>
        <p *ngIf="verifEstado() === 'loading'" class="text-xs text-stone-400 mt-6 text-center">
          Consultando servidores del gobierno peruano...
        </p>
      </div>
    </div>
  `,
})
export class ObraComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);

  obra = signal<ObraFicha | null>(null);
  verifiOpen = signal(false);
  verifEstado = signal<'loading' | 'done'>('loading');
  verifResultados = signal<any | null>(null);
  verifTimestamp = signal<string>('');

  ngOnInit(): void {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    this.api.obra(id).subscribe(o => this.obra.set(o));
  }

  abrirVerificacion() {
    this.verifiOpen.set(true);
    this.verifEstado.set('loading');
    this.verifResultados.set(null);
    const id = this.obra()?.id;
    if (!id) return;
    this.api.verificarLive(id).subscribe(v => {
      this.verifResultados.set(v.fuentes);
      this.verifEstado.set('done');
      this.verifTimestamp.set(new Date().toLocaleTimeString('es-PE'));
    });
  }

  cerrarVerificacion() { this.verifiOpen.set(false); }

  narrativa(): string {
    const o = this.obra(); if (!o) return '';
    const partes: string[] = [];
    if (o.fecha_inicio_mef) {
      const años = Math.max(0, new Date().getFullYear() - new Date(o.fecha_inicio_mef).getFullYear());
      if (años > 2) partes.push(`Esta obra lleva ${años} años desde su inicio.`);
    }
    if (o.sobrecosto_pct !== null && o.sobrecosto_pct! > 30) {
      partes.push(`El presupuesto pasó de S/ ${this.fmt(o.mto_viable)} a S/ ${this.fmt(o.costo_actualizado)} — un sobrecosto del ${o.sobrecosto_pct}%.`);
    }
    if (o.estado_proyecto_mef === 'DESACTIVADO_PERMANENTE') {
      partes.push(`El MEF la marca como DESACTIVADO PERMANENTE. El proyecto está oficialmente cerrado.`);
    }
    if (o.estado_obra_wfs === 'Paralizada') {
      partes.push(`Contraloría WFS confirma que está paralizada hoy.`);
    }
    if ((o.saldos_hijos?.length || 0) > 0) {
      partes.push(`Tiene ${o.saldos_hijos!.length} ${o.saldos_hijos!.length === 1 ? 'saldo' : 'saldos'} de obra — indicio de que el contrato original quedó inconcluso.`);
    }
    if (partes.length === 0) return o.nombre_obra || o.nombre_inversion || '';
    return partes.join(' ');
  }

  hayDiscrepancia(): boolean {
    const o = this.obra(); if (!o) return false;
    const mef = (o.estado_proyecto_mef || '').toUpperCase();
    const wfs = (o.estado_obra_wfs || '').toUpperCase();
    const inf = (o.estado_obra_ficha || '').toUpperCase();
    const conflicto1 = mef === 'ACTIVO' && wfs.includes('PARALIZ');
    const conflicto2 = mef.includes('DESACTIVA') && (inf.includes('EJECUCI') || wfs.includes('EJECUCI'));
    const conflicto3 = o.avance_fisico_mef !== null && o.avance_fisico_infobras !== null
                       && Math.abs(Number(o.avance_fisico_mef) - Number(o.avance_fisico_infobras)) > 10;
    return conflicto1 || conflicto2 || conflicto3;
  }

  describeDiscrepancia(): string {
    const o = this.obra(); if (!o) return '';
    const partes: string[] = [];
    if ((o.estado_proyecto_mef || '').toUpperCase() === 'ACTIVO' && (o.estado_obra_wfs || '').toUpperCase().includes('PARALIZ')) {
      partes.push('MEF la considera activa, pero Contraloría WFS la tiene paralizada.');
    }
    if ((o.estado_proyecto_mef || '').includes('DESACTIVA') && ((o.estado_obra_ficha || '').toUpperCase().includes('EJECUCI') || (o.estado_obra_wfs || '').toUpperCase().includes('EJECUCI'))) {
      partes.push('MEF la dio de baja, pero Infobras la sigue mostrando como activa.');
    }
    if (o.avance_fisico_mef !== null && o.avance_fisico_infobras !== null) {
      const diff = Math.abs(Number(o.avance_fisico_mef) - Number(o.avance_fisico_infobras));
      if (diff > 10) partes.push(`MEF reporta ${o.avance_fisico_mef}% de avance, Infobras ${o.avance_fisico_infobras}% — diferencia de ${diff.toFixed(1)} puntos.`);
    }
    return partes.join(' ');
  }

  esContradictorio(e: string | null | undefined): boolean {
    if (!e) return false;
    const u = e.toUpperCase();
    return u.includes('PARALIZ') || u.includes('DESACTIVA');
  }

  fmt(n: number | null | undefined): string {
    if (!n) return '—';
    return Number(n).toLocaleString('es-PE', { maximumFractionDigits: 0 });
  }

  formatDate(d: string | null | undefined): string {
    if (!d) return '';
    try {
      return new Date(d).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch { return String(d); }
  }

  exportarCsvUrl(): string {
    return `http://localhost:8000/api/obras/${this.obra()?.id}/exportar`;
  }
}
