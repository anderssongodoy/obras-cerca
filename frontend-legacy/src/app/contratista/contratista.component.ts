import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../core/api.service';
import { ContratistaFicha } from '../core/models';

@Component({
  selector: 'app-contratista',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <main *ngIf="c() as ct" class="max-w-4xl mx-auto px-6 py-12">

      <nav class="text-sm text-stone-500 mb-6">
        <a routerLink="/" class="hover:text-stone-700">Inicio</a>
        <span class="mx-2">›</span>
        <span class="text-stone-700">Contratista</span>
      </nav>

      <header class="mb-10">
        <div class="flex items-center gap-2 mb-3">
          <span class="text-xs text-stone-500 uppercase tracking-wide">RUC {{ ct.ruc }}</span>
          <span *ngIf="ct.tiene_sancion_oece" class="text-xs px-2 py-0.5 bg-terracotta/10 text-terracotta rounded">
            Sancionado OECE
          </span>
        </div>
        <h1 class="font-serif text-3xl text-stone-900 mb-4">{{ ct.razon_social }}</h1>
      </header>

      <!-- Obras adjudicadas -->
      <section *ngIf="ct.obras?.length" class="mb-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">Obras adjudicadas ({{ ct.obras.length }})</h2>
        <div class="space-y-3">
          <a *ngFor="let o of ct.obras" [routerLink]="['/obra', o.id]"
             class="block p-4 bg-white border border-stone-200 rounded hover:border-stone-300 transition-colors">
            <div class="flex items-start justify-between gap-4">
              <div class="flex-1">
                <p class="font-serif text-base text-stone-900 mb-1">{{ (o.nombre || '').slice(0, 100) }}</p>
                <p class="text-sm text-stone-500">NOBR {{ o.nobr_id }} · {{ o.distrito || '—' }}</p>
              </div>
              <div class="text-right">
                <span class="text-xs px-2 py-1 rounded"
                      [class.bg-terracotta]="o.estado_obra_wfs === 'Paralizada'"
                      [class.text-white]="o.estado_obra_wfs === 'Paralizada'"
                      [class.bg-stone-100]="o.estado_obra_wfs !== 'Paralizada'"
                      [class.text-stone-700]="o.estado_obra_wfs !== 'Paralizada'">
                  {{ o.estado_obra_wfs || '—' }}
                </span>
                <p class="text-sm text-terracotta mt-1">{{ o.avance_fisico_infobras ?? 0 }}% avance</p>
              </div>
            </div>
          </a>
        </div>
      </section>

      <!-- Procedimientos SEACE -->
      <section *ngIf="ct.procedimientos?.length" class="mb-10">
        <h2 class="font-serif text-2xl text-stone-900 mb-4">Procedimientos SEACE</h2>
        <div class="space-y-3">
          <div *ngFor="let p of ct.procedimientos" class="p-4 bg-white border border-stone-200 rounded">
            <p class="text-sm text-stone-500 mb-1">{{ p.nomenclatura }}</p>
            <div class="flex flex-wrap items-center justify-between gap-4">
              <p class="font-serif text-lg text-stone-900" *ngIf="p.monto_contratado">
                S/ {{ p.monto_contratado | number:'1.0-0' }}
              </p>
              <p class="text-sm text-stone-500" *ngIf="p.fecha_buena_pro">
                Buena pro: {{ formatDate(p.fecha_buena_pro) }}
              </p>
              <a *ngIf="p.url_contrato_pdf" [href]="p.url_contrato_pdf" target="_blank" rel="noopener"
                 class="text-xs text-terracotta hover:underline">Ver PDF →</a>
            </div>
          </div>
        </div>
      </section>

      <p *ngIf="!ct.obras?.length && !ct.procedimientos?.length" class="text-stone-500 italic">
        Aún no tenemos obras ni procedimientos cargados para este RUC.
      </p>
    </main>
  `,
})
export class ContratistaComponent implements OnInit {
  private api = inject(ApiService);
  private route = inject(ActivatedRoute);
  c = signal<ContratistaFicha | null>(null);

  ngOnInit(): void {
    const ruc = this.route.snapshot.paramMap.get('ruc')!;
    this.api.contratista(ruc).subscribe(c => this.c.set(c));
  }

  formatDate(d: string): string {
    if (!d) return '';
    try {
      return new Date(d).toLocaleDateString('es-PE', { day: 'numeric', month: 'short', year: 'numeric' });
    } catch { return d; }
  }
}
