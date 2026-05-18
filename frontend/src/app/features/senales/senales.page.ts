import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { SenalesPageService } from '../../core/services/senales-page.service';
import { formatDate, formatScore, scoreLabel, tipoLabel } from '../../shared/utils/senal-format';

import { Topbar } from '../mapa/components/topbar/topbar';

@Component({
  selector: 'app-senales-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Topbar],
  templateUrl: './senales.page.html',
  styleUrl: './senales.page.scss',
})
export class SenalesPage {
  readonly svc = inject(SenalesPageService);

  readonly senales = this.svc.senales;
  readonly loading = this.svc.isLoading;
  readonly error = this.svc.error;

  readonly filtro = signal<string | null>(null);
  readonly page = signal(1);
  readonly pageSize = 8;

  readonly tipos = computed(() => Array.from(new Set((this.senales() ?? []).map((senal) => senal.tipo))));

  readonly filtradas = computed(() => {
    const filtro = this.filtro();
    const lista = this.senales() ?? [];
    return filtro ? lista.filter((senal) => senal.tipo === filtro) : lista;
  });

  readonly totalFiltradas = computed(() => this.filtradas().length);

  readonly totalPages = computed(() => {
    const total = this.totalFiltradas();
    return total > 0 ? Math.ceil(total / this.pageSize) : 1;
  });

  readonly currentPage = computed(() => this.clampPage(this.page()));

  readonly paginadas = computed(() => {
    const pagina = this.currentPage();
    const inicio = (pagina - 1) * this.pageSize;
    const fin = inicio + this.pageSize;
    return this.filtradas().slice(inicio, fin);
  });

  readonly rangoActual = computed(() => {
    const total = this.totalFiltradas();
    if (total === 0) {
      return { inicio: 0, fin: 0, total };
    }

    const inicio = (this.currentPage() - 1) * this.pageSize + 1;
    const fin = Math.min(inicio + this.pageSize - 1, total);
    return { inicio, fin, total };
  });

  protected readonly tipoLabel = tipoLabel;
  protected readonly scoreLabel = scoreLabel;
  protected readonly formatScore = formatScore;
  protected readonly formatDate = formatDate;

  setFiltro(tipo: string | null): void {
    this.filtro.set(tipo);
    this.page.set(1);
  }

  previousPage(): void {
    this.page.set(this.clampPage(this.currentPage() - 1));
  }

  nextPage(): void {
    this.page.set(this.clampPage(this.currentPage() + 1));
  }

  contar(tipo: string): number {
    return (this.senales() ?? []).filter((senal) => senal.tipo === tipo).length;
  }

  private clampPage(page: number): number {
    return Math.min(Math.max(page, 1), this.totalPages());
  }
}
