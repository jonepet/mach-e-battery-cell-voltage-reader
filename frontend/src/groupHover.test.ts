import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { defineComponent, h } from 'vue';

import BalancingPanel from './components/BalancingPanel.vue';
import CellVoltagesPanel from './components/CellVoltagesPanel.vue';
import GroupHealthPanel from './components/GroupHealthPanel.vue';
import GroupReadout from './components/GroupReadout.vue';
import { provideGroupHover } from './composables/useGroupHover';
import type { Reading } from './types';

const voltages = [3.7, 3.71, 3.69];

const reading: Reading = {
  duration_s: 1,
  voltages,
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
    outliers: [],
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
    charge: [50, 50.5, 49.5],
    charge_mean: 50,
    charge_min: 49.5,
    charge_max: 50.5,
    active: [false, true, false],
    seconds: [0, 125, 0],
    active_count: 1,
    longest_s: 125,
  },
  balancing_error: null,
  signals: [
    { key: 'soh', label: 'State of health', group: 'battery', unit: '%', decimals: 1, value: 100 },
  ],
};

const Page = defineComponent({
  setup() {
    provideGroupHover();
    return () =>
      h('div', [
        h(CellVoltagesPanel, { reading }),
        h(GroupHealthPanel, { reading }),
        h(BalancingPanel, { reading }),
        h(GroupReadout, { reading }),
      ]);
  },
});

describe('group hover', () => {
  it('highlights the hovered group in every chart and the table, and shows its values', async () => {
    const page = mount(Page);

    await page.findAll('#health-chart .slot')[1]?.trigger('pointerenter');

    for (const chart of ['#chart', '#health-chart', '#balancing-chart']) {
      const bands = page.findAll(`${chart} .band`);
      expect(bands.map((band) => band.classes('band--hovered'))).toEqual([false, true, false]);
      expect(page.findAll(`${chart} .bar`).map((bar) => bar.classes('bar--hovered'))).toEqual([false, true, false]);
    }
    expect(page.findAll('tbody tr').map((row) => row.classes('row--hovered'))).toEqual([false, true, false]);
    const readout = page.get('.readout').text();
    expect(readout).toContain('Cell group #2');
    expect(readout).toContain('3.7100 V');
    expect(readout).toContain('Yes, 2 min');
  });

  it('clears the hover when the pointer leaves the chart', async () => {
    const page = mount(Page);
    await page.findAll('#chart .slot')[0]?.trigger('pointerenter');

    await page.get('#chart').trigger('pointerleave');

    expect(page.findAll('.band--hovered')).toHaveLength(0);
    expect(page.findAll('.row--hovered')).toHaveLength(0);
    expect(page.get('.readout').text()).toContain('Hover a cell group');
  });

  it('highlights the hovered group from a table row', async () => {
    const page = mount(Page);

    await page.findAll('tbody tr')[2]?.trigger('pointerenter');

    expect(page.findAll('#balancing-chart .band').map((band) => band.classes('band--hovered'))).toEqual([
      false,
      false,
      true,
    ]);
  });
});
