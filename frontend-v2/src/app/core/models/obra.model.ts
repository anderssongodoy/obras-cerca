// Estados del demo — 5 buckets visuales que mapean a la lógica de negocio del backend.
export type EstadoObra =
  | 'en_ejecucion'
  | 'en_licitacion'
  | 'verificada'
  | 'informativo'
  | 'senal';

export type Fuente = 'INFObras' | 'SEACE' | 'Ciudadanos';

// Shape EXACTO que devuelve /api/obras (vista v_obra_mvp en backend).
// Campos opcionales reflejan columnas nullables del SELECT.
export interface ObraApi {
  id: number;
  nobr_id: string | null;
  cui: string | null;
  cod_snip: string | null;
  nombre_inversion: string | null;
  nombre_obra: string | null;
  entidad_nombre: string | null;
  entidad_tipo: string | null;
  entidad_sector: string | null;
  contratista_ruc: string | null;
  contratista_nombre: string | null;
  distrito_nombre: string | null;
  distrito_ubigeo: string | null;
  direccion: string | null;
  latitud: number | null;
  longitud: number | null;
  geom_fuente: string | null;
  estado_obra_wfs: string | null;
  estado_obra_ficha: string | null;
  estado_proyecto_mef: string | null;
  avance_fisico_infobras: number | null;
  avance_fisico_mef: number | null;
  devengado_siaf: number | null;
  fecha_ult_avance: string | null;
  fecha_inicio_mef: string | null;
  fecha_fin_mef: string | null;
  mto_viable: number | null;
  costo_actualizado: number | null;
  monto_contrato: number | null;
  sobrecosto_pct: number | null;
  existe_paralizacion_mef: boolean | null;
  existe_informe_control: boolean | null;
  es_saldo_obra: boolean | null;
  url_infobras_ficha: string | null;
  url_mef_ssi: string | null;
  url_infobras_informes: string | null;
  distancia_m: number | null;
}

// Envelope paginado del endpoint /api/obras.
export interface ObrasListResponse {
  total: number;
  limit: number;
  offset: number;
  items: ObraApi[];
}

// Shape NORMALIZADO para el frontend — paridad con el demo/index.html.
// El service mapea ObraApi[] + Set<senales> → Obra[].
export interface Obra {
  id: number;
  titulo: string;
  estado: EstadoObra;
  montoNumerico: number | null;
  montoLabel: string;
  entidad: string;
  distrito: string;
  coords: [number, number];
  conSenal: boolean;
  fuente: Fuente;
  // Refs para verificación humana
  urlInfobras: string | null;
  urlMef: string | null;
  // Identificadores de fuente para el panel
  nobrId: string | null;
  cui: string | null;
}

// Tramo de avenida — polyline en el mapa. Mock en assets/mock/tramos.callao.json.
export interface Tramo {
  nombre: string;
  estado: EstadoObra;
  coords: [number, number][];
}

// Shape de /api/senales (array directo, no envelope).
export interface SenalApi {
  id: number;
  tipo: string;
  titulo: string | null;
  resumen: string | null;
  score: number | null;
  formula: string | null;
  evidencia: unknown;
  detectada_en: string | null;
  obra_id: number | null;
  cui: string | null;
  nobr_id: string | null;
  distrito: string | null;
  ubigeo: string | null;
  entidad: string | null;
  contratista: string | null;
}
