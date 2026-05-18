export interface Stats {
  totales: {
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
  };
}

export interface Distrito {
  id: number;
  ubigeo: string;
  departamento: string;
  provincia: string;
  distrito: string;
  lat: number | null;
  lon: number | null;
  ambito_mvp: boolean;
}

export interface ObraResumen {
  id: number;
  nobr_id: number;
  cui: number;
  nombre_obra: string;
  nombre_inversion: string;
  entidad_nombre: string;
  contratista_ruc: string | null;
  contratista_nombre: string | null;
  distrito_nombre: string;
  distrito_ubigeo: string;
  provincia?: string;
  departamento?: string;
  latitud: number | null;
  longitud: number | null;
  estado_obra_wfs: string | null;
  estado_obra_ficha: string | null;
  estado_proyecto_mef: string;
  avance_fisico_infobras: number | null;
  avance_fisico_mef: number | null;
  sobrecosto_pct: number | null;
  mto_viable: number | null;
  costo_actualizado: number | null;
  monto_contrato: number | null;
  existe_paralizacion_mef: boolean;
  existe_informe_control: boolean;
  es_saldo_obra: boolean;
  distancia_m?: number | null;
}

export interface ObraListResponse {
  total: number;
  limit: number;
  offset: number;
  items: ObraResumen[];
}

export interface ObraFicha extends ObraResumen {
  url_infobras_ficha: string;
  url_mef_ssi: string;
  url_infobras_informes: string;
  fecha_inicio_mef: string | null;
  fecha_fin_mef: string | null;
  fecha_ult_avance: string | null;
  devengado_siaf: number | null;
  geom_fuente: string | null;
  saldos_hijos: any[];
  procedimientos: any[];
  paralizaciones: any[];
  informes_control: any[];
  senales: any[];
}

export interface Senal {
  id: number;
  tipo: string;
  titulo: string;
  resumen: string;
  score: number | null;
  formula: string;
  evidencia: any;
  detectada_en: string;
  obra_id: number | null;
  cui: number | null;
  nobr_id: number | null;
  distrito: string | null;
  ubigeo: string | null;
  entidad: string | null;
  contratista: string | null;
}

export interface ContratistaFicha {
  id: number;
  ruc: string;
  razon_social: string;
  tiene_sancion_oece: boolean;
  obras: any[];
  procedimientos: any[];
}

export interface VerificacionLive {
  obra_id: number;
  nobr_id: number;
  cui: number;
  fuentes: {
    mef_invierte_pe: any;
    mef_nobr_vinculados: any[];
    mef_paralizaciones: any[];
    seace_contratos: any[];
    infobras_wfs: any;
    infobras_ficha_publica: any;
    contraloria_informes: any[];
  };
  urls: { mef_ssi: string; infobras_ficha: string; infobras_informes: string };
}
