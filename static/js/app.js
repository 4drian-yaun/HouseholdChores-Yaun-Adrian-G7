(() => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 1. Sticky topbar shadow on scroll
  const topbar = document.getElementById("topbar");
  if (topbar) {
    const onScroll = () => {
      topbar.classList.toggle("scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // 2. Mobile navigation toggle
  const navToggle = document.getElementById("navToggle");
  const mainNav = document.getElementById("mainNav");
  if (navToggle && mainNav) {
    navToggle.addEventListener("click", () => {
      const expanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!expanded));
      navToggle.classList.toggle("open", !expanded);
      mainNav.classList.toggle("open", !expanded);
    });
  }

  // 3. Dismissible flash messages with smooth exit
  document.querySelectorAll(".messages li").forEach((item) => {
    const dismiss = () => {
      if (item.classList.contains("leaving")) return;
      item.classList.add("leaving");
      window.setTimeout(() => item.remove(), prefersReducedMotion ? 0 : 240);
    };

    const closeBtn = item.querySelector(".msg-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", dismiss);
    }

    if (item.classList.contains("success") || item.classList.contains("info")) {
      let timer = window.setTimeout(dismiss, 6500);
      item.addEventListener("mouseenter", () => window.clearTimeout(timer));
      item.addEventListener("mouseleave", () => {
        timer = window.setTimeout(dismiss, 2500);
      });
    }
  });

  // 4. Copy username callout button
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const value = btn.getAttribute("data-copy");
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        const prev = btn.textContent;
        btn.textContent = "Copied!";
        btn.classList.add("copied");
        window.setTimeout(() => {
          btn.textContent = prev;
          btn.classList.remove("copied");
        }, 1800);
      } catch {
        // Fallback: select callout text
        const callout = document.getElementById("usernameCallout");
        if (callout && window.getSelection) {
          const range = document.createRange();
          range.selectNodeContents(callout);
          const sel = window.getSelection();
          sel.removeAllRanges();
          sel.addRange(range);
        }
      }
    });
  });

  // 5. Interactive Dashboard Chore Filters
  const filterGroup = document.querySelector("[data-chore-filter]");
  if (filterGroup) {
    const buttons = filterGroup.querySelectorAll(".pill");
    const rows = document.querySelectorAll(".chore-row");
    const emptyMsg = document.querySelector(".filter-empty");

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-filter");
        buttons.forEach((b) => b.classList.toggle("active", b === btn));

        let visibleCount = 0;
        rows.forEach((row) => {
          const isMine = row.getAttribute("data-mine") === "true";
          const status = row.getAttribute("data-status");
          let show = true;
          if (mode === "mine") show = isMine;
          else if (mode === "pending") show = status === "pending";
          else if (mode === "completed") show = status === "completed";

          row.hidden = !show;
          if (show) {
            visibleCount += 1;
            if (!prefersReducedMotion) {
              row.classList.remove("row-pop");
              void row.offsetWidth;
              row.classList.add("row-pop");
            }
          }
        });

        if (emptyMsg) {
          emptyMsg.hidden = visibleCount > 0;
        }
      });
    });
  }

  // 6. Auto-submit history filter selects
  document.querySelectorAll("form[data-auto-submit] select").forEach((select) => {
    select.addEventListener("change", () => {
      select.form.submit();
    });
  });

  // 7. Smooth KPI count-up animation
  if (!prefersReducedMotion) {
    const counters = document.querySelectorAll("[data-count]");
    counters.forEach((el) => {
      const target = parseInt(el.getAttribute("data-count"), 10);
      if (Number.isNaN(target) || target <= 0) return;
      const duration = Math.min(700, 260 + target * 12);
      const start = performance.now();
      const tick = (now) => {
        const progress = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = String(Math.round(target * eased));
        if (progress < 1) {
          requestAnimationFrame(tick);
        } else {
          el.textContent = String(target);
        }
      };
      requestAnimationFrame(tick);
    });
  }

  // 8. Prevent accidental double-submits on POST forms
  document.querySelectorAll('form[method="post"]').forEach((form) => {
    form.addEventListener("submit", () => {
      const submitBtn = form.querySelector('button[type="submit"]');
      if (submitBtn && !submitBtn.disabled) {
        submitBtn.classList.add("is-submitting");
      }
    });
  });

  // 9. Landing page scroll-reveal animation
  const revealEls = document.querySelectorAll(".reveal");
  if (revealEls.length) {
    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      revealEls.forEach((el) => el.classList.add("visible"));
    } else {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add("visible");
              observer.unobserve(entry.target);
            }
          });
        },
        { threshold: 0.12, rootMargin: "0px 0px -30px 0px" }
      );
      revealEls.forEach((el) => observer.observe(el));
    }
  }

  // 10. Landing page interactive preview chore board
  const demoChart = document.querySelector("[data-demo-chart]");
  if (demoChart) {
    const items = demoChart.querySelectorAll("[data-demo-item]");
    const bar = demoChart.querySelector("[data-demo-bar]");
    const countEl = demoChart.querySelector("[data-demo-count]");

    const syncDemo = () => {
      const total = items.length;
      let done = 0;
      items.forEach((li) => {
        if (li.classList.contains("done")) done += 1;
      });
      if (bar) bar.style.width = `${Math.round((done / total) * 100)}%`;
      if (countEl) countEl.textContent = `${done}/${total}`;
    };

    items.forEach((li) => {
      const btn = li.querySelector("button.state");
      const toggle = () => {
        const isDone = li.classList.toggle("done");
        if (btn) btn.classList.toggle("done", isDone);
        syncDemo();
      };
      if (btn) {
        btn.addEventListener("click", (e) => {
          e.stopPropagation();
          toggle();
        });
      }
      li.addEventListener("click", toggle);
    });
  }
})();
