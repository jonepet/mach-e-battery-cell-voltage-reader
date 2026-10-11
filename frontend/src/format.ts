import type { SignalReading } from './types';

export const millivolts = (volts: number): string => `${(volts * 1000).toFixed(1)} mV`;

export const signedMillivolts = (volts: number): string => `${volts >= 0 ? '+' : ''}${millivolts(volts)}`;

export const volts = (value: number): string => `${value.toFixed(4)} V`;

export const percent = (value: number): string => `${value.toFixed(1)} %`;

export const ampereHours = (value: number): string => `${value.toFixed(1)} Ah`;

export const duration = (seconds: number): string => {
  const minutes = Math.floor(seconds / 60);
  return minutes < 60 ? `${minutes} min` : `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
};

export const elapsed = (value: number): string => `${Math.floor(value)} s`;

export const signalValue = (signal: SignalReading): string => {
  if (signal.value === null) {
    return 'Read failed';
  }
  const digits = { minimumFractionDigits: signal.decimals, maximumFractionDigits: signal.decimals };
  return `${signal.value.toLocaleString(undefined, digits)} ${signal.unit}`;
};
