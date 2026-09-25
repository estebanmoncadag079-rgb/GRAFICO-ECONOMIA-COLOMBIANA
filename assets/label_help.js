(function () {
  "use strict";
  const aliases = {
    "ICOLCAP empalmado · legado": "ICOLCAP empalmado",
    "Índice equiponderado · legado": "Índice equiponderado",
    "7 Magníficas · legado": "7 Magníficas",
    "IPC mensual · derecha": "Inflación mensual",
    "IPC anual · izquierda": "Inflación anual",
    "PIB interanual · izquierda": "PIB real",
    "TES 1 año (corto plazo)": "1A",
    "TES 5 años (medio plazo)": "5A",
    "TES 10 años (largo plazo)": "10A"
  };
  let popup;
  let active;

  function hide() {
    if (popup) popup.hidden = true;
    if (active) active.removeAttribute("aria-describedby");
    active = null;
  }

  function show(target) {
    const label = target.closest(".help-label, .legend .traces");
    if (!label) return;
    let explanation = label.dataset.help;
    if (!explanation) {
      const name = label.textContent.trim().replace(/\s+/g, " ");
      const key = aliases[name] || name;
      const source = Array.from(document.querySelectorAll(".help-label"))
        .find(item => item.textContent === key);
      explanation = source && source.dataset.help;
    }
    if (!explanation) return;
    hide();
    if (!popup) {
      popup = document.createElement("div");
      popup.id = "chart-label-help";
      popup.className = "chart-label-help";
      popup.setAttribute("role", "tooltip");
      document.body.appendChild(popup);
    }
    popup.textContent = explanation;
    popup.hidden = false;
    active = label;
    label.setAttribute("aria-describedby", popup.id);
    const rect = label.getBoundingClientRect();
    const box = popup.getBoundingClientRect();
    popup.style.left = Math.max(12, Math.min(rect.left, window.innerWidth - box.width - 12)) + "px";
    const below = rect.bottom + 8;
    popup.style.top = Math.max(12, below + box.height < window.innerHeight - 12
      ? below : rect.top - box.height - 8) + "px";
  }

  document.addEventListener("pointerover", event => show(event.target));
  document.addEventListener("focusin", event => show(event.target));
  document.addEventListener("pointerout", event => {
    if (active && !active.contains(event.relatedTarget) &&
        !(popup && popup.contains(event.relatedTarget))) hide();
  });
  document.addEventListener("focusout", hide);
  document.addEventListener("keydown", event => { if (event.key === "Escape") hide(); });
  document.addEventListener("click", event => {
    if (popup && popup.contains(event.target)) return;
    hide();
    show(event.target);
  });
  window.addEventListener("scroll", hide, true);
  window.addEventListener("resize", hide);
}());
