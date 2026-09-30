(function () {
  "use strict";
  // Tras desplazar o acercar un gráfico, ajusta el eje vertical a los datos del
  // tramo visible, como en una plataforma de trading. Los valores no cambian;
  // solo el rango que se dibuja.
  const CHARTS = ["chart-bolsa", "chart-inflacion", "chart-tes", "detail-chart"];
  // Todas las fechas en hora local; "2026-08-31" (sin hora) se leería en UTC
  // y desplazaría el tramo visible cinco horas en Colombia.
  const time = value => {
    const text = String(value).replace(" ", "T");
    return Date.parse(text.length === 10 ? `${text}T00:00:00` : text);
  };

  function visibleValues(gd, start, end, axis) {
    const values = [];
    (gd._fullData || []).forEach(trace => {
      if (trace.visible !== true || (trace.yaxis || "y") !== axis || !trace.x || !trace.y) return;
      for (let i = 0; i < trace.x.length; i++) {
        const t = time(trace.x[i]);
        const y = trace.y[i];
        if (t >= start && t <= end && y !== null && y !== undefined && Number.isFinite(+y)) values.push(+y);
      }
    });
    return values;
  }

  function dataBounds(gd) {
    let low = Infinity;
    let high = -Infinity;
    (gd._fullData || []).forEach(trace => {
      if (trace.visible !== true || !trace.x || !trace.x.length) return;
      low = Math.min(low, time(trace.x[0]));
      high = Math.max(high, time(trace.x[trace.x.length - 1]));
    });
    return Number.isFinite(low) ? [low, high] : null;
  }

  // Fecha local en el formato de Plotly (mismo reloj que time()).
  const pad2 = n => String(n).padStart(2, "0");
  const iso = ms => {
    const d = new Date(ms);
    return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())} ` +
           `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`;
  };

  function fitY(gd) {
    const range = gd._fullLayout && gd._fullLayout.xaxis && gd._fullLayout.xaxis.range;
    if (!range) return;
    let start = time(range[0]);
    let end = time(range[1]);
    // Tope: al arrastrar, la vista no sale del período con datos.
    const bounds = dataBounds(gd);
    const update = {};
    if (bounds && end - start < bounds[1] - bounds[0]) {
      const shift = start < bounds[0] ? bounds[0] - start : end > bounds[1] ? bounds[1] - end : 0;
      if (shift) {
        start += shift;
        end += shift;
        update["xaxis.range"] = [iso(start), iso(end)];
      }
    }
    const y2 = gd.layout.yaxis2 && gd.layout.yaxis2.overlaying === "y";
    if (y2) {
      // Inflación/PIB: conserva la relación visual 10:1 y el cero compartido.
      const values = [0, ...visibleValues(gd, start, end, "y"),
                      ...visibleValues(gd, start, end, "y2").map(v => v * 10)];
      const low = Math.min(...values);
      const high = Math.max(...values);
      const pad = Math.max((high - low) * 0.08, 0.5);
      Object.assign(update, {"yaxis.range": [low - pad, high + pad],
                             "yaxis2.range": [(low - pad) / 10, (high + pad) / 10]});
      Plotly.relayout(gd, update);
      return;
    }
    const values = visibleValues(gd, start, end, "y");
    if (values.length) {
      const low = Math.min(...values);
      const high = Math.max(...values);
      const pad = Math.max((high - low) * 0.06, Math.abs(high) * 0.005, 0.05);
      update["yaxis.range"] = [low - pad, high + pad];
    }
    // Panel inferior independiente (pendiente TES): siempre con el cero visible.
    if (gd.layout.yaxis2) {
      const lower = [0, ...visibleValues(gd, start, end, "y2")];
      const low = Math.min(...lower);
      const high = Math.max(...lower);
      const pad = Math.max((high - low) * 0.1, 0.1);
      update["yaxis2.range"] = [low - pad, high + pad];
    }
    if (Object.keys(update).length) Plotly.relayout(gd, update);
  }

  function attach() {
    CHARTS.forEach(id => {
      const gd = document.querySelector(`#${id} .js-plotly-plot`);
      if (!gd || gd._fitYAttached || typeof gd.on !== "function") return;
      gd._fitYAttached = true;
      // El primer clic de un doble clic fija una fecha; el doble clic debe
      // volver a la vista inicial completa, así que también la libera.
      gd.on("plotly_doubleclick", () => {
        const release = document.getElementById("btn-soltar");
        if (release) setTimeout(() => release.click(), 60);
      });
      gd.on("plotly_relayout", event => {
        // Solo reacciona a cambios del eje de fechas; así no se llama a sí mismo.
        if (Object.keys(event || {}).some(key => key.startsWith("xaxis"))) fitY(gd);
      });
    });
  }

  setInterval(attach, 1000);
}());
