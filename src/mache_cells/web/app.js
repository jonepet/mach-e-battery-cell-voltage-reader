const SVG = 'http://www.w3.org/2000/svg';
const CHART = { width: 960, height: 260, left: 52, right: 12, top: 12, bottom: 28 };

const byId = (id) => document.getElementById(id);
const ui = {
  form: byId('connection'),
  port: byId('port'),
  refresh: byId('refresh'),
  connect: byId('connect'),
  disconnect: byId('disconnect'),
  status: byId('status'),
  vehicle: byId('vehicle'),
  battery: byId('battery'),
  temperature: byId('temperature'),
  cellError: byId('cell-error'),
  cellStats: byId('cell-stats'),
  chart: byId('chart'),
  cellTable: byId('cell-table'),
  adapter: byId('adapter'),
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) {
    node.className = className;
  }
  if (text !== undefined) {
    node.textContent = text;
  }
  return node;
}

function svgElement(tag, attributes) {
  const node = document.createElementNS(SVG, tag);
  Object.entries(attributes).forEach(([name, value]) => node.setAttribute(name, String(value)));
  return node;
}

async function api(method, path, body) {
  const response = await fetch(`api/${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.detail ?? response.statusText);
  }
  return payload;
}

function facts(list, entries) {
  list.replaceChildren(...entries.flatMap(([term, value]) => [element('dt', '', term), element('dd', '', value)]));
}

function signalTile(signal) {
  const tile = element('div', signal.value === null ? 'tile tile--error' : 'tile');
  const digits = { minimumFractionDigits: signal.decimals, maximumFractionDigits: signal.decimals };
  const value = signal.value === null ? 'Read failed' : `${signal.value.toLocaleString('en', digits)} ${signal.unit}`;
  tile.append(element('span', 'tile__label', signal.label), element('span', 'tile__value', value));
  if (signal.error) {
    tile.title = signal.error;
  }
  return tile;
}

function renderSignals(signals) {
  [ui.vehicle, ui.battery, ui.temperature].forEach((container) => {
    container.replaceChildren(...signals.filter((s) => s.group === container.id).map(signalTile));
  });
}

const millivolts = (volts) => `${(volts * 1000).toFixed(1)} mV`;
const signedMillivolts = (volts) => `${volts >= 0 ? '+' : ''}${millivolts(volts)}`;

function renderStats(stats, voltages) {
  if (!stats) {
    ui.cellStats.replaceChildren();
    return;
  }
  const outliers = stats.outliers.length ? stats.outliers.map((cell) => `#${cell}`).join(', ') : 'None';
  facts(ui.cellStats, [
    ['Readings', `${stats.valid} / ${voltages.length}`],
    ['Minimum', `${stats.minimum.toFixed(4)} V (#${stats.min_cell})`],
    ['Maximum', `${stats.maximum.toFixed(4)} V (#${stats.max_cell})`],
    ['Mean', `${stats.mean.toFixed(4)} V`],
    ['Spread', `${millivolts(stats.spread)}${stats.spread_exceeded ? ' — above warning limit' : ''}`],
    ['Std. deviation', millivolts(stats.stdev)],
    ['Outliers', outliers],
  ]);
}

function niceStep(range) {
  const rough = range / 4;
  const magnitude = 10 ** Math.floor(Math.log10(rough));
  return [1, 2, 5, 10].map((factor) => factor * magnitude).find((step) => step >= rough);
}

function renderChart(voltages, stats) {
  const { width, height, left, right, top, bottom } = CHART;
  ui.chart.setAttribute('viewBox', `0 0 ${width} ${height}`);
  if (!stats) {
    ui.chart.replaceChildren();
    return;
  }
  const deviations = voltages.map((value) => (value === null ? null : (value - stats.median) * 1000));
  const extent = Math.max(2, ...deviations.filter((value) => value !== null).map(Math.abs));
  const step = niceStep(extent * 2);
  const limit = Math.ceil(extent / step) * step;
  const plotHeight = height - top - bottom;
  const y = (millivolt) => top + ((limit - millivolt) / (2 * limit)) * plotHeight;
  const slot = (width - left - right) / voltages.length;
  const outliers = new Set(stats.outliers);
  const nodes = [];
  for (let tick = -limit; tick <= limit + step / 2; tick += step) {
    nodes.push(svgElement('line', { x1: left, x2: width - right, y1: y(tick), y2: y(tick), class: tick === 0 ? 'axis' : 'grid' }));
    const label = svgElement('text', { x: left - 6, y: y(tick) + 4, class: 'tick', 'text-anchor': 'end' });
    label.textContent = `${tick > 0 ? '+' : ''}${Number(tick.toFixed(2))} mV`;
    nodes.push(label);
  }
  deviations.forEach((deviation, index) => {
    const cell = index + 1;
    if ((cell - 1) % 3 === 0) {
      const label = svgElement('text', { x: left + slot * (index + 0.5), y: height - 8, class: 'tick', 'text-anchor': 'middle' });
      label.textContent = String(cell);
      nodes.push(label);
    }
    if (deviation === null) {
      return;
    }
    const barTop = Math.min(y(deviation), y(0));
    const bar = svgElement('rect', {
      x: left + slot * index + slot * 0.15,
      width: slot * 0.7,
      y: barTop,
      height: Math.max(1, Math.abs(y(deviation) - y(0))),
      rx: 2,
      class: outliers.has(cell) ? 'bar bar--outlier' : 'bar',
    });
    const tooltip = svgElement('title', {});
    tooltip.textContent = `Cell ${cell}: ${voltages[index].toFixed(4)} V (${signedMillivolts(deviation / 1000)})`;
    bar.append(tooltip);
    nodes.push(bar);
  });
  ui.chart.replaceChildren(...nodes);
}

function renderTable(voltages, stats) {
  const rows = voltages.map((value, index) => {
    const row = element('tr', stats?.outliers.includes(index + 1) ? 'row--outlier' : '');
    row.append(
      element('td', '', String(index + 1)),
      element('td', '', value === null ? 'No value' : `${value.toFixed(4)} V`),
      element('td', '', value === null || !stats ? '' : signedMillivolts(value - stats.median)),
    );
    return row;
  });
  ui.cellTable.replaceChildren(...rows);
}

function renderReading(reading) {
  renderSignals(reading?.signals ?? []);
  ui.cellError.hidden = !reading?.cell_error;
  ui.cellError.textContent = reading?.cell_error ? `Cell read failed: ${reading.cell_error}` : '';
  renderStats(reading?.stats, reading?.voltages ?? []);
  renderChart(reading?.voltages ?? [], reading?.stats);
  renderTable(reading?.voltages ?? [], reading?.stats);
}

function renderState(state) {
  const connected = state.status === 'connected';
  ui.connect.disabled = connected || state.status === 'connecting';
  ui.disconnect.disabled = !connected;
  ui.status.textContent = [state.status, state.port, state.error].filter(Boolean).join(' — ');
  ui.status.dataset.status = state.status;
  facts(ui.adapter, [
    ['Port', state.port ?? '—'],
    ['Device', state.adapter?.device ?? '—'],
    ['ELM version', state.adapter?.elm_version ?? '—'],
    ['Adapter supply', state.adapter?.battery_voltage ?? '—'],
    ['Read duration', state.reading ? `${state.reading.duration_s.toFixed(1)} s` : '—'],
  ]);
  renderReading(state.reading);
}

async function refreshPorts() {
  const ports = await api('GET', 'ports');
  const current = ui.port.value;
  ui.port.replaceChildren(...ports.map((port) => {
    const option = element('option', '', port);
    option.value = port;
    return option;
  }));
  if (ports.includes(current)) {
    ui.port.value = current;
  }
}

async function attempt(action) {
  try {
    renderState(await action());
  } catch (error) {
    ui.status.textContent = error.message;
  }
}

async function poll() {
  try {
    renderState(await api('GET', 'state'));
  } catch (error) {
    ui.status.textContent = `Reader service unreachable: ${error.message}`;
  }
  window.setTimeout(poll, 1000);
}

ui.form.addEventListener('submit', (event) => {
  event.preventDefault();
  attempt(() => api('PUT', 'connection', { port: ui.port.value }));
});
ui.disconnect.addEventListener('click', () => attempt(() => api('DELETE', 'connection')));
ui.refresh.addEventListener('click', () => refreshPorts().catch((error) => {
  ui.status.textContent = error.message;
}));

refreshPorts().catch((error) => {
  ui.status.textContent = error.message;
});
poll();
