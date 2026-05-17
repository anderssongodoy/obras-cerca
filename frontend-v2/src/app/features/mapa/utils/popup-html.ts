import type { Obra } from '../../../core/models/obra.model';
import { estadoColorVar, estadoColorVarSoft, estadoLabel } from './estado-catalog';

/**
 * Render del popup como HTML string.
 * Fase 4.7: el click del marker ya abre el panel de detalle; el popup queda como resumen.
 */
export function popupHtml(obra: Obra): string {
  const bg = estadoColorVarSoft[obra.estado];
  const color = estadoColorVar[obra.estado];
  return `<div class="popup-inner">
    <div class="popup-estado" style="background:${bg};color:${color}">${escapeHtml(estadoLabel[obra.estado])}</div>
    <div class="popup-titulo">${escapeHtml(obra.titulo)}</div>
    <div class="popup-hint">Detalle abierto en el panel</div>
  </div>`;
}

/**
 * Escape minimal para evitar XSS en el contenido del popup.
 * No usamos DomSanitizer porque el popup vive fuera del árbol Angular (Leaflet DOM).
 */
function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
