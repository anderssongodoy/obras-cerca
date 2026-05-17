import type { EstadoObra, Fuente, ObraApi } from '../../../core/models/obra.model';

// Reglas para mapear el modelo del backend a los 5 buckets visuales del demo.
// Orden importa: la primera regla que matchea gana.
export function derivarEstado(o: ObraApi, tieneSenal: boolean): EstadoObra {
  const avance = o.avance_fisico_infobras ?? 0;
  const wfs = (o.estado_obra_wfs ?? '').toLowerCase();
  const mef = (o.estado_proyecto_mef ?? '').toUpperCase();

  if (o.existe_informe_control && avance >= 95) return 'verificada';
  if (wfs === 'en ejecución' || wfs === 'en ejecucion' || wfs === 'activa') {
    return 'en_ejecucion';
  }
  if (mef === 'ACTIVO' && o.avance_fisico_infobras == null) return 'en_licitacion';
  if (tieneSenal && !o.existe_informe_control && o.avance_fisico_infobras == null) {
    return 'senal';
  }
  return 'informativo';
}

// Fuente primaria — INFObras si la obra tiene nobr (registro Contraloría),
// SEACE si tiene contrato (procedimiento), Ciudadanos como fallback de señal pura.
export function derivarFuente(o: ObraApi, soloSenalSinObra: boolean): Fuente {
  if (soloSenalSinObra) return 'Ciudadanos';
  if (o.nobr_id) return 'INFObras';
  if (o.contratista_ruc || o.monto_contrato != null) return 'SEACE';
  return 'INFObras';
}

// Formato del demo: "S/ 2.85 M" — usa el monto más fiable disponible.
// Si no hay monto, devuelve "—" (em-dash) como el demo.
export function formatoMonto(o: ObraApi): { numerico: number | null; label: string } {
  const n = o.costo_actualizado ?? o.mto_viable ?? o.monto_contrato ?? null;
  if (n == null || n <= 0) return { numerico: null, label: '—' };
  const millones = n / 1_000_000;
  if (millones >= 1) return { numerico: n, label: `S/ ${millones.toFixed(2)} M` };
  const miles = n / 1_000;
  return { numerico: n, label: `S/ ${miles.toFixed(0)} K` };
}

// Labels visibles del demo — usados en pills, chips, popups.
export const estadoLabel: Record<EstadoObra, string> = {
  en_ejecucion: 'En ejecución',
  en_licitacion: 'En licitación',
  verificada: 'Información contrastada',
  informativo: 'Informativo',
  senal: 'Señal ciudadana',
};

// Icono Material Symbols por estado — paridad con `iconConfig` del demo (línea ~1430).
export const estadoIcon: Record<EstadoObra, string> = {
  en_ejecucion: 'construction',
  en_licitacion: 'gavel',
  verificada: 'verified',
  informativo: 'info',
  senal: 'flag',
};

// CSS custom-prop a usar como color principal del estado en pills, banda, marker.
export const estadoColorVar: Record<EstadoObra, string> = {
  en_ejecucion: 'var(--state-ejecucion)',
  en_licitacion: 'var(--state-licitacion)',
  verificada: 'var(--state-verificada)',
  informativo: 'var(--state-informativo)',
  senal: 'var(--state-senal)',
};

export const estadoColorVarSoft: Record<EstadoObra, string> = {
  en_ejecucion: 'var(--state-ejecucion-soft)',
  en_licitacion: 'var(--state-licitacion-soft)',
  verificada: 'var(--state-verificada-soft)',
  informativo: 'var(--state-informativo-soft)',
  senal: 'var(--state-senal-soft)',
};
