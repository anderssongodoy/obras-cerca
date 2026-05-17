export interface Obra {
  id: number;
  codigo_infobras: number;
  nombre: string;
  estado_ejecucion: string;
  naturaleza: string;
  sector: string;
  fecha_inicio: string;
  fecha_fin_programada: string;
  fecha_ultimo_avance: string;
  avance_fisico_real: number;
  avance_fisico_programado: number;
  porcentaje_ejecucion_financiera: number;
  monto_contrato: number;
  monto_ejecutado: number;
  existe_paralizacion: boolean;
  clasificacion_paralizacion: 'vigente' | 'dudosa' | 'zombie' | null;
  confirmada_contraloria_2025: boolean;
  dias_paralizada_real: number | null;
  dias_sin_avance: number | null;
  latitud: number;
  longitud: number;
  direccion: string;
  tipo_ubicacion: string;
  entidad_nombre: string;
  contratista_ruc: string;
  contratista_nombre: string;
  distrito_nombre: string;
  provincia: string;
  distrito_ubigeo: string;
  infobras_url?: string;
  paralizacion?: {
    fecha_paralizacion: string;
    dias_paralizado: number;
    causal: string;
    comentarios: string;
    avance_fisico_al_par: number;
  };
  senales?: Senal[];
}

export interface Senal {
  id: number;
  tipo: string;
  titulo: string;
  explicacion: string;
  score: number;
  formula: string;
  obra_id?: number;
  obra_nombre?: string;
  clasificacion_paralizacion?: string;
  confirmada_contraloria_2025?: boolean;
  dias_paralizada_real?: number;
  distrito?: string;
  contratista_ruc?: string;
  contratista_nombre?: string;
  entidad_nombre?: string;
}

