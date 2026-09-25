(function () {
  "use strict";
  const component = (type, children, props = {}) => ({
    namespace: "dash_html_components", type, props: { children, ...props }
  });
  const months = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"];
  const arrays = new WeakMap();
  function numbers(values) {
    if (Array.isArray(values) || ArrayBuffer.isView(values)) return values;
    if (!values || !values.bdata) return [];
    if (arrays.has(values)) return arrays.get(values);
    const types = { f8: Float64Array, f4: Float32Array, i4: Int32Array,
      i2: Int16Array, i1: Int8Array, u4: Uint32Array, u2: Uint16Array, u1: Uint8Array };
    const Type = types[values.dtype];
    if (!Type) return [];
    const bytes = Uint8Array.from(atob(values.bdata), c => c.charCodeAt(0));
    const decoded = new Type(bytes.buffer);
    arrays.set(values, decoded);
    return decoded;
  }
  function period(value, frequency) {
    const date = new Date(value);
    const month = date.getUTCMonth();
    const year = date.getUTCFullYear();
    if (frequency === "quarterly") return `T${Math.floor(month / 3) + 1} ${year}`;
    if (frequency === "monthly") return `${months[month]} ${year}`;
    return `${String(date.getUTCDate()).padStart(2, "0")} ${months[month]} ${year}`;
  }

  // Find only observations at or before the cursor's date. Never borrow a future quarter.
  function observation(trace, reference) {
    const values = numbers(trace.y);
    let low = 0;
    let high = trace.x.length;
    while (low < high) {
      const mid = Math.floor((low + high) / 2);
      if (Date.parse(trace.x[mid]) <= reference) low = mid + 1;
      else high = mid;
    }
    for (let i = low - 1; i >= 0; i--) {
      const value = values[i];
      if (value !== null && value !== undefined && Number.isFinite(Number(value))) {
        return { value: Number(value), date: trace.x[i] };
      }
    }
    return null;
  }

  window.dash_clientside = window.dash_clientside || {};
  window.dash_clientside.analysis = {
    readout: function (hover, figure) {
      const traces = (figure && figure.data || []).filter(trace =>
        trace.meta && trace.x && trace.x.length && trace.visible !== false && trace.visible !== "legendonly");
      if (!traces.length) return component("Div", "Sin series activas", { className: "readout-empty" });
      const context = window.dash_clientside.callback_context;
      const reset = (context.triggered || []).some(item => item.prop_id.endsWith(".figure"));
      const point = !reset && hover && hover.points && hover.points[0];
      let reference = point && Date.parse(point.x);
      if (!Number.isFinite(reference)) {
        reference = Math.max(...traces.map(trace => Date.parse(trace.x[trace.x.length - 1]) || 0));
      }
      const entries = traces.map(trace => {
        const item = observation(trace, reference);
        const meta = trace.meta;
        const color = trace.line && trace.line.color || trace.marker && trace.marker.color || "#64748b";
        const unit = meta.unit === "%" ? "%" : ` ${meta.unit}`;
        return component("Div", [
          component("Div", [
            component("Span", "", { className: "readout-swatch", style: {
              borderColor: color, borderTopStyle: trace.line && trace.line.dash ? "dashed" : "solid"
            }}),
            component("Span", meta.label)
          ], { className: "readout-label" }),
          component("Strong", item ? item.value.toLocaleString("es-CO", {
            minimumFractionDigits: 2, maximumFractionDigits: 2
          }) + unit : "Sin dato", { className: "readout-value" }),
          component("Span", (item ? period(item.date, meta.frequency) : "Sin observación previa") +
            (meta.axis ? ` · eje ${meta.axis}` : ""), { className: "readout-period" })
        ], { className: "readout-series" });
      });
      return [
        component("Div", `Referencia: ${period(reference, "daily")}`, { className: "readout-date" }),
        component("Div", entries, { className: "readout-values" })
      ];
    }
  };
}());
