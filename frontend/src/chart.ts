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

const niceStep = (range: number): number => {
  const rough = range / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  return [1, 2, 5, 10].map((factor) => factor * magnitude).find((step) => step >= rough) ?? 10 * magnitude;
};

export function deviationChart(
  values: readonly (number | null)[],
  center: number,
  unit: string,
  minimumExtent: number,
): DeviationChartModel {
  const deviations = values.map((value) => (value === null ? null : value - center));
  const extent = Math.max(
    minimumExtent,
    ...deviations.flatMap((deviation) => (deviation === null ? [] : [Math.abs(deviation)])),
  );
  const step = niceStep(extent * 2);
  const limit = Math.ceil(extent / step) * step;
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
