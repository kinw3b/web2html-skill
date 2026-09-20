/* website-to-html 2.10.11 — Emil in-view reveal (file://).
 * GSAP + ScrollTrigger only. No window scroll listeners.
 * When a parent group's top crosses 25% from the viewport bottom
 * (start: "top 75%"), its first children + siblings fade+rise in order.
 * Heads stagger text children. Grids stagger article/div/li items.
 * Mixed inners (copy + media) flatten wrappers, then stagger that list.
 * Pitfall #1: never hide with CSS; never class="reveal"; above-fold stays visible.
 * Pitfall #204: this pass is mandatory — do not skip from a 1.4 archive.
 */
(function () {
  "use strict";

  var DURATION = 0.95;
  var RISE = 28;
  var STAGGER = 0.08;
  var EASE = "expo.out";
  var FOLD = 0.92;
  var START = "top 75%";
  var MAX_FLAT = 4;

  var SKIP_CHILD_TAGS = {
    nav: 1,
    script: 1,
    style: 1,
    link: 1,
    meta: 1,
    noscript: 1,
    br: 1,
    hr: 1,
    source: 1,
    track: 1,
    canvas: 1,
    svg: 1,
    path: 1,
  };

  function hasQaOutlinesParam() {
    try {
      var search = location.search || "";
      if (search.indexOf("qa-outlines=") !== -1) return true;
      var hash = location.hash || "";
      if (hash.indexOf("qa-outlines=") !== -1) return true;
    } catch (err) {}
    return false;
  }

  function prefersReducedMotion() {
    return !!(
      window.matchMedia &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    );
  }

  function qaOutlinesActive() {
    var qa = document.documentElement.getAttribute("data-qa-outlines");
    return qa != null && qa !== "off";
  }

  function skipPrep() {
    return hasQaOutlinesParam() || qaOutlinesActive() || prefersReducedMotion();
  }

  function markReady() {
    document.documentElement.dataset.gsapReveal = "on";
    window.__gsapRevealReady = true;
  }

  function classStr(el) {
    if (!el) return "";
    var raw = el.className;
    if (raw && raw.baseVal != null) return String(raw.baseVal);
    return String(raw || "");
  }

  function hasToken(el, token) {
    return new RegExp(
      "(?:^|[\\s_/#.-])" + token + "(?:$|[\\s_/#.-])",
      "i"
    ).test(classStr(el) + " " + (el.id || ""));
  }

  function isDecorative(el) {
    if (!el || el.nodeType !== 1) return true;
    if (el.hasAttribute("data-decorative")) return true;
    if (hasToken(el, "decorative") || hasToken(el, "deco")) return true;
    if (hasToken(el, "paw") || hasToken(el, "watermark")) return true;
    if (hasToken(el, "qa-overlay")) return true;
    return false;
  }

  function isSiteChrome(el) {
    if (!el || !el.closest) return false;
    if (el.closest("nav")) return true;
    if (el.closest(".site-header, .site-nav, .navbar, #site-header, #site-nav")) {
      return true;
    }
    return false;
  }

  function isHero(el) {
    return !!(el && el.closest && el.closest(".hero, #hero, [id='hero']"));
  }

  function isHost(el) {
    var tag = (el.tagName || "").toLowerCase();
    return tag === "section" || tag === "footer";
  }

  function isItemLike(el) {
    var tag = (el.tagName || "").toLowerCase();
    if (tag === "article" || tag === "li") return true;
    return (
      hasToken(el, "card") ||
      hasToken(el, "plan") ||
      hasToken(el, "quote") ||
      hasToken(el, "feature") ||
      hasToken(el, "item") ||
      hasToken(el, "tile")
    );
  }

  function isCollection(el) {
    if (!el) return false;
    var items = elementKids(el).filter(isItemLike);
    return items.length >= 2;
  }

  function isHeadCluster(el) {
    if (!el) return false;
    var tag = (el.tagName || "").toLowerCase();
    if (tag === "header" && !isSiteChrome(el)) return true;
    if (hasToken(el, "head") && !hasToken(el, "header")) return true;
    if (hasToken(el, "intro")) return true;
    var kids = flattenPassthrough(elementKids(el), 1);
    var textish = kids.filter(isContent);
    return textish.length >= 2 && textish.length === kids.length;
  }

  function isMixedCluster(el) {
    if (!el) return false;
    if (isHost(el)) return false;
    if (hasToken(el, "section") && hasToken(el, "inner")) return false;
    var kids = elementKids(el);
    if (kids.length < 2) return false;
    var media = kids.some(hasMediaDesc);
    var copy = kids.some(hasCopyDesc);
    return media && copy;
  }

  function hasMediaDesc(el) {
    if (isMedia(el) && !isDecorative(el)) return true;
    if (hasToken(el, "media") || hasToken(el, "visual") || hasToken(el, "photo")) {
      return true;
    }
    var imgs = el.querySelectorAll ? el.querySelectorAll("img, picture, video") : [];
    var i;
    for (i = 0; i < imgs.length; i++) {
      if (!isDecorative(imgs[i])) return true;
    }
    return false;
  }

  function hasCopyDesc(el) {
    if (isContent(el) || isHeadCluster(el)) return true;
    if (hasToken(el, "copy") || hasToken(el, "intro")) return true;
    return !!(el.querySelector && el.querySelector("h1,h2,h3,p"));
  }

  function isPassthrough(el) {
    if (!el) return false;
    if (isItemLike(el) || isCollection(el) || isHeadCluster(el)) return false;
    return (
      hasToken(el, "stack") ||
      hasToken(el, "wrap") ||
      hasToken(el, "wrapper") ||
      hasToken(el, "inner") ||
      hasToken(el, "intro") ||
      hasToken(el, "copy") ||
      hasToken(el, "media") ||
      hasToken(el, "body")
    );
  }

  function isContent(el) {
    var tag = (el.tagName || "").toLowerCase();
    if (/^h[1-6]$/.test(tag)) return true;
    if (tag === "p" || tag === "blockquote" || tag === "small") return true;
    if (tag === "a" || tag === "button") return true;
    return false;
  }

  function isMedia(el) {
    var tag = (el.tagName || "").toLowerCase();
    return tag === "img" || tag === "picture" || tag === "video" || tag === "figure";
  }

  function elementKids(el) {
    if (!el || !el.children) return [];
    return Array.prototype.filter.call(el.children, function (n) {
      if (n.nodeType !== 1) return false;
      var tag = (n.tagName || "").toLowerCase();
      if (SKIP_CHILD_TAGS[tag]) return false;
      if (isSiteChrome(n)) return false;
      if (isDecorative(n)) return false;
      return true;
    });
  }

  function flattenPassthrough(kids, depth) {
    var out = [];
    if (depth > MAX_FLAT) return kids.slice();
    kids.forEach(function (k) {
      if (isPassthrough(k)) {
        flattenPassthrough(elementKids(k), depth + 1).forEach(function (x) {
          out.push(x);
        });
      } else {
        out.push(k);
      }
    });
    return out;
  }

  function flattenContent(el, depth) {
    var out = [];
    if (!el || depth > MAX_FLAT) return out;
    elementKids(el).forEach(function (k) {
      if (isCollection(k)) {
        elementKids(k).filter(isItemLike).forEach(function (item) {
          out.push(item);
        });
        return;
      }
      if (isPassthrough(k) || (isWrapper(k) && !isItemLike(k) && !isMedia(k))) {
        flattenContent(k, depth + 1).forEach(function (x) {
          out.push(x);
        });
        return;
      }
      out.push(k);
    });
    return out;
  }

  function isWrapper(el) {
    var tag = (el.tagName || "").toLowerCase();
    if (tag !== "div" && tag !== "span") return false;
    if (isItemLike(el) || isContent(el) || isMedia(el)) return false;
    return elementKids(el).length > 0;
  }

  function ancestorItem(el) {
    var p = el.parentElement;
    while (p && p !== document.body && p !== document.documentElement) {
      if (isItemLike(p)) return p;
      if (isHost(p)) break;
      p = p.parentElement;
    }
    return null;
  }

  function isGroupCandidate(el) {
    if (!el || isSiteChrome(el) || isHero(el) || isDecorative(el)) return false;
    if (ancestorItem(el)) return false;
    if (isItemLike(el) && el.parentElement && isCollection(el.parentElement)) {
      return false;
    }
    if (isHeadCluster(el) || isCollection(el) || isMixedCluster(el)) return true;
    if (isHost(el)) return true;
    return false;
  }

  function looseHeadsBefore(collection) {
    var heads = [];
    var n = collection.previousElementSibling;
    while (n) {
      if (isCollection(n) || isMixedCluster(n)) break;
      if (
        n.hasAttribute("data-reveal") &&
        (isHeadCluster(n) || isCollection(n) || isMixedCluster(n))
      ) {
        break;
      }
      if (isContent(n) || isHeadCluster(n)) {
        heads.unshift(n);
      } else if (isPassthrough(n) || isWrapper(n)) {
        flattenContent(n, 0)
          .filter(isContent)
          .reverse()
          .forEach(function (x) {
            heads.unshift(x);
          });
      } else {
        break;
      }
      n = n.previousElementSibling;
    }
    return uniqueNodes(heads);
  }

  function membersOf(parent) {
    if (isContent(parent) && elementKids(parent).length === 0) {
      return [parent];
    }
    if (isCollection(parent) && !isMixedCluster(parent)) {
      var kids = elementKids(parent);
      var items = kids.filter(isItemLike);
      var heads = [];
      kids.forEach(function (k) {
        if (items.indexOf(k) !== -1) return;
        if (isHeadCluster(k) || isContent(k)) {
          flattenContent(k, 0).forEach(function (x) {
            heads.push(x);
          });
        } else if (isPassthrough(k) || isWrapper(k)) {
          flattenContent(k, 0).forEach(function (x) {
            heads.push(x);
          });
        }
      });
      return uniqueNodes(heads.concat(items));
    }
    if (isHeadCluster(parent) || isMixedCluster(parent)) {
      return uniqueNodes(flattenContent(parent, 0));
    }
    var kids = elementKids(parent);
    if (kids.length === 1 && (isPassthrough(kids[0]) || isWrapper(kids[0]))) {
      kids = elementKids(kids[0]);
    }
    return uniqueNodes(kids);
  }

  function uniqueNodes(list) {
    var out = [];
    list.forEach(function (el) {
      if (!el || out.indexOf(el) !== -1) return;
      out.push(el);
    });
    return out;
  }

  function pickParents(targets) {
    var candidates = targets.filter(isGroupCandidate);
    var mixed = candidates.filter(isMixedCluster);
    var out = [];

    mixed.forEach(function (el) {
      if (membersOf(el).length) out.push(el);
    });

    candidates.forEach(function (el) {
      if (out.indexOf(el) !== -1) return;
      if (out.some(function (o) {
        return o.contains(el);
      })) {
        return;
      }
      if (isHeadCluster(el) || isCollection(el)) {
        if (membersOf(el).length) out.push(el);
      }
    });

    out.slice().forEach(function (el) {
      if (!isCollection(el)) return;
      looseHeadsBefore(el).forEach(function (h) {
        if (out.indexOf(h) !== -1) return;
        if (out.some(function (o) {
          return o.contains(h);
        })) {
          return;
        }
        out.push(h);
      });
    });

    candidates.forEach(function (el) {
      if (out.indexOf(el) !== -1) return;
      if (!isHost(el)) return;
      if (out.some(function (o) {
        return el.contains(o) || o.contains(el);
      })) {
        return;
      }
      if (membersOf(el).length) out.push(el);
    });

    if (out.length) return out;

    return fallbackLeafHosts(targets);
  }

  function isLeaf(el, pool) {
    var i;
    for (i = 0; i < pool.length; i++) {
      if (pool[i] !== el && el.contains(pool[i])) return false;
    }
    return true;
  }

  function hostOf(el) {
    return el.closest("section, footer") || el;
  }

  function fallbackLeafHosts(targets) {
    var leaves = targets.filter(function (el) {
      return isLeaf(el, targets) && !isSiteChrome(el) && !isHero(el);
    });
    var hosts = [];
    var seen = [];
    leaves.forEach(function (el) {
      var host = hostOf(el);
      var i = seen.indexOf(host);
      if (i === -1) {
        seen.push(host);
        hosts.push(host);
      }
    });
    return hosts;
  }

  function ident(el) {
    if (!el || el.nodeType !== 1) return "";
    var tag = el.tagName.toLowerCase();
    var out = tag;
    if (el.id) out += "#" + el.id;
    var cls = classStr(el).split(/\s+/).filter(Boolean);
    if (cls.length) out += "." + cls.slice(0, 3).join(".");
    return out;
  }

  function collectPlan(root) {
    var scope = root || document;
    var targets = Array.prototype.slice.call(
      scope.querySelectorAll("[data-reveal]")
    );
    return pickParents(targets).map(function (host) {
      return { host: host, members: membersOf(host) };
    }).filter(function (g) {
      return g.members.length > 0;
    });
  }

  function inspectPlan(root) {
    return collectPlan(root).map(function (g) {
      return {
        host: ident(g.host),
        members: g.members.map(ident),
      };
    });
  }

  window.__gsapRevealInspect = inspectPlan;
  window.__gsapRevealMembersOf = membersOf;
  window.__gsapRevealPickParents = pickParents;

  function boot() {
    document.documentElement.dataset.gsapReveal = "on";

    if (typeof gsap === "undefined" || typeof ScrollTrigger === "undefined") {
      markReady();
      return;
    }

    gsap.registerPlugin(ScrollTrigger);

    var ctx = gsap.context(function () {
      if (skipPrep()) {
        return;
      }

      var vh = window.innerHeight || 0;
      var groups = collectPlan();

      groups.forEach(function (g) {
        var members = g.members.filter(function (el) {
          return el.getBoundingClientRect().top >= vh * FOLD;
        });
        if (!members.length) return;
        members.forEach(function (el) {
          gsap.set(el, { opacity: 0, y: RISE, force3D: true });
        });
        ScrollTrigger.create({
          trigger: g.host,
          start: START,
          once: true,
          onEnter: function () {
            gsap.to(members, {
              opacity: 1,
              y: 0,
              duration: DURATION,
              stagger: STAGGER,
              ease: EASE,
              overwrite: "auto",
            });
          },
        });
      });
    });

    window.__gsapRevealContext = ctx;
    window.__gsapRevealTeardown = function () {
      if (ctx && ctx.revert) ctx.revert();
    };
    window.addEventListener("pagehide", function () {
      if (ctx && ctx.revert) ctx.revert();
    });
    markReady();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      requestAnimationFrame(boot);
    });
  } else {
    requestAnimationFrame(boot);
  }
})();
