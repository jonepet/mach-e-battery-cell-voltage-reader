export const CHART = { width: 960, height: 260, left: 52, right: 12, top: 12, bottom: 28 } as const;

const PLOT_HEIGHT = CHART.height - CHART.top - CHART.bottom;

export interface Tick {
  readonly y: number;
  readonly label: string;
  readonly isAxis: boolean;
}

export interface Bar {
  readonly x: number;
  readonly y: number;
  readonly width: number;
  readonly height: number;
}

export interface Slot {
  readonly group: number;
  readonly x: number;
  readonly width: number;
  readonly labelX: number | null;
  readonly bar: Bar | null;
}

export interface DeviationChartModel {
  readonly ticks: readonly Tick[];
  readonly slots: readonly Slot[];
  readonly plotHeight: number;
}

export interface ChartRange {
  readonly limit: number;
  readonly step: number;
  readonly narrowerSince: number | null;
}

const NARROW_AFTER_MS = 60_000;

const niceStep = (range: number): number => {
  const rough = range / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  return [1, 2, 5, 10].map((factor) => factor * magnitude).find((step) => step >= rough) ?? 10 * magnitude;
};

export function deviationExtent(
  values: readonly (number | null)[],
  center: number,
  minimumExtent: number,
): number {
  return Math.max(minimumExtent, ...values.flatMap((value) => (value === null ? [] : [Math.abs(value - center)])));
}

/** Widens at once so no bar is clipped; narrows only after the data has fitted a narrower range for a minute. */
export function holdRange(previous: ChartRange | null, extent: number, now: number): ChartRange {
  const step = niceStep(extent * 2);
  const wanted = { limit: Math.ceil(extent / step) * step, step, narrowerSince: null };
  if (previous === null || wanted.limit > previous.limit) {
    return wanted;
  }
  if (wanted.limit === previous.limit) {
    return { ...previous, narrowerSince: null };
  }
  const since = previous.narrowerSince ?? now;
  return now - since >= NARROW_AFTER_MS ? wanted : { ...previous, narrowerSince: since };
}

export function deviationChart(
  values: readonly (number | null)[],
  center: number,
  unit: string,
  range: ChartRange,
): DeviationChartModel {
  const { limit, step } = range;
  const deviations = values.map((value) => (value === null ? null : value - center));
  const y = (deviation: number): number => CHART.top + ((limit - deviation) / (2 * limit)) * PLOT_HEIGHT;

  const tickCount = Math.round((2 * limit) / step);
  const ticks = Array.from({ length: tickCount + 1 }, (_, index) => {
    const tick = -limit + index * step;
    const rounded = Number(tick.toFixed(2));
    return { y: y(tick), label: `${rounded > 0 ? '+' : ''}${rounded} ${unit}`, isAxis: index === tickCount / 2 };
  });

  const width = (CHART.width - CHART.left - CHART.right) / values.length;
  const slots = deviations.map((deviation, index): Slot => {
    const x = CHART.left + width * index;
    const bar =
      deviation === null
        ? null
        : {
            x: x + width * 0.15,
            width: width * 0.7,
            y: Math.min(y(deviation), y(0)),
            height: Math.max(1, Math.abs(y(deviation) - y(0))),
          };
    return { group: index + 1, x, width, labelX: index % 3 === 0 ? x + width / 2 : null, bar };
  });

  return { ticks, slots, plotHeight: PLOT_HEIGHT };
}
