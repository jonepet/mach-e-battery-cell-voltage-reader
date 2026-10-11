<script setup lang="ts">
import { computed } from 'vue';

import { CHART, deviationChart } from '../chart';
import { useGroupHover } from '../composables/useGroupHover';

const props = defineProps<{
  chartId: string;
  label: string;
  values: readonly (number | null)[];
  center: number | null;
  unit: string;
  minimumExtent: number;
  highlighted: ReadonlySet<number>;
  highlightClass: 'outlier' | 'balancing';
}>();

const { group: hovered, set: setHovered } = useGroupHover();

const model = computed(() =>
  props.center === null ? null : deviationChart(props.values, props.center, props.unit, props.minimumExtent),
);
</script>

<template>
  <figure
    v-if="model"
    class="chart"
  >
    <svg
      :id="chartId"
      :viewBox="`0 0 ${CHART.width} ${CHART.height}`"
      role="img"
      :aria-label="label"
      @pointerleave="setHovered(null)"
    >
      <g class="ticks">
        <template
          v-for="tick in model.ticks"
          :key="tick.y"
        >
          <line
            :x1="CHART.left"
            :x2="CHART.width - CHART.right"
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
        @pointerenter="setHovered(slot.group)"
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
          :class="[
            { [`bar--${highlightClass}`]: highlighted.has(slot.group), 'bar--hovered': hovered === slot.group },
          ]"
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
  font-size: 11px;
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
