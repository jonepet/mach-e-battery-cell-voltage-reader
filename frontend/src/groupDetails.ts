import { ampereHours, duration, percent, signedMillivolts, volts } from './format';
import type { Balancing, Reading } from './types';

export interface GroupDetails {
  readonly group: number;
  readonly voltage: string | null;
  readonly fromMedian: string | null;
  readonly capacity: string | null;
  readonly health: string | null;
  readonly balancing: string | null;
}

const at = <T>(values: readonly (T | null)[] | undefined, index: number): T | null => values?.[index] ?? null;

const present = <T>(value: T | null, format: (value: T) => string): string | null =>
  value === null ? null : format(value);

const balancingText = (balancing: Balancing, index: number): string =>
  balancing.active[index] === true ? `Yes, ${duration(balancing.seconds[index] ?? 0)}` : 'No';

export function groupDetails(reading: Reading, group: number): GroupDetails {
  const index = group - 1;
  const voltage = at(reading.voltages, index);
  const { stats, health, balancing } = reading;
  return {
    group,
    voltage: present(voltage, volts),
    fromMedian: voltage === null || stats === null ? null : signedMillivolts(voltage - stats.median),
    capacity: present(at(health?.capacities, index), ampereHours),
    health: present(at(health?.health, index), percent),
    balancing: balancing === null ? null : balancingText(balancing, index),
  };
}
