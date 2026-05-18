import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { HomeService } from '../../core/services/home.service';
import { SenalesPageService } from '../../core/services/senales-page.service';
import { formatDate, formatMoney, formatScore, scoreLabel, tipoLabel } from '../../shared/utils/senal-format';

import { Topbar } from '../mapa/components/topbar/topbar';

@Component({
  selector: 'app-inicio-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Topbar, RouterLink, DecimalPipe],
  templateUrl: './inicio.page.html',
  styleUrl: './inicio.page.scss',
})
export class InicioPage {
  private readonly home = inject(HomeService);
  private readonly senalesSvc = inject(SenalesPageService);

  readonly stats = this.home.stats;
  readonly senales = this.senalesSvc.senales;
  readonly statsLoading = this.home.isLoading;
  readonly statsError = this.home.error;
  readonly senalesLoading = this.senalesSvc.isLoading;
  readonly senalesError = this.senalesSvc.error;

  // Fallback público documentado en el plan hasta que `/api/stats` exponga un monto confiable.
  readonly montoParalizado = computed(() => this.stats()?.totales.monto_paralizado ?? 43_000_000_000);
  readonly senalesRecientes = computed(() => (this.senales() ?? []).slice(0, 5));

  protected readonly tipoLabel = tipoLabel;
  protected readonly scoreLabel = scoreLabel;
  protected readonly formatScore = formatScore;
  protected readonly formatDate = formatDate;
  protected readonly formatMoney = formatMoney;
}
