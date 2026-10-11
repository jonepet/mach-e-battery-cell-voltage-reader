import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, h, nextTick, shallowRef } from 'vue';

import CellVoltagesPanel from './components/CellVoltagesPanel.vue';
import GroupHealthPanel from './components/GroupHealthPanel.vue';
import GroupReadout from './components/GroupReadout.vue';
import { provideGroupHover } from './composables/useGroupHover';
import type { Reading } from './types';

const voltages = [3.7, 3.71, 3.69];
const MOUSE = { pointerType: 'mouse' };
const TOUCH = { pointerType: 'touch' };

const reading: Reading = {
  timestamp: 1_791_720_000,
  duration_s: 1,
  voltages,
  voltages_age_s: 1.2,
  stats: {
    valid: 3,
    minimum: 3.69,
    maximum: 3.71,
    mean: 3.7,
    median: 3.7,
    stdev: 0.01,
    spread: 0.02,
    min_cell: 3,
    max_cell: 2,
    outliers: [3],
    spread_exceeded: false,
  },
  cell_error: null,
  health: {
    capacities: [250, 251, 249],
    reference_capacity: 250,
    health: [100, 100.4, 99.6],
    minimum: 249,
    maximum: 251,
    mean: 250,
    weakest_group: 3,
    strongest_group: 2,
  },
  health_error: null,
  balancing: {
    active: [false, true, true],
    seconds: [0, 125, 60],
    active_count: 2,
    longest_s: 125,
  },
  balancing_error: null,
  signals: [
    { key: 'soh', label: 'State of health', group: 'battery', unit: '%', decimals: 1, value: 100 },
  ],
};

const current = shallowRef(reading);

const Page = defineComponent({
  setup() {
    provideGroupHover();
    return () =>
      h('div', [
        h(CellVoltagesPanel, { reading: current.value }),
        h(GroupHealthPanel, { reading: current.value }),
        h(GroupReadout, { reading: current.value }),
      ]);
  },
});

beforeEach(() => {
  current.value = reading;
});

describe('cell voltage panel', () => {
  it('colours balancing groups, lets outliers win, and shows the measurement age and balancing facts', () => {
    const page = mount(Page);

    expect(page.findAll('#chart .bar').map((bar) => [bar.classes('bar--outlier'), bar.classes('bar--balancing')])).toEqual([
      [false, false],
      [false, true],
      [true, false],
    ]);
    const panel = page.get('#cells-panel').text();
    expect(panel).toContain('Measured by the battery module 1 s ago');
    expect(panel).toContain('Groups balancing2 / 3');
    expect(panel).toContain('Longest running2 min');
  });

  it('counts the measurement age up between readings and restarts it with a new reading', async () => {
    vi.useFakeTimers();
    try {
      const panel = mount(Page);

      await vi.advanceTimersByTimeAsync(3000);
      expect(panel.get('.age').text()).toBe('Measured by the battery module 4 s ago');

      current.value = { ...reading, timestamp: reading.timestamp + 3, voltages_age_s: 0 };
      await nextTick();
      expect(panel.get('.age').text()).toBe('Measured by the battery module 0 s ago');
    } finally {
      vi.useRealTimers();
    }
  });
});

describe('group hover', () => {
  it('highlights the hovered group in every chart and the table, and shows its values', async () => {
    const page = mount(Page);

    await page.findAll('#health-chart .slot')[1]?.trigger('pointerenter', MOUSE);

    for (const chart of ['#chart', '#health-chart']) {
      const bands = page.findAll(`${chart} .band`);
      expect(bands.map((band) => band.classes('band--hovered'))).toEqual([false, true, false]);
      expect(page.findAll(`${chart} .bar`).map((bar) => bar.classes('bar--hovered'))).toEqual([false, true, false]);
    }
    expect(page.findAll('tbody tr').map((row) => row.classes('row--hovered'))).toEqual([false, true, false]);
    const readout = page.get('.readout').text();
    expect(readout).toContain('Cell group #2');
    expect(readout).toContain('3.7100 V');
    expect(readout).toContain('Yes, 2 min');
    expect(readout).not.toContain('State of charge');
  });

  it('clears the hover when the pointer leaves the chart', async () => {
    const page = mount(Page);
    await page.findAll('#chart .slot')[0]?.trigger('pointerenter', MOUSE);

    await page.get('#chart').trigger('pointerleave', MOUSE);

    expect(page.findAll('.band--hovered')).toHaveLength(0);
    expect(page.findAll('.row--hovered')).toHaveLength(0);
    expect(page.get('.readout').text()).toContain('Hover or tap a cell group');
  });

  it('highlights the hovered group from a table row', async () => {
    const page = mount(Page);

    await page.findAll('tbody tr')[2]?.trigger('pointerenter', MOUSE);

    expect(page.findAll('#health-chart .band').map((band) => band.classes('band--hovered'))).toEqual([
      false,
      false,
      true,
    ]);
  });

  it('keeps a tapped group selected after the finger lifts, until it is tapped again', async () => {
    const page = mount(Page);
    const slot = page.findAll('#chart .slot')[1];

    await slot?.trigger('pointerenter', TOUCH);
    await slot?.trigger('pointerup', TOUCH);
    await page.get('#chart').trigger('pointerleave', TOUCH);

    expect(page.findAll('#health-chart .band').map((band) => band.classes('band--hovered'))).toEqual([
      false,
      true,
      false,
    ]);
    expect(page.get('.readout').text()).toContain('Cell group #2');

    await slot?.trigger('pointerup', TOUCH);

    expect(page.findAll('.band--hovered')).toHaveLength(0);
  });

  it('moves the selection to another tapped group', async () => {
    const page = mount(Page);

    await page.findAll('#chart .slot')[0]?.trigger('pointerup', TOUCH);
    await page.findAll('tbody tr')[2]?.trigger('pointerup', TOUCH);

    expect(page.get('.readout').text()).toContain('Cell group #3');
  });
});
