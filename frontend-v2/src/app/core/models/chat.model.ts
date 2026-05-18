export interface ChatFuente {
  informe_id: number;
  nro_informe: string | null;
  titulo: string | null;
  pagina: number | null;
  url_pdf: string | null;
}

export interface ChatMessage {
  role: 'user' | 'ai';
  text: string;
  fuentes?: ChatFuente[];   // solo en role='ai'
  loading?: boolean;         // placeholder mientras llega la respuesta
  isError?: boolean;         // true si la llamada falló
  cached?: boolean;          // true si la respuesta vino del cache backend
  timestamp: number;         // Date.now() para track @for y debug
}

export interface ChatHealth {
  obra_id: number;
  chunks_indexados: number;
  informes_indexados: number;
  puede_preguntar: boolean;
}

export interface ChatSugerencias {
  obra_id: number;
  puede_preguntar: boolean;
  sugerencias: string[];
}

export interface ChatResponse {
  respuesta: string;
  fuentes: ChatFuente[];
  cache: boolean;
  provider?: string;
  modelo?: string;
}

export interface PreguntaIn {
  pregunta: string;
}
