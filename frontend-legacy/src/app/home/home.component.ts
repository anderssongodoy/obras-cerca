import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { Stats, Senal } from '../core/models';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="max-w-4xl mx-auto px-6 py-12">

      <!-- Cabecera editorial -->
      <div class="mb-12">
        <p class="text-sm text-stone-500 uppercase tracking-wide mb-2">
          Transparencia ciudadana
        </p>
        <h1 class="font-serif text-4xl md:text-5xl text-stone-900 leading-tight mb-6">
          El Estado peruano tiene
          <span class="text-terracotta">{{ formatMoney(montoParalizado()) }}</span>
          en obras paralizadas
        </h1>
        <p class="text-lg text-stone-600 leading-relaxed max-w-2xl">
          Cruzamos tres fuentes oficiales — MEF/Invierte.pe, Contraloría e Infobras — y mostramos las contradicciones.
          Cuando el gobierno dice una cosa de sí mismo en un portal y otra cosa en otro, lo señalamos.
        </p>
      </div>

      <!-- Resumen compacto -->
      <div *ngIf="stats() as s" class="flex flex-wrap gap-x-8 gap-y-2 text-sm text-stone-600 mb-12 pb-8 border-b border-stone-200">
        <span><strong class="text-stone-900">{{ s.totales.proyectos | number }}</strong> proyectos</span>
        <span><strong class="text-stone-900">{{ s.totales.obras | number }}</strong> obras</span>
        <span><strong class="text-terracotta">{{ s.totales.obras_paralizadas_wfs }}</strong> paralizadas (WFS)</span>
        <span><strong class="text-terracotta">{{ s.totales.proyectos_desactivados }}</strong> desactivadas MEF</span>
        <span><strong class="text-stone-900">{{ s.totales.informes_control }}</strong> informes de Contraloría</span>
        <span><strong class="text-terracotta">{{ s.totales.senales_activas }}</strong> señales activas</span>
      </div>

      <!-- Señales recientes -->
      <section>
        <div class="flex items-center justify-between mb-6">
          <h2 class="font-serif text-2xl text-stone-900">Señales recientes</h2>
          <a routerLink="/senales" class="text-sm text-terracotta hover:underline">
            Ver todas →
          </a>
        </div>

        <div *ngIf="senales().length === 0" class="text-stone-500 italic py-8">
          No hay señales aún. Para llenar la BD corre los scripts del backend
          (<code class="bg-stone-100 px-1 rounded">00_ingesta_demo.py</code> + <code class="bg-stone-100 px-1 rounded">06_generar_senales.py</code>).
        </div>

        <article *ngFor="let s of senales().slice(0, 8)"
                 class="border-b border-stone-200 py-8 first:pt-0 last:border-b-0 cursor-pointer hover:bg-stone-50/50 -mx-6 px-6 transition-colors"
                 [routerLink]="s.obra_id ? ['/obra', s.obra_id] : (s.contratista ? ['/contratista', getEvidenciaRuc(s)] : null)">
          <div class="flex items-start gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-xs text-stone-500 uppercase tracking-wide">
                  {{ tipoLabel(s.tipo) }}
                </span>
                <span class="text-xs text-stone-400">·</span>
                <span class="text-xs text-stone-500">{{ formatDate(s.detectada_en) }}</span>
              </div>
              <h3 class="font-serif text-xl text-stone-900 mb-3 leading-tight">{{ s.titulo }}</h3>
              <p class="text-stone-600 leading-relaxed mb-4">{{ s.resumen }}</p>

              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-stone-500">
                <span *ngIf="s.distrito">📍 {{ s.distrito }}</span>
                <span *ngIf="s.entidad">·  {{ s.entidad }}</span>
                <span *ngIf="s.contratista">·  {{ s.contratista }}</span>
              </div>
            </div>

            <div *ngIf="s.score !== null" class="text-right shrink-0">
              <p class="text-2xl font-serif text-terracotta">{{ formatScore(s) }}</p>
              <p class="text-xs text-stone-500">{{ scoreLabel(s.tipo) }}</p>
            </div>
          </div>
        </article>
      </section>

    </main>
  `,
})
export class HomeComponent implements OnInit {
  private api = inject(ApiService);
  stats = signal<Stats | null>(null);
  senales = signal<Senal[]>([]);

  montoParalizado = computed(() => {
    const s = this.stats();
    return s ? (s.totales as any).monto_paralizado || 0 : 43000000000;
  });

  ngOnInit(): void {
    this.api.stats().subscribe(s => this.stats.set(s));
    this.api.senales({ limit: 30 }).subscribe(s => this.senales.set(s));
  }

  formatMoney(n: number): string {
    if (!n) return 'miles de millones de soles';
    if (n >= 1_000_000_000) return `S/${(n / 1_000_000_000).toFixed(1)} mil millones`;
    if (n >= 1_000_000) return `S/${(n / 1_000_000).toFixed(1)} millones`;
    return `S/${n.toLocaleString('es-PE')}`;
  }

  formatDate(d: string): string {
    if (!d) return '';
    try {
      return new Date(d).toLocaleDateString('es-PE', { day: 'numeric', month: 'long', year: 'numeric' });
    } catch { return d; }
  }

  tipoLabel(t: string): string { return (t || '').replace(/_/g, ' '); }

  scoreLabel(tipo: string): string {
    if (tipo === 'sobrecosto') return 'sobrecosto';
    if (tipo === 'discrepancia_avance') return 'diferencia';
    if (tipo === 'concentracion_menores') return '% concentración';
    if (tipo === 'paralizacion_real') return 'verificada WFS';
    if (tipo === 'inactiva_mef') return 'desactivada';
    return 'score';
  }

  formatScore(s: any): string {
    if (!s.score) return '—';
    const tipo = s.tipo;
    if (tipo === 'sobrecosto' || tipo === 'discrepancia_avance' || tipo === 'concentracion_menores') {
      return `${Math.round(s.score)}%`;
    }
    return String(s.score);
  }

  getEvidenciaRuc(s: any): string {
    return s?.evidencia?.ruc || s?.contratista_ruc || '';
  }
}