export const MOCK_OBRAS: Obra[] = [
  {
    id: 1,
    codigo_infobras: 536317,
    nombre: 'MEJORAMIENTO DE LA TRANSITABILIDAD VEHICULAR Y PEATONAL EN CINCO PASOS A DESNIVEL',
    estado_ejecucion: 'PARALIZADA',
    naturaleza: 'Mejoramiento',
    sector: 'TRANSPORTES',
    fecha_inicio: '2021-03-15',
    fecha_fin_programada: '2023-09-30',
    fecha_ultimo_avance: '2024-02-10',
    avance_fisico_real: 11.31,
    avance_fisico_programado: 100,
    porcentaje_ejecucion_financiera: 14.2,
    monto_contrato: 489000000,
    monto_ejecutado: 69498000,
    existe_paralizacion: true,
    clasificacion_paralizacion: 'vigente',
    confirmada_contraloria_2025: false,
    dias_paralizada_real: 103,
    dias_sin_avance: 103,
    latitud: -11.9866,
    longitud: -77.0058,
    direccion: 'Av. Próceres de la Independencia, San Juan de Lurigancho',
    tipo_ubicacion: 'referencial',
    entidad_nombre: 'FONDO METROPOLITANO DE INVERSIONES - INVERMET',
    contratista_ruc: '20100128056',
    contratista_nombre: 'CONSTRUCTORA GRECA S.A.',
    distrito_nombre: 'San Juan de Lurigancho',
    provincia: 'Lima',
    distrito_ubigeo: '150132',
    infobras_url: 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=536317',
    paralizacion: {
      fecha_paralizacion: '2024-02-10',
      dias_paralizado: 103,
      causal: 'Conflictos sociales',
      comentarios: 'Paralización por conflictos sociales con comunidades aledañas. Sin fecha estimada de reinicio.',
      avance_fisico_al_par: 11.31,
    },
    senales: [
      {
        id: 1,
        tipo: 'paralizacion',
        titulo: '🔴 Paralización vigente — S/ 489 M detenidos',
        explicacion: 'Esta obra lleva 103 días paralizada con solo 11.31% de avance. El monto sin ejecutar es S/ 419 millones de dinero público que no llega a los vecinos de San Juan de Lurigancho (1.1 M de habitantes potencialmente afectados).',
        score: 98,
        formula: 'dias_paralizada_real=103; avance=11.31%; monto_sin_ejecutar=S/419M',
      },
    ],
  },
  {
    id: 2,
    codigo_infobras: 504340,
    nombre: 'MEJORAMIENTO DE LA MOVILIDAD URBANA EN LA AV. SANTA ROSA, DISTRITO DE CHORRILLOS',
    estado_ejecucion: 'PARALIZADA',
    naturaleza: 'Mejoramiento',
    sector: 'TRANSPORTES',
    fecha_inicio: '2022-01-10',
    fecha_fin_programada: '2023-12-31',
    fecha_ultimo_avance: '2024-02-05',
    avance_fisico_real: 79.43,
    avance_fisico_programado: 100,
    porcentaje_ejecucion_financiera: 76.1,
    monto_contrato: 3160000,
    monto_ejecutado: 2405760,
    existe_paralizacion: true,
    clasificacion_paralizacion: 'vigente',
    confirmada_contraloria_2025: true,
    dias_paralizada_real: 103,
    dias_sin_avance: 103,
    latitud: -12.1627,
    longitud: -77.0175,
    direccion: 'Av. Santa Rosa, Chorrillos',
    tipo_ubicacion: 'exacta',
    entidad_nombre: 'MUNICIPALIDAD DISTRITAL DE CHORRILLOS',
    contratista_ruc: '20514207737',
    contratista_nombre: 'CONSTRUCTORA VIAL PERU S.A.C.',
    distrito_nombre: 'Chorrillos',
    provincia: 'Lima',
    distrito_ubigeo: '150109',
    infobras_url: 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=504340',
    paralizacion: {
      fecha_paralizacion: '2024-02-05',
      dias_paralizado: 103,
      causal: 'Resolución de contrato',
      comentarios: 'Contrato resuelto por incumplimiento del contratista. La obra quedó al 79.43% sin terminar.',
      avance_fisico_al_par: 79.43,
    },
    senales: [
      {
        id: 2,
        tipo: 'paralizacion',
        titulo: '🔴 Doble validación: Infobras + Contraloría dic-2025',
        explicacion: 'Esta es una de las 81 obras confirmadas oficialmente por la Contraloría en diciembre 2025. Con 79.43% de avance y paralizada hace 103 días, los vecinos de Chorrillos esperan el 20.57% restante que ya fue pagado.',
        score: 95,
        formula: 'confirmada_contraloria_2025=true; dias_paralizada=103; avance=79.43%',
      },
    ],
  },
  {
    id: 3,
    codigo_infobras: 42593,
    nombre: 'MEJORAMIENTO DEL SISTEMA DE SEGURIDAD CIUDADANA Y EQUIPAMIENTO - JNJ',
    estado_ejecucion: 'PARALIZADA',
    naturaleza: 'Mejoramiento',
    sector: 'ORDEN PUBLICO Y SEGURIDAD',
    fecha_inicio: '2019-06-01',
    fecha_fin_programada: '2021-12-31',
    fecha_ultimo_avance: '2024-01-20',
    avance_fisico_real: 99.86,
    avance_fisico_programado: 100,
    porcentaje_ejecucion_financiera: 98.2,
    monto_contrato: 32000000,
    monto_ejecutado: 31424000,
    existe_paralizacion: true,
    clasificacion_paralizacion: 'vigente',
    confirmada_contraloria_2025: false,
    dias_paralizada_real: 103,
    dias_sin_avance: 103,
    latitud: -12.0970,
    longitud: -77.0430,
    direccion: 'Jr. Nazca 370, San Isidro',
    tipo_ubicacion: 'exacta',
    entidad_nombre: 'JUNTA NACIONAL DE JUSTICIA',
    contratista_ruc: '20601234567',
    contratista_nombre: 'SERVICIOS INTEGRADOS DE SEGURIDAD S.A.C.',
    distrito_nombre: 'San Isidro',
    provincia: 'Lima',
    distrito_ubigeo: '150131',
    infobras_url: 'https://infobras.contraloria.gob.pe/InfobrasWeb/Mapa/Sumario?ObraId=42593',
    paralizacion: {
      fecha_paralizacion: '2024-01-20',
      dias_paralizado: 103,
      causal: 'Resolución de contrato',
      comentarios: 'Obra paralizada al 99.86% de avance. Resolución de contrato cuando faltaba el 0.14% para terminar.',
      avance_fisico_al_par: 99.86,
    },
    senales: [
      {
        id: 3,
        tipo: 'paralizacion',
        titulo: '⚠️ Absurdo institucional: 99.86% de avance paralizada',
        explicacion: 'Esta obra de la Junta Nacional de Justicia fue paralizada cuando faltaba el 0.14% para terminar. S/ 32 millones invertidos y la obra no se entregó por una resolución de contrato al final del proceso.',
        score: 91,
        formula: 'avance=99.86%; dias_paralizada=103; monto_no_ejecutado=S/44,800',
      },
    ],
  },
  {
    id: 4,
    codigo_infobras: 521890,
    nombre: 'CREACIÓN DEL PARQUE ZONAL EN EL SECTOR 4, VILLA EL SALVADOR',
    estado_ejecucion: 'EN EJECUCIÓN',
    naturaleza: 'Creación',
    sector: 'CULTURA Y DEPORTE',
    fecha_inicio: '2023-03-01',
    fecha_fin_programada: '2025-06-30',
    fecha_ultimo_avance: '2025-05-10',
    avance_fisico_real: 62.4,
    avance_fisico_programado: 70.0,
    porcentaje_ejecucion_financiera: 59.8,
    monto_contrato: 8500000,
    monto_ejecutado: 5083000,
    existe_paralizacion: false,
    clasificacion_paralizacion: null,
    confirmada_contraloria_2025: false,
    dias_paralizada_real: null,
    dias_sin_avance: null,
    latitud: -12.2130,
    longitud: -76.9432,
    direccion: 'Sector 4, Villa El Salvador',
    tipo_ubicacion: 'referencial',
    entidad_nombre: 'MUNICIPALIDAD DISTRITAL DE VILLA EL SALVADOR',
    contratista_ruc: '20451234890',
    contratista_nombre: 'CONSTRUCTORA HORIZONTE S.A.C.',
    distrito_nombre: 'Villa El Salvador',
    provincia: 'Lima',
    distrito_ubigeo: '150142',
  },
  {
    id: 5,
    codigo_infobras: 498201,
    nombre: 'REHABILITACIÓN DE PISTAS Y VEREDAS JR. LOS ROSALES - LOS OLIVOS',
    estado_ejecucion: 'EN EJECUCIÓN',
    naturaleza: 'Rehabilitación',
    sector: 'TRANSPORTES',
    fecha_inicio: '2024-01-15',
    fecha_fin_programada: '2025-07-15',
    fecha_ultimo_avance: '2025-05-12',
    avance_fisico_real: 45.0,
    avance_fisico_programado: 50.0,
    porcentaje_ejecucion_financiera: 42.3,
    monto_contrato: 2100000,
    monto_ejecutado: 888300,
    existe_paralizacion: false,
    clasificacion_paralizacion: null,
    confirmada_contraloria_2025: false,
    dias_paralizada_real: null,
    dias_sin_avance: null,
    latitud: -11.9675,
    longitud: -77.0742,
    direccion: 'Jr. Los Rosales cdra. 3-8, Los Olivos',
    tipo_ubicacion: 'referencial',
    entidad_nombre: 'MUNICIPALIDAD DISTRITAL DE LOS OLIVOS',
    contratista_ruc: '20512987654',
    contratista_nombre: 'PAVIMENTOS DEL NORTE S.R.L.',
    distrito_nombre: 'Los Olivos',
    provincia: 'Lima',
    distrito_ubigeo: '150122',
  },
];
