export interface StatsTotales {
  distritos_mvp: number;
  entidades: number;
  contratistas: number;
  proyectos: number;
  obras: number;
  proyectos_desactivados: number;
  obras_paralizadas_wfs: number;
  saldos_obra: number;
  informes_control: number;
  ordenes_menores: number;
  senales_activas: number;
  monto_paralizado?: number | null;
}

export interface StatsApi {
  totales: StatsTotales;
}
