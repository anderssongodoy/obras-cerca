import type { SenalApi } from '../../core/models/obra.model';

export function tipoLabel(tipo: string | null | undefined): string {
  return (tipo ?? '').replace(/_/g, ' ');
}

export function scoreLabel(tipo: string): string {
  switch (tipo) {
    case 'sobrecosto':
      return 'sobrecosto';
    case 'discrepancia_avance':
      return 'diferencia';
    case 'concentracion_menores':
      return '% concentración';
    case 'paralizacion_real':
      return 'verificada WFS';
    case 'inactiva_mef':
      return 'desactivada';
    default:
      return 'score';
  }
}

export function formatScore(senal: SenalApi): string {
  if (senal.score == null) {
    return '—';
  }

  const tiposPct = new Set(['sobrecosto', 'discrepancia_avance', 'concentracion_menores']);
  return tiposPct.has(senal.tipo) ? `${Math.round(senal.score)}%` : String(senal.score);
}

export function formatDate(value: string | null | undefined): string {
  if (!value) {
    return '';
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleDateString('es-PE', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

export function formatMoney(value: number | null | undefined): string {
  if (value == null) {
    return 'miles de millones de soles';
  }

  if (value >= 1_000_000_000) {
    return `S/${(value / 1_000_000_000).toFixed(1)} mil millones`;
  }

  if (value >= 1_000_000) {
    return `S/${(value / 1_000_000).toFixed(1)} millones`;
  }

  return `S/${value.toLocaleString('es-PE')}`;
}
