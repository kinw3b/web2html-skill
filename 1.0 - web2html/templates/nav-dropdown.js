(function () {
  "use strict";

  var triggers = document.querySelectorAll("[data-nav-dropdown-trigger]");
  if (!triggers.length) return;

  function panelOf(trigger) {
    var owned = trigger.getAttribute("aria-controls");
    if (owned) {
      var byId = document.getElementById(owned);
      if (byId) return byId;
    }
    var host = trigger.closest("[data-nav-dropdown]");
    if (host) return host.querySelector("[data-nav-dropdown-panel]");
    var next = trigger.nextElementSibling;
    if (next && next.hasAttribute("data-nav-dropdown-panel")) return next;
    return null;
  }

  function setOpen(trigger, open) {
    var panel = panelOf(trigger);
    trigger.setAttribute("aria-expanded", open ? "true" : "false");
    if (panel) {
      panel.setAttribute("aria-hidden", open ? "false" : "true");
      panel.classList.toggle("is-open", open);
    }
  }

  function closeAll(except) {
    triggers.forEach(function (trigger) {
      if (trigger !== except) setOpen(trigger, false);
    });
  }

  triggers.forEach(function (trigger, index) {
    if (trigger.getAttribute("data-nav-dropdown-bound") === "1") return;
    trigger.setAttribute("data-nav-dropdown-bound", "1");
    var panel = panelOf(trigger);
    if (panel && !panel.id) panel.id = "nav-dropdown-" + index;
    if (panel) trigger.setAttribute("aria-controls", panel.id);
    trigger.setAttribute("aria-haspopup", "true");
    trigger.setAttribute("aria-expanded", "false");

    trigger.addEventListener("click", function (event) {
      if (window.matchMedia("(max-width: 768px)").matches) return;
      event.preventDefault();
      var open = trigger.getAttribute("aria-expanded") === "true";
      closeAll(trigger);
      setOpen(trigger, !open);
    });
    trigger.addEventListener("mouseenter", function () {
      if (window.matchMedia("(max-width: 768px)").matches) return;
      closeAll(trigger);
      setOpen(trigger, true);
    });
    if (panel) {
      panel.addEventListener("mouseenter", function () {
        if (window.matchMedia("(max-width: 768px)").matches) return;
        setOpen(trigger, true);
      });
    }
    var host = trigger.closest("[data-nav-dropdown], li, nav, header") || trigger.parentElement;
    if (host) {
      host.addEventListener("mouseleave", function () {
        if (!window.matchMedia("(max-width: 768px)").matches) setOpen(trigger, false);
      });
    }
  });

  document.addEventListener("click", function (event) {
    var hit = event.target.closest("[data-nav-dropdown], [data-nav-dropdown-trigger], [data-nav-dropdown-panel]");
    if (!hit) closeAll();
  });
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeAll();
  });
})();
