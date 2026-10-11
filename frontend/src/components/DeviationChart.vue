<script setup lang="ts">
import { computed, onUnmounted, ref, shallowRef, useTemplateRef, watch } from 'vue';

import { CHART, type ChartRange, deviationChart, deviationExtent, holdRange } from '../chart';
import { useGroupHover } from '../composables/useGroupHover';

const props = defineProps<{
  chartId: string;
  label: string;
  values: readonly (number | null)[];
  center: number | null;
  unit: string;
  minimumExtent: number;
  barKind: (group: number) => 'outlier' | 'balancing' | null;
}>();

const { group: hovered, enter, leave, tap } = useGroupHover();

const figure = useTemplateRef<HTMLElement>('figure');
const width = ref<number>(CHART.width);
const resize = new ResizeObserver(([entry]) => {
  if (entry && entry.contentRect.width > 0) {
    width.value = entry.contentRect.width;
  }
});
watch(figure, (element, previous) => {
  if (previous) {
    resize.unobserve(previous);
  }
  if (element) {
    resize.observe(element);
  }
});
onUnmounted(() => {
  resize.disconnect();
});

const range = shallowRef<ChartRange | null>(null);

watch(
  [() => props.values, () => props.center],
  ([values, center]) => {
    if (center === null) {
      return;
    }
    range.value = holdRange(range.value, deviationExtent(values, center, props.minimumExtent), Date.now());
  },
  { immediate: true },
);

const model = computed(() =>
  props.center === null || range.value === null
    ? null
    : deviationChart(props.values, props.center, props.unit, range.value, width.value),
);
</script>

<template>
  <figure
    v-if="model"
    ref="figure"
    class="chart"
  >
    <svg
      :id="chartId"
      :viewBox="`0 0 ${model.width} ${CHART.height}`"
      role="img"
      :aria-label="label"
      @pointerleave="leave"
    >
      <g class="ticks">
        <template
          v-for="tick in model.ticks"
          :key="tick.y"
        >
          <line
            :x1="CHART.left"
            :x2="model.width - CHART.right"
            :y1="tick.y"
            :y2="tick.y"
            :class="tick.isAxis ? 'axis' : 'grid'"
          />
          <text
            :x="CHART.left - 6"
            :y="tick.y + 4"
            class="tick"
            text-anchor="end"
          >{{ tick.label }}</text>
        </template>
      </g>
      <g
        v-for="slot in model.slots"
        :key="slot.group"
        class="slot"
        @pointerenter="enter(slot.group, $event)"
        @pointerup="tap(slot.group, $event)"
      >
        <rect
          :x="slot.x"
          :y="CHART.top"
          :width="slot.width"
          :height="model.plotHeight"
          class="band"
          :class="{ 'band--hovered': hovered === slot.group }"
        />
        <text
          v-if="slot.labelX !== null"
          :x="slot.labelX"
          :y="CHART.height - 8"
          class="tick"
          text-anchor="middle"
        >
          {{ slot.group }}
        </text>
        <rect
          v-if="slot.bar"
          v-bind="slot.bar"
          rx="2"
          class="bar"
          :class="[barKind(slot.group) && `bar--${barKind(slot.group)}`, { 'bar--hovered': hovered === slot.group }]"
        />
      </g>
    </svg>
    <figcaption><slot /></figcaption>
  </figure>
</template>

<style scoped>
.chart {
  margin: 0 0 12px;
}

svg {
  display: block;
  width: 100%;
  height: auto;
}

figcaption {
  color: var(--muted);
  font-size: 13px;
}

.ticks {
  pointer-events: none;
}

.grid {
  stroke: var(--grid);
}

.axis {
  stroke: var(--muted);
}

.tick {
  fill: var(--muted);
  font-size: 12px;
}

.band {
  fill: transparent;
}

.band--hovered {
  fill: color-mix(in srgb, var(--hover) 22%, transparent);
}

.bar {
  fill: var(--accent);
  pointer-events: none;
}

.bar--outlier {
  fill: var(--error);
}

.bar--balancing {
  fill: var(--balancing);
}

.bar--hovered {
  stroke: var(--text);
  stroke-width: 2;
}
</style>
