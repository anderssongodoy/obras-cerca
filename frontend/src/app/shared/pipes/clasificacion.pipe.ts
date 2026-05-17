import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'clasificacion', standalone: true })
export class ClasificacionPipe implements PipeTransform {
  transform(value: string | null): string {
    const map: Record<string, string> = {
      vigente: '🔴 Vigente',
      dudosa:  '🟡 Dudosa',
      zombie:  '⚫ Zombie',
    };
    return value ? (map[value] ?? value) : '—';
  }
}
