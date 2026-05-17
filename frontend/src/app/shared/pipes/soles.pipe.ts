import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'soles', standalone: true })
export class SolesPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (value == null) return '—';
    if (value >= 1_000_000_000) return `S/ ${(value / 1_000_000_000).toFixed(2)} mil M`;
    if (value >= 1_000_000)     return `S/ ${(value / 1_000_000).toFixed(2)} M`;
    if (value >= 1_000)         return `S/ ${(value / 1_000).toFixed(0)} k`;
    return `S/ ${value.toLocaleString('es-PE')}`;
  }
}
