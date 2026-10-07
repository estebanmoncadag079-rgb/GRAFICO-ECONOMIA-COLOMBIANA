"use strict";

(async function () {
  const MONTHS = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  const COLORS = {"1A": "#ffa657", "5A": "#38bdf8", "10A": "#bc8cff"};
  const CONFIG = {displaylogo: false, scrollZoom: true, responsive: true,
    displayModeBar: "hover", doubleClick: "reset", modeBarButtons: [["resetScale2d", "toImage"]]};
  const state = {ranges: {}, pinned: null, detailWindow: "1A"};
  let payload;

  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function day(value) {
    if (typeof value === "number") return value;
    if (value instanceof Date) return Date.parse(value.toISOString().slice(0, 10) + "T00:00:00Z");
    return Date.parse(String(value).slice(0, 10) + "T00:00:00Z");
  }
  function dateLabel(value, frequency = "daily") {
    const date = new Date(day(value));
    const month = date.getUTCMonth();
    const year = date.getUTCFullYear();
    if (frequency === "quarterly") return `T${Math.floor(month / 3) + 1} ${year}`;
    if (frequency === "monthly") return `${MONTHS[month]} ${year}`;
    return `${String(date.getUTCDate()).padStart(2, "0")} ${MONTHS[month]} ${year}`;
  }
  function numbers(values) {
    if (Array.isArray(values) || ArrayBuffer.isView(values)) return values;
    if (!values || !values.bdata) return [];
    const types = {f8: Float64Array, f4: Float32Array, i4: Int32Array,
      i2: Int16Array, i1: Int8Array, u4: Uint32Array, u2: Uint16Array, u1: Uint8Array};
    const Type = types[values.dtype];
    if (!Type) return [];
    const bytes = Uint8Array.from(atob(values.bdata), c => c.charCodeAt(0));
    return new Type(bytes.buffer);
  }
  function selections(id) {
    return new Set([...document.querySelectorAll(`#${id} input:checked`)].map(input => input.value));
  }
  function selectedRadio(id) {
    return document.querySelector(`#${id} input:checked`)?.value;
  }
  function lastAtOrBefore(rows, reference, dateKey, required = []) {
    for (let i = rows.length - 1; i >= 0; i--) {
      const row = rows[i];
      if (day(row[dateKey]) <= reference && required.every(key => row[key] != null)) return row;
    }
    return null;
  }
  function lastObservation(trace, reference) {
    const values = numbers(trace.y);
    for (let i = trace.x.length - 1; i >= 0; i--) {
      const value = Number(values[i]);
      if (day(trace.x[i]) <= reference && values[i] != null && Number.isFinite(value)) {
        return {value, date: trace.x[i]};
      }
    }
    return null;
  }
  function latestTraceDate(traces) {
    return Math.max(...traces.filter(trace => trace.visible !== false && trace.meta && trace.x?.length)
      .map(trace => day(trace.x[trace.x.length - 1])));
  }
  function textElement(tag, className, value) {
    const element = document.createElement(tag);
    element.className = className;
    element.textContent = value;
    return element;
  }
  function updateReadout(id, reference) {
    const graph = document.getElementById(id);
    const target = document.getElementById(`${id}-readout`);
    if (!graph?.data || !target) return;
    const traces = graph.data.filter(trace => trace.meta && trace.x?.length &&
      trace.visible !== false && trace.visible !== "legendonly");
    if (!traces.length) {
      target.replaceChildren(textElement("div", "readout-empty", "Sin series activas"));
      return;
    }
    if (!Number.isFinite(reference)) reference = latestTraceDate(traces);
    const date = textElement("div", "readout-date", `Referencia: ${dateLabel(reference)}`);
    const values = document.createElement("div");
    values.className = "readout-values";
    for (const trace of traces) {
      const item = lastObservation(trace, reference);
      const entry = document.createElement("div");
      entry.className = "readout-series";
      const label = document.createElement("div");
      label.className = "readout-label";
      const swatch = textElement("span", "readout-swatch", "");
      swatch.style.borderColor = trace.line?.color || trace.marker?.color || "#64748b";
      swatch.style.borderTopStyle = trace.line?.dash ? "dashed" : "solid";
      label.append(swatch, textElement("span", "", trace.meta.label));
      const unit = trace.meta.unit === "%" ? "%" : ` ${trace.meta.unit}`;
      const value = item ? item.value.toLocaleString("es-CO", {minimumFractionDigits: 2,
        maximumFractionDigits: 2}) + unit : "Sin dato";
      const period = item ? dateLabel(item.date, trace.meta.frequency) : "Sin observación previa";
      entry.append(label, textElement("strong", "readout-value", value),
        textElement("span", "readout-period", period +
          (trace.meta.axis ? ` · eje ${trace.meta.axis}` : "")));
      values.append(entry);
    }
    target.replaceChildren(date, values);
  }

  function inflationRange(fig, range) {
    const values = [0];
    for (const trace of fig.data) {
      if (trace.visible === false) continue;
      const numbersY = numbers(trace.y);
      const factor = trace.yaxis === "y2" ? 10 : 1;
      for (let i = 0; i < trace.x.length; i++) {
        if (range && (day(trace.x[i]) < day(range[0]) || day(trace.x[i]) > day(range[1]))) continue;
        if (numbersY[i] != null && Number.isFinite(Number(numbersY[i]))) values.push(Number(numbersY[i]) * factor);
      }
    }
    const low = Math.min(...values);
    const high = Math.max(...values);
    const pad = Math.max((high - low) * 0.08, 0.5);
    fig.layout.yaxis.range = [low - pad, high + pad];
    fig.layout.yaxis2.range = [(low - pad) / 10, (high + pad) / 10];
    fig.layout.yaxis.visible = fig.data.some(trace => trace.visible !== false && trace.yaxis !== "y2");
    fig.layout.yaxis2.visible = fig.data.some(trace => trace.visible !== false && trace.yaxis === "y2");
  }
  function configureFigure(id, selected, range) {
    const fig = clone(payload.figures[id]);
    if (id === "chart-bolsa") {
      const keys = ["oficial", "equiponderado", "grandes"];
      fig.data.forEach((trace, i) => { trace.visible = selected.has(keys[i]); });
      if (!selected.has("oficial")) {
        fig.layout.shapes = [];
        fig.layout.annotations = [];
      }
    } else if (id === "chart-inflacion") {
      const keys = {"IPC mensual": "inf_mensual", "IPC anual": "inf_anual", "PIB real interanual": "pib"};
      fig.data.forEach(trace => { trace.visible = selected.has(keys[trace.meta.label]); });
      inflationRange(fig, range);
    } else if (id === "chart-tes") {
      const spread = selected.has("1A") && selected.has("10A");
      fig.data.forEach((trace, i) => {
        trace.visible = i < 3 ? selected.has(["1A", "5A", "10A"][i]) : spread;
      });
      fig.layout.yaxis.domain = spread ? [0.36, 1] : [0, 1];
      fig.layout.xaxis.anchor = spread ? "y2" : "y";
      fig.layout.yaxis2.visible = spread;
      fig.layout.annotations = (fig.layout.annotations || []).filter(annotation =>
        spread || !String(annotation.text || "").includes("Pendiente de la curva"));
    }
    if (range) {
      fig.layout.xaxis.range = range;
      fig.layout.xaxis.autorange = false;
    } else {
      delete fig.layout.xaxis.range;
      fig.layout.xaxis.autorange = true;
    }
    return fig;
  }
  function layersFor(id) {
    if (id === "chart-bolsa") return selections("bolsa-layers");
    if (id === "chart-inflacion") return selections("inf-layers");
    return selections("curve-toggle");
  }
  async function drawMain(id) {
    const fig = configureFigure(id, layersFor(id), state.ranges[id]);
    await Plotly.react(id, fig.data, fig.layout, CONFIG);
    updateReadout(id);
  }
  function setDate(id, value, pinned) {
    const reference = day(value);
    if (!Number.isFinite(reference)) return;
    updateReadout(id, reference);
    if (pinned) state.pinned = reference;
    if (state.pinned == null || pinned) updateCurve(state.pinned ?? reference);
  }
  function attachMainEvents(id) {
    const graph = document.getElementById(id);
    graph.on("plotly_hover", event => setDate(id, event.points[0]?.x, false));
    graph.on("plotly_click", event => setDate(id, event.points[0]?.x, true));
    graph.on("plotly_relayout", event => {
      if (event["xaxis.range[0]"] && event["xaxis.range[1]"]) {
        state.ranges[id] = [event["xaxis.range[0]"], event["xaxis.range[1]"]];
      } else if (event["xaxis.autorange"]) {
        delete state.ranges[id];
      } else {
        return;
      }
      if (id === "chart-inflacion") {
        const fig = configureFigure(id, layersFor(id), state.ranges[id]);
        Plotly.relayout(graph, {"yaxis.range": fig.layout.yaxis.range,
          "yaxis2.range": fig.layout.yaxis2.range});
      }
    });
  }

  function metric(title, value, color, subtitle) {
    const card = document.createElement("div");
    card.className = "static-metric";
    const heading = textElement("div", "static-metric-title help-label", title);
    heading.tabIndex = 0;
    heading.dataset.help = payload.help[title] || "";
    const number = textElement("div", "static-metric-value", value);
    number.style.color = color;
    card.append(heading, number, textElement("div", "static-metric-subtitle", subtitle));
    return card;
  }
  function updateCurve(reference) {
    const tables = payload.tables;
    const tenors = selections("curve-toggle");
    const tes = lastAtOrBefore(tables.tes, reference, "fecha",
      ["tes_pesos_1y", "tes_pesos_5y", "tes_pesos_10y"]);
    const date = document.getElementById("fecha-activa");
    date.textContent = `${state.pinned == null ? "Referencia" : "Fecha fijada"}: ${dateLabel(reference)}`;
    const cards = document.getElementById("curve-metrics");
    cards.replaceChildren();
    if (tes) {
      const keys = {"1A": "tes_pesos_1y", "5A": "tes_pesos_5y", "10A": "tes_pesos_10y"};
      const terms = {"1A": "Corto plazo", "5A": "Medio plazo", "10A": "Largo plazo"};
      for (const tenor of ["1A", "5A", "10A"]) {
        if (tenors.has(tenor)) cards.append(metric(`TES ${tenor}`,
          `${Number(tes[keys[tenor]]).toFixed(2)}%`, COLORS[tenor],
          `${terms[tenor]} · ${dateLabel(tes.fecha)}`));
      }
      if (tenors.has("1A") && tenors.has("10A")) {
        const spread = tes.tes_pesos_10y - tes.tes_pesos_1y;
        const phase = spread > 0.3 ? "Normal" : spread < 0 ? "Invertida" : "Plana";
        const color = spread > 0.3 ? "#58a6ff" : spread < 0 ? "#ff7b72" : "#e3b341";
        cards.append(metric("Spread 10A-1A", `${spread >= 0 ? "+" : ""}${spread.toFixed(2)}pp`,
          color, `${phase} · ${dateLabel(tes.fecha)}`));
      }
      const curve = clone(payload.figures["curve-chart"]);
      const selected = ["1A", "5A", "10A"].filter(key => tenors.has(key));
      const labels = {"1A": "1 Año\n(corto)", "5A": "5 Años\n(medio)", "10A": "10 Años\n(largo)"};
      const xs = selected.map(key => labels[key]);
      const ys = selected.map(key => Number(tes[keys[key]]));
      for (const trace of curve.data) { trace.x = xs; trace.y = ys; }
      curve.data[1].text = ys.map(value => `<b>${value.toFixed(2)}%</b>`);
      curve.data[1].marker.color = selected.map(key => COLORS[key]);
      if (ys.length) {
        const pad = Math.max((Math.max(...ys) - Math.min(...ys)) * 0.55, 0.6);
        curve.layout.yaxis.range = [Math.min(...ys) - pad, Math.max(...ys) + pad];
      }
      Plotly.react("curve-chart", curve.data, curve.layout,
        {displaylogo: false, responsive: true, displayModeBar: "hover", modeBarButtons: [["toImage"]]});
    } else {
      Plotly.purge("curve-chart");
    }
    const colcap = lastAtOrBefore(tables.colcap, reference, "fecha", ["colcap_puntos"]);
    if (colcap) cards.append(metric("COLCAP oficial",
      Number(colcap.colcap_puntos).toLocaleString("es-CO", {minimumFractionDigits: 2,
        maximumFractionDigits: 2}), "#3fb950", `puntos · ${dateLabel(colcap.fecha)}`));
    const inflation = lastAtOrBefore(tables.inflation, reference, "reference_end", ["inflacion_anual"]);
    if (inflation?.inflacion_mensual != null) cards.append(metric("Inflación mensual",
      `${Number(inflation.inflacion_mensual).toFixed(2)}%`, "#fb923c", dateLabel(inflation.fecha, "monthly")));
    if (inflation) cards.append(metric("Inflación anual 12M",
      `${Number(inflation.inflacion_anual).toFixed(2)}%`, "#f43f5e", dateLabel(inflation.fecha, "monthly")));
    const gdp = lastAtOrBefore(tables.gdp, reference, "reference_end", ["pib_real_yoy"]);
    if (gdp) cards.append(metric("PIB real interanual",
      `${Number(gdp.pib_real_yoy).toFixed(2)}%`, "#14b8a6",
      `${gdp.trimestre} · vintage ${gdp.fecha_publicacion_vintage}`));
  }

  function windowRange(traces, windowKey) {
    if (windowKey === "ALL") return null;
    const latest = latestTraceDate(traces);
    const earlier = new Date(latest);
    if (windowKey.endsWith("M")) earlier.setUTCMonth(earlier.getUTCMonth() - parseInt(windowKey));
    if (windowKey.endsWith("A")) earlier.setUTCFullYear(earlier.getUTCFullYear() - parseInt(windowKey));
    return [earlier.toISOString().slice(0, 10), new Date(latest).toISOString().slice(0, 10)];
  }
  async function drawDetail() {
    const variable = selectedRadio("detail-var") || "bolsa";
    const source = variable === "bolsa" ? "chart-bolsa" : variable === "tes" ? "chart-tes" : "chart-inflacion";
    const layers = variable === "inflacion" ? new Set(["inf_mensual", "inf_anual"]) :
      variable === "pib" ? new Set(["pib"]) : variable === "inf_pib" ?
        new Set(["inf_anual", "pib"]) : layersFor(source);
    const fig = configureFigure(source, layers, null);
    const range = windowRange(fig.data, state.detailWindow);
    if (range) {
      fig.layout.xaxis.range = range;
      fig.layout.xaxis.autorange = false;
    }
    if (source === "chart-inflacion") inflationRange(fig, range);
    fig.layout.height = 500;
    fig.layout.uirevision = `${variable}|${state.detailWindow}`;
    await Plotly.react("detail-chart", fig.data, fig.layout, CONFIG);
    updateReadout("detail-chart");
  }

  async function start() {
    const response = await fetch("dashboard.json");
    if (!response.ok) throw new Error(`Datos: HTTP ${response.status}`);
    payload = await response.json();
    for (const id of ["chart-bolsa", "chart-inflacion", "chart-tes"]) {
      await drawMain(id);
      attachMainEvents(id);
    }
    const cycle = payload.figures["cycle-6A"];
    await Plotly.newPlot("cycle-chart", cycle.data, cycle.layout,
      {displaylogo: false, responsive: true, modeBarButtons: [["zoom2d", "pan2d", "resetScale2d"]]});
    document.getElementById("cycle-window").addEventListener("change", () => {
      const key = selectedRadio("cycle-window") || "6A";
      const fig = payload.figures[`cycle-${key}`];
      Plotly.react("cycle-chart", fig.data, fig.layout,
        {displaylogo: false, responsive: true, modeBarButtons: [["zoom2d", "pan2d", "resetScale2d"]]});
    });
    const dates = [payload.tables.tes, payload.tables.colcap].map(rows => day(rows[rows.length - 1].fecha));
    updateCurve(Math.max(...dates));
    document.getElementById("btn-soltar").addEventListener("click", () => {
      state.pinned = null;
      updateCurve(Math.max(...dates));
    });
    for (const [control, chart] of [["bolsa-layers", "chart-bolsa"],
      ["inf-layers", "chart-inflacion"], ["curve-toggle", "chart-tes"]]) {
      document.getElementById(control).addEventListener("change", async () => {
        await drawMain(chart);
        if (control === "curve-toggle") updateCurve(state.pinned ?? Math.max(...dates));
        if (document.getElementById("modal").style.display === "block") drawDetail();
      });
    }
    const modal = document.getElementById("modal");
    document.getElementById("open-modal").addEventListener("click", () => {
      modal.style.display = "block";
      document.body.classList.add("modal-open");
      drawDetail();
    });
    const close = () => { modal.style.display = "none"; document.body.classList.remove("modal-open"); };
    document.getElementById("close-modal").addEventListener("click", close);
    modal.addEventListener("click", event => { if (event.target === modal) close(); });
    document.addEventListener("keydown", event => { if (event.key === "Escape") close(); });
    document.getElementById("detail-var").addEventListener("change", drawDetail);
    for (const windowKey of ["3M", "6M", "1A", "3A", "5A", "ALL"]) {
      document.getElementById(`detail-btn-${windowKey}`).addEventListener("click", () => {
        state.detailWindow = windowKey;
        const labels = {"3M": "3 meses", "6M": "6 meses", "1A": "1 año", "3A": "3 años",
          "5A": "5 años", "ALL": "Todo el período"};
        document.getElementById("detail-periodo-label").textContent = `Mostrando: ${labels[windowKey]}`;
        drawDetail();
      });
    }
    document.getElementById("detail-periodo-label").textContent = "Mostrando: 1 año";
  }

  try { await start(); }
  catch (error) {
    console.error(error);
    const notice = textElement("div", "static-error", "No se pudieron cargar los gráficos. Recarga la página.");
    document.querySelector(".dashboard-header")?.after(notice);
  }
}());
