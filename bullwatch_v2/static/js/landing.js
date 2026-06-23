/* ══════════════════════════════════════════════════════════════
   FAZ 59 — Landing Page Interactions
   ══════════════════════════════════════════════════════════════ */
(function () {
  "use strict";

  // ── Navbar scroll effect ──────────────────────────────────
  var nav = document.querySelector(".ln-nav");
  if (nav) {
    window.addEventListener("scroll", function () {
      nav.classList.toggle("scrolled", window.scrollY > 40);
    }, { passive: true });
  }

  // ── Smooth scroll for anchor links ────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener("click", function (e) {
      var target = document.querySelector(a.getAttribute("href"));
      if (target) {
        e.preventDefault();
        var offset = 80;
        var top = target.getBoundingClientRect().top + window.pageYOffset - offset;
        window.scrollTo({ top: top, behavior: "smooth" });
      }
    });
  });

  // ── Fade-up on scroll (IntersectionObserver) ──────────────
  var fadeEls = document.querySelectorAll(".ln-fade-up");
  if (fadeEls.length > 0 && "IntersectionObserver" in window) {
    var obs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    fadeEls.forEach(function (el) { obs.observe(el); });
  } else {
    // Fallback: show all immediately
    fadeEls.forEach(function (el) { el.classList.add("visible"); });
  }

  // ── Counter animation for proof numbers ───────────────────
  var counters = document.querySelectorAll("[data-count]");
  if (counters.length > 0 && "IntersectionObserver" in window) {
    var counterObs = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            animateCounter(entry.target);
            counterObs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.5 }
    );
    counters.forEach(function (el) { counterObs.observe(el); });
  }

  function animateCounter(el) {
    var target = parseInt(el.getAttribute("data-count"), 10);
    var suffix = el.getAttribute("data-suffix") || "";
    var prefix = el.getAttribute("data-prefix") || "";
    var duration = 1600;
    var start = 0;
    var startTime = null;

    function step(timestamp) {
      if (!startTime) startTime = timestamp;
      var progress = Math.min((timestamp - startTime) / duration, 1);
      var eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      var current = Math.floor(eased * target);
      el.textContent = prefix + current.toLocaleString("tr-TR") + suffix;
      if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // ── Analytics tracking ────────────────────────────────────
  function trackEvent(name, data) {
    try {
      fetch("/api/analytics/track", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event: name,
          data: data || {},
          page: "landing",
          ts: new Date().toISOString()
        })
      }).catch(function () {});
    } catch (e) {}
  }

  trackEvent("landing_visit");

  // Track CTA clicks
  document.querySelectorAll('a[href="/register"]').forEach(function (a) {
    a.addEventListener("click", function () {
      trackEvent("landing_register_click", { section: closestSection(a) });
    });
  });
  document.querySelectorAll('a[href="/login"]').forEach(function (a) {
    a.addEventListener("click", function () {
      trackEvent("landing_login_click");
    });
  });
  document.querySelectorAll('a[href="/discover"]').forEach(function (a) {
    a.addEventListener("click", function () {
      trackEvent("landing_demo_click");
    });
  });

  function closestSection(el) {
    var sec = el.closest("section");
    return sec ? (sec.id || "unknown") : "unknown";
  }

  // ── Mobile menu toggle ────────────────────────────────────
  var toggle = document.querySelector(".ln-menu-toggle");
  var navCenter = document.querySelector(".ln-nav-center");
  if (toggle && navCenter) {
    toggle.addEventListener("click", function () {
      var open = navCenter.style.display === "flex";
      navCenter.style.display = open ? "" : "flex";
      navCenter.style.position = open ? "" : "fixed";
      navCenter.style.top = open ? "" : "56px";
      navCenter.style.left = open ? "" : "0";
      navCenter.style.right = open ? "" : "0";
      navCenter.style.flexDirection = open ? "" : "column";
      navCenter.style.padding = open ? "" : "20px";
      navCenter.style.background = open ? "" : "rgba(5,6,8,.98)";
      navCenter.style.borderBottom = open ? "" : "1px solid rgba(255,255,255,.06)";
      navCenter.style.gap = open ? "" : "16px";
      navCenter.style.zIndex = open ? "" : "999";
    });
  }
})();
