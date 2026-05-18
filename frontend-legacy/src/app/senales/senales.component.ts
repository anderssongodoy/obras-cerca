import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { Senal } from '../core/models';

@Component({
  selector: 'app-senales',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main class="max-w-4xl mx-auto px-6 py-12">
      <header class="mb-8">
        <h1 class="font-serif text-3xl text-stone-900 mb-3">Señales de revisión</h1>
        <p class="text-stone-600 max-w-2xl">
          Cada señal es una anomalía detectada automáticamente al cruzar fuentes oficiales:
          contradicciones entre sistemas, sobrecostos atípicos, paralizaciones no declaradas,
          concentración irregular en compras menores. Priorizadas por severidad.
        </p>
      </header>

      <!-- Filtros por tipo -->
      <div class="flex flex-wrap gap-2 mb-8">
        <button (click)="filtro.set(null)"
                [class.bg-stone-900]="filtro() === null"
                [class.text-stone-50]="filtro() === null"
                [class.bg-stone-100]="filtro() !== null"
                [class.text-stone-600]="filtro() !== null"
                class="px-3 py-1.5 text-sm rounded transition-colors hover:opacity-80">
          Todas ({{ senales().length }})
        </button>
        <button *ngFor="let t of tipos()" (click)="filtro.set(t)"
                [class.bg-stone-900]="filtro() === t"
                [class.text-stone-50]="filtro() === t"
                [class.bg-stone-100]="filtro() !== t"
                [class.text-stone-600]="filtro() !== t"
                class="px-3 py-1.5 text-sm rounded transition-colors hover:opacity-80">
          {{ tipoLabel(t) }} ({{ contar(t) }})
        </button>
      </div>

      <!-- Lista -->
      <div *ngIf="filtradas().length === 0" class="text-center py-16">
        <p class="text-stone-500 mb-2">No hay señales con este filtro.</p>
        <button (click)="filtro.set(null)" class="text-terracotta hover:underline text-sm">
          Ver todas las señales
        </button>
      </div>

      <div class="space-y-0">
        <article *ngFor="let s of filtradas()"
                 class="border-b border-stone-200 py-8 first:pt-0 last:border-b-0 cursor-pointer hover:bg-stone-50/50 -mx-6 px-6 transition-colors"
                 [routerLink]="s.obra_id ? ['/obra', s.obra_id] : (getEvidenciaRuc(s) ? ['/contratista', getEvidenciaRuc(s)] : null)">
          <div class="flex items-start gap-4">
            <div class="flex-1">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-xs text-stone-500 uppercase tracking-wide">{{ tipoLabel(s.tipo) }}</span>
                <span class="text-xs text-stone-400">·</span>
                <span class="text-xs text-stone-500">{{ formatDate(s.detectada_en) }}</span>
              </div>
              <h2 class="font-serif text-xl text-stone-900 mb-3 leading-tight">{{ s.titulo }}</h2>
              <p class="text-stone-600 leading-relaxed mb-4">{{ s.resumen }}</p>
              <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-stone-500">
                <span *ngIf="s.distrito">📍 {{ s.distrito }}</span>
                <span *ngIf="s.entidad">·  {{ s.entidad }}</span>
                <span *ngIf="s.contratista">·  {{ s.contratista }}</span>
              </div>
            </div>
            <div *ngIf="s.score" class="text-right shrink-0">
              <p class="text-2xl font-serif text-terracotta">{{ formatScore(s) }}</p>
              <p class="text-xs text-stone-500">{{ scoreLabel(s.tipo) }}</p>
            </div>
          </div>
        </article>
      </div>
    </main>
  `,
})
export class SenalesComponent implements OnInit {
  private api = inject(ApiService);
  senales = signal<Senal[]>([]);
  filtro = signal<string | null>(null);

  tipos = computed(() => Array.from(new Set(this.senales().map(s => s.tipo))));
  filtradas = computed(() => {
    const f = this.filtro();
    return f ? this.senales().filter(s => s.tipo === f) : this.senales();
  });

  ngOnInit(): void {
    this.api.senales({ limit: 200 }).subscribe(s => this.senales.set(s));
  }

  contar(t: string): number { return this.senales().filter(s => s.tipo === t).length; }
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

  formatDate(d: string): string {
    if (!d) return '';
    try {
      return new Date(d).toLocaleDateString('es-PE', { day: 'numeric', month: 'long', year: 'numeric' });
    } catch { return d; }
  }

  getEvidenciaRuc(s: any): string {
    return s?.evidencia?.ruc || s?.contratista_ruc || '';
  }
}
