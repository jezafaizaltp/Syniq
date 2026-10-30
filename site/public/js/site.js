import { renderDiagram, parseDiagram } from "./diagram.js";

const toggle = document.querySelector(".nav-toggle");
const nav = document.getElementById("nav");
if (toggle && nav) {
  toggle.addEventListener("click", () => {
    const open = nav.classList.toggle("open");
    toggle.setAttribute("aria-expanded", String(open));
  });
  nav.addEventListener("click", (e) => {
    if (e.target.closest("a")) {
      nav.classList.remove("open");
      toggle.setAttribute("aria-expanded", "false");
    }
  });
}

// Example diagrams on the home page use the same drawing code as the tutor.
for (const holder of document.querySelectorAll("[data-diagram]")) {
  const source = holder.querySelector('script[type="application/json"]');
  const spec = source && parseDiagram(source.textContent);
  if (spec) holder.replaceChildren(renderDiagram(spec));
}
