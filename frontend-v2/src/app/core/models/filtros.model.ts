import type { EstadoObra } from './obra.model';

// Chip seleccionable en el drawer — paridad demo (todas + 4 buckets concretos).
export type FiltroChip = 'todas' | EstadoObra | 'con_senal';

export interface FiltrosState {
  estado: FiltroChip;
  texto: string;
  ubigeo: string | null;
}
