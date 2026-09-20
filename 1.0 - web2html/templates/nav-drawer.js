(function () {
  "use strict";

  var toggle = document.querySelector("[data-nav-toggle]");
  var panel = document.querySelector("[data-nav-panel], #nav-panel");
  if (!toggle || !panel) return;
  if (toggle.getAttribute("data-nav-drawer-bound") === "1") return;
  toggle.setAttribute("data-nav-drawer-bound", "1");

  var root = document.documentElement;
  var host = toggle.closest("header, .site-header") || document.body;

  function syncTop() {
    var box = host.getBoundingClientRect();
    root.style.setProperty("--nav-drawer-top", Math.round(box.bottom) + "px");
  }

  function setOpen(open) {
    root.classList.toggle("is-nav-open", open);
    document.body.classList.toggle("nav-open", open);
    host.classList.toggle("is-nav-open", open);
    toggle.setAttribute("aria-expanded", open ? "true" : "false");
    toggle.setAttribute("aria-label", open ? "Close menu" : "Open menu");
    panel.setAttribute("aria-hidden", open ? "false" : "true");
    if (open) syncTop();
  }

  toggle.addEventListener("click", function (event) {
    event.preventDefault();
    event.stopPropagation();
    setOpen(!root.classList.contains("is-nav-open"));
  });

  panel.querySelectorAll("a").forEach(function (link) {
    link.addEventListener("click", function () {
      setOpen(false);
    });
  });

  document.addEventListener("click", function (event) {
    if (!root.classList.contains("is-nav-open")) return;
    if (host.contains(event.target)) return;
    setOpen(false);
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") setOpen(false);
  });

  window.addEventListener("resize", function () {
    var style = window.getComputedStyle(toggle);
    if (style.display === "none" || style.visibility === "hidden") {
      setOpen(false);
      return;
    }
    if (root.classList.contains("is-nav-open")) syncTop();
  });

  setOpen(false);
})();
