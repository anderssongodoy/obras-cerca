import type { Obra } from '../../../core/models/obra.model';

/**
 * Radio del círculo de impacto en metros (paridad demo línea 1534).
 * Estados informativo/senal no tienen monto significativo → radio fijo chico.
 */
export function radiusFromObra(obra: Obra): number {
  if (obra.estado === 'informativo' || obra.estado === 'senal') return 60;
  const m = obra.montoNumerico ?? 0;
  if (m <= 0) return 80;
  const millones = m / 1_000_000;
  if (millones < 1) return 50;
  if (millones < 3) return 80;
  if (millones < 5) return 110;
  return 140;
}
