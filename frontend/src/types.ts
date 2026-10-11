export type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'failed' | 'port_busy';

export type SignalGroup = 'vehicle' | 'battery' | 'temperature';

export interface SignalReading {
  readonly key: string;
  readonly label: string;
  readonly group: SignalGroup;
  readonly unit: string;
  readonly decimals: number;
  readonly value: number | null;
}

export interface CellStats {
  readonly valid: number;
  readonly minimum: number;
  readonly maximum: number;
  readonly mean: number;
  readonly median: number;
  readonly stdev: number;
  readonly spread: number;
  readonly min_cell: number;
  readonly max_cell: number;
  readonly outliers: readonly number[];
  readonly spread_exceeded: boolean;
}

export interface GroupHealth {
  readonly capacities: readonly (number | null)[];
  readonly reference_capacity: number | null;
  readonly health: readonly (number | null)[];
  readonly minimum: number;
  readonly maximum: number;
  readonly mean: number;
  readonly weakest_group: number;
  readonly strongest_group: number;
}

export interface Balancing {
  readonly charge: readonly (number | null)[];
  readonly charge_mean: number | null;
  readonly charge_min: number | null;
  readonly charge_max: number | null;
  readonly active: readonly boolean[];
  readonly seconds: readonly number[];
  readonly active_count: number;
  readonly longest_s: number;
}

export interface Reading {
  readonly duration_s: number;
  readonly voltages: readonly (number | null)[];
  readonly stats: CellStats | null;
  readonly cell_error: string | null;
  readonly health: GroupHealth | null;
  readonly health_error: string | null;
  readonly balancing: Balancing | null;
  readonly balancing_error: string | null;
  readonly signals: readonly SignalReading[];
}

export interface AdapterInfo {
  readonly elm_version: string | null;
  readonly device: string | null;
  readonly battery_voltage: string | null;
}

export interface MonitorState {
  readonly status: ConnectionStatus;
  readonly port: string | null;
  readonly adapter: AdapterInfo | null;
  readonly reading: Reading | null;
}
