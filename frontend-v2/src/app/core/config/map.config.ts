// Centro de Lima Metro — cubre los 4 distritos del snapshot demo
// (Lima, San Isidro, San Miguel, Chorrillos).
export const CENTER_CALLAO: [number, number] = [-12.0800, -77.0400];
export const ZOOM_DEFAULT = 12;
// La demo no fija minZoom; permitir alejar más hace visible la UX de clustering.
export const ZOOM_MIN = 8;
export const ZOOM_MAX = 18;

// CARTO Positron — fondo claro neutral, sin API key, atribución obligatoria.
export const TILE_URL =
  'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';

// Sin ubigeo por defecto: el snapshot demo tiene obras en 4 distritos de Lima Metro.
// Setear a null para que ObrasService traiga todas las obras con coords disponibles.
// Cambiar a '150101' u otro ubigeo cuando la BD tenga datos concentrados en un distrito.
export const UBIGEO_CALLAO_DEFAULT: string | null = null;

// Tamaño máximo del cluster Leaflet (px) — paridad demo.
export const CLUSTER_RADIUS = 60;
