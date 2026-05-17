import * as L from 'leaflet';

import type { EstadoObra } from '../../../core/models/obra.model';
import { estadoColorVar, estadoIcon } from './estado-catalog';

/**
 * Crea un L.DivIcon con el pin civic del demo (paridad línea 1435).
 * El estilo `.marker-pin` vive en `styles/_leaflet-overrides.scss`.
 */
export function makeIcon(estado: EstadoObra, titulo: string): L.DivIcon {
  const color = estadoColorVar[estado];
  const iconName = estadoIcon[estado];
  const label = escapeAttribute(`Seleccionar obra: ${titulo}`);
  return L.divIcon({
    className: 'marker-divicon',
    html: `<div class="marker-pin" role="button" aria-label="${label}" style="background:${color};color:${color}"><span class="material-symbols-outlined" aria-hidden="true">${iconName}</span></div>`,
    iconSize: [44, 44],
    iconAnchor: [22, 22],
    popupAnchor: [0, -22],
  });
}

function escapeAttribute(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
