(function () {
  "use strict";

  var root =
    document.querySelector("[data-faq-root]") ||
    document.getElementById("faq-section") ||
    document.querySelector("[data-faq-item]");
  if (!root) return;
  if (root.getAttribute("data-faq-bound") === "1") return;
  root.setAttribute("data-faq-bound", "1");

  var items = root.querySelectorAll("[data-faq-item]");
  if (!items.length) return;

  function setOpen(item, open) {
    item.setAttribute("data-open", open ? "true" : "false");
    var button = item.querySelector("[data-action='toggle-faq']");
    var answer = item.querySelector("[data-faq-answer]");
    if (button) button.setAttribute("aria-expanded", open ? "true" : "false");
    if (answer) answer.setAttribute("aria-hidden", open ? "false" : "true");
  }

  items.forEach(function (item, index) {
    var button = item.querySelector("[data-action='toggle-faq']");
    var answer = item.querySelector("[data-faq-answer]");
    if (item.getAttribute("role") === "button" && button) {
      item.removeAttribute("role");
      item.removeAttribute("tabindex");
    }
    if (answer && !answer.id) answer.id = "faq-a-" + index;
    if (button) {
      if (!button.id) button.id = "faq-q-" + index;
      if (answer) button.setAttribute("aria-controls", answer.id);
      button.addEventListener("click", function (event) {
        event.preventDefault();
        var open = item.getAttribute("data-open") === "true";
        items.forEach(function (other) {
          if (other !== item) setOpen(other, false);
        });
        setOpen(item, !open);
      });
    }
    if (!item.hasAttribute("data-open")) {
      setOpen(item, false);
    } else {
      setOpen(item, item.getAttribute("data-open") === "true");
    }
  });
})();
