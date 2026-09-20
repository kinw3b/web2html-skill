(() => {
  // Names a captured element by what it IS (its component archetype), not by the
  // text that happens to sit inside it. A short hint is appended only when it
  // helps tell two same-archetype takes apart.

  const STOP_WORDS = new Set([
    "the", "a", "an", "and", "or", "of", "for", "to", "your", "our", "with",
    "is", "are", "it", "this", "that", "you", "we", "in", "on", "at", "by",
  ]);

  function text(element) {
    const value = element?.getAttribute?.("aria-label")
      || element?.getAttribute?.("alt")
      || element?.innerText
      || element?.textContent
      || "";
    return String(value).replace(/\s+/g, " ").trim();
  }

  function titleCase(value) {
    return value.replace(/\S+/g, (word) => word[0].toUpperCase() + word.slice(1));
  }

  // 1-3 meaningful words, from the element's own heading when it has one.
  function hintFor(element, archetype) {
    const heading = element.querySelector?.("h1,h2,h3,h4,h5,h6,summary,figcaption,strong,b");
    const source = text(heading) || text(element);
    if (!source) return "";
    const words = source
      .split(/[^\p{L}\p{N}$€£%+.-]+/u)
      .filter((word) => word && !STOP_WORDS.has(word.toLowerCase()))
      .slice(0, 3);
    if (!words.length) return "";
    const hint = titleCase(words.join(" ")).slice(0, 28).trim();
    return hint.toLowerCase() === archetype.toLowerCase() ? "" : hint;
  }

  function hasStat(element) {
    const nodes = [element, ...element.querySelectorAll("*")].slice(0, 60);
    return nodes.some((node) => {
      if (node.children.length) return false;
      const value = text(node);
      if (!/^[+\-]?[\d.,]+\s*(x|%|k|m|b|\+|hrs?|days?|min)?$/i.test(value)) return false;
      return parseFloat(getComputedStyle(node).fontSize) >= 32;
    });
  }

  function hasPrice(element) {
    return /(^|\s)[$€£]\s?\d/.test(text(element));
  }

  function media(element) {
    const images = element.querySelectorAll("img,svg,picture,video,canvas").length;
    const words = text(element).split(/\s+/).filter(Boolean).length;
    return { images, words };
  }

  function repeatedChildren(element) {
    const children = [...element.children].filter((child) => {
      const rect = child.getBoundingClientRect();
      return rect.width > 2 && rect.height > 2;
    });
    if (children.length < 3) return 0;
    const shapes = new Set(children.map((child) => `${child.tagName}:${child.children.length}`));
    return shapes.size <= Math.ceil(children.length / 2) ? children.length : 0;
  }

  function archetypeOf(element, context = {}) {
    const tag = element.tagName.toLowerCase();
    const role = (element.getAttribute("role") || "").toLowerCase();
    const kind = String(context.kind || "").toLowerCase();
    const hay = `${element.className || ""} ${element.getAttribute("data-framer-name") || ""} ${element.id || ""}`.toLowerCase();
    const body = text(element);
    const { images, words } = media(element);

    if (kind === "navbar" || tag === "nav" || role === "navigation") return "Navbar";
    if (kind === "dropdown" || role === "menu" || /dropdown|megamenu|flyout/.test(hay)) return "Dropdown Menu";
    if (tag === "header") return "Header";
    if (tag === "footer" || /footer/.test(hay)) return "Footer";
    if (tag === "form" || element.querySelector("input,textarea,select")) return "Form";
    if (tag === "details" || element.querySelector("details")
      || (element.hasAttribute("aria-expanded") && words > 12)
      || /accordion|faq/.test(hay)) return "Accordion Item";
    if (tag === "table" || role === "table") return "Table";

    if (images && !words) {
      const rect = element.getBoundingClientRect();
      if (/logo|brand|wordmark/.test(hay)) return "Logo";
      return rect.width <= 48 && rect.height <= 48 ? "Icon" : "Image";
    }
    if ((tag === "a" || tag === "button" || role === "button") && words <= 6) {
      return tag === "a" && !/btn|button|cta/.test(hay) && !/inline-flex|flex/.test(getComputedStyle(element).display)
        ? "Link"
        : "Button";
    }
    if (/badge|pill|chip|tag/.test(hay) && words <= 6) return "Badge";

    if (/rating|review|star|trustpilot|testimonial|quote/.test(`${hay} ${body}`.toLowerCase())
      || tag === "blockquote") {
      return words <= 14 ? "Rating Badge" : "Testimonial Card";
    }
    if (hasPrice(element) && words > 4) return "Pricing Card";
    if (hasStat(element)) return "Stat Card";

    const grid = repeatedChildren(element);
    if (grid) {
      const display = getComputedStyle(element).display;
      if (tag === "ul" || tag === "ol") return "List";
      return /grid/.test(display) ? "Card Grid" : "Item Group";
    }

    if (element.querySelector("h1,h2,h3,h4,h5,h6") && words > 3) {
      if (element.querySelector("h1") && element.querySelector("a,button")) return "Hero";
      return images ? "Feature Card" : "Text Card";
    }
    if (/^(h1|h2|h3|h4|h5|h6)$/.test(tag)) return "Heading";
    if (tag === "p" || (words > 3 && !images)) return "Text Block";
    if (tag === "section" || tag === "article") return "Section";
    return "Card";
  }

  function componentName(element, context = {}) {
    if (!(element instanceof Element)) return String(context.kind || "Capture");
    let archetype;
    try {
      archetype = archetypeOf(element, context);
    } catch {
      archetype = "Card";
    }
    if (context.mode === "hover") archetype = `${archetype} (Hover)`;
    const hint = hintFor(element, archetype);
    return hint ? `${archetype} · ${hint}` : archetype;
  }

  globalThis.PaperCaptureNaming = { componentName, archetypeOf };
})();
