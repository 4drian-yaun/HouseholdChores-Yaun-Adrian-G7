(() => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 0. Unified Theme & Color Palette Picker
  const themeMeta = document.getElementById("themeColorMeta");
  const modeButtons = document.querySelectorAll("[data-theme-choice]");

  const applyTheme = (theme, persist) => {
    document.documentElement.setAttribute("data-theme", theme);
    if (persist) {
      localStorage.setItem("hc-theme", theme);
    }
    if (themeMeta) {
      themeMeta.setAttribute("content", theme === "dark" ? "#1c1e21" : "#fcfcfd");
    }
    modeButtons.forEach((btn) => {
      const active = btn.getAttribute("data-theme-choice") === theme;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", String(active));
    });
  };

  const initialTheme = document.documentElement.getAttribute("data-theme") || "light";
  applyTheme(initialTheme, false);

  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    if (!localStorage.getItem("hc-theme")) {
      applyTheme(e.matches ? "dark" : "light", false);
    }
  });

  modeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const choice = btn.getAttribute("data-theme-choice");
      if (choice === "light" || choice === "dark") {
        applyTheme(choice, true);
      }
    });
  });

  const palettePicker = document.getElementById("palettePicker");
  const paletteToggle = document.getElementById("paletteToggle");
  const palettePopover = document.getElementById("palettePopover");
  const paletteSwatches = document.querySelectorAll("[data-palette-choice]");

  const applyPalette = (palette, persist) => {
    const valid = [
      "blue", "indigo", "sky", "teal", "emerald",
      "violet", "pink", "rose", "amber", "slate",
      "ocean", "sunset", "forest", "lavender", "coffee", "nord",
      "cherry", "mint", "cyber", "royal", "coral", "aurora",
      "berry", "citrus", "midnight",
    ];
    const next = valid.includes(palette) ? palette : "blue";
    document.documentElement.setAttribute("data-palette", next);
    if (persist) {
      localStorage.setItem("hc-palette", next);
    }
    paletteSwatches.forEach((btn) => {
      const active = btn.getAttribute("data-palette-choice") === next;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", String(active));
    });
  };

  applyPalette(document.documentElement.getAttribute("data-palette") || localStorage.getItem("hc-palette") || "blue", false);

  if (palettePicker && paletteToggle && palettePopover) {
    const setPopoverOpen = (open) => {
      palettePopover.hidden = !open;
      paletteToggle.setAttribute("aria-expanded", String(open));
    };

    paletteToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      setPopoverOpen(palettePopover.hidden);
    });

    paletteSwatches.forEach((btn) => {
      btn.addEventListener("click", () => {
        applyPalette(btn.getAttribute("data-palette-choice"), true);
        if (!prefersReducedMotion) {
          const mark = document.querySelector(".brand-mark");
          if (mark) {
            mark.classList.remove("is-pulsing");
            void mark.offsetWidth;
            mark.classList.add("is-pulsing");
          }
          spawnGlobalSparks(btn);
        }
      });
    });

    document.addEventListener("click", (e) => {
      if (!palettePopover.hidden && !palettePicker.contains(e.target)) {
        setPopoverOpen(false);
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && !palettePopover.hidden) {
        setPopoverOpen(false);
        paletteToggle.focus();
      }
    });
  }

  // 1. Sticky topbar shadow on scroll
  const topbar = document.getElementById("topbar");
  if (topbar) {
    const onScroll = () => {
      topbar.classList.toggle("scrolled", window.scrollY > 8);
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // 2. Mobile navigation toggle (with tap-outside, Escape, and resize close)
  const navToggle = document.getElementById("navToggle");
  const mainNav = document.getElementById("mainNav");
  if (navToggle && mainNav) {
    const setNavOpen = (open) => {
      navToggle.setAttribute("aria-expanded", String(open));
      navToggle.classList.toggle("open", open);
      mainNav.classList.toggle("open", open);
    };

    navToggle.addEventListener("click", (e) => {
      e.stopPropagation();
      const expanded = navToggle.getAttribute("aria-expanded") === "true";
      setNavOpen(!expanded);
    });

    document.addEventListener("click", (e) => {
      if (mainNav.classList.contains("open") && topbar && !topbar.contains(e.target)) {
        setNavOpen(false);
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && mainNav.classList.contains("open")) {
        setNavOpen(false);
        navToggle.focus();
      }
    });

    mainNav.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", () => setNavOpen(false));
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 860 && mainNav.classList.contains("open")) {
        setNavOpen(false);
      }
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

  // Helper: micro particle spark burst (reused across all pages)
  const spawnGlobalSparks = (el, count = 7) => {
    if (prefersReducedMotion || !el) return;
    const rect = el.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const colors = ["var(--teal)", "var(--teal-2)", "var(--ok)", "var(--sun)"];
    for (let i = 0; i < count; i += 1) {
      const spark = document.createElement("span");
      spark.className = "spark-dot";
      const angle = (Math.PI * 2 * i) / count + (Math.random() * 0.4 - 0.2);
      const dist = 18 + Math.random() * 18;
      spark.style.left = `${cx - 3}px`;
      spark.style.top = `${cy - 3}px`;
      spark.style.setProperty("--tx", `${Math.cos(angle) * dist}px`);
      spark.style.setProperty("--ty", `${Math.sin(angle) * dist}px`);
      spark.style.setProperty("--spark-c", colors[i % colors.length]);
      document.body.appendChild(spark);
      window.setTimeout(() => spark.remove(), 540);
    }
  };

  // Helper: interactive stagger dot grid (hero + page headers + auth screens)
  const initKineticGrid = (gridEl, hostEl, colsDesktop, rowsDesktop, colsMobile, rowsMobile) => {
    if (!gridEl || !hostEl || prefersReducedMotion) return;
    const isCompact = window.innerWidth < 640;
    const cols = isCompact ? colsMobile : colsDesktop;
    const rows = isCompact ? rowsMobile : rowsDesktop;
    gridEl.style.setProperty("--grid-cols", String(cols));
    gridEl.style.setProperty("--grid-rows", String(rows));

    const dots = [];
    for (let i = 0; i < cols * rows; i += 1) {
      const dot = document.createElement("span");
      dot.className = "kinetic-dot";
      gridEl.appendChild(dot);
      dots.push(dot);
    }

    const triggerRipple = (originIdx) => {
      const ox = originIdx % cols;
      const oy = Math.floor(originIdx / cols);
      dots.forEach((dot, idx) => {
        const dist = Math.hypot((idx % cols) - ox, Math.floor(idx / cols) - oy);
        if (dist > 4.2) return;
        const delay = Math.round(dist * 46);
        window.setTimeout(() => {
          dot.classList.add("is-wave");
          window.setTimeout(() => dot.classList.remove("is-wave"), 360);
        }, delay);
      });
    };

    let lastRipple = 0;
    hostEl.addEventListener("pointermove", (e) => {
      const now = performance.now();
      if (now - lastRipple < 170) return;
      lastRipple = now;
      const r = gridEl.getBoundingClientRect();
      if (!r.width || !r.height) return;
      const col = Math.max(0, Math.min(cols - 1, Math.floor(((e.clientX - r.left) / r.width) * cols)));
      const row = Math.max(0, Math.min(rows - 1, Math.floor(((e.clientY - r.top) / r.height) * rows)));
      triggerRipple(row * cols + col);
    });

    window.setTimeout(() => triggerRipple(Math.floor((rows * cols) / 2)), 260);
  };

  // 4. Copy username callout button
  document.querySelectorAll(".copy-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const value = btn.getAttribute("data-copy");
      if (!value) return;
      try {
        await navigator.clipboard.writeText(value);
        spawnGlobalSparks(btn, 6);
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

  // 5. Interactive Dashboard Chore Filters + Coordinated Live Search
  const filterGroup = document.querySelector("[data-chore-filter]");
  const choreSearchInput = document.querySelector('[data-table-search=".chore-row"]');
  if (filterGroup || choreSearchInput) {
    const buttons = filterGroup ? filterGroup.querySelectorAll(".pill") : [];
    const rows = document.querySelectorAll(".chore-row");
    const emptyMsg = document.querySelector(".filter-empty");
    let activeMode = "all";
    let searchQuery = "";

    const applyChoreFilters = (animate) => {
      let visibleCount = 0;
      rows.forEach((row) => {
        const isMine = row.getAttribute("data-mine") === "true";
        const status = row.getAttribute("data-status");
        let show = true;
        if (activeMode === "mine") show = isMine;
        else if (activeMode === "pending") show = status === "pending";
        else if (activeMode === "completed") show = status === "completed";

        if (show && searchQuery) {
          const text = (row.textContent || "").toLowerCase();
          show = text.includes(searchQuery);
        }

        row.hidden = !show;
        if (show) {
          visibleCount += 1;
          if (animate && !prefersReducedMotion) {
            row.classList.remove("row-pop");
            void row.offsetWidth;
            row.classList.add("row-pop");
          }
        }
      });

      if (emptyMsg) {
        emptyMsg.hidden = visibleCount > 0;
      }
    };

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        activeMode = btn.getAttribute("data-filter") || "all";
        buttons.forEach((b) => b.classList.toggle("active", b === btn));
        applyChoreFilters(true);
      });
    });

    if (choreSearchInput) {
      choreSearchInput.addEventListener("input", () => {
        searchQuery = choreSearchInput.value.trim().toLowerCase();
        applyChoreFilters(false);
      });
    }
  }

  // 6. Auto-submit history filter selects
  document.querySelectorAll("form[data-auto-submit] select").forEach((select) => {
    select.addEventListener("change", () => {
      if (select.form.requestSubmit) {
        select.form.requestSubmit();
      } else {
        select.form.submit();
      }
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

  // 10. Enhanced Landing Page Interactive Preview Board (Checkboxes + Simulate Next Monday + Sparks)
  const demoChart = document.querySelector("[data-demo-chart]");
  if (demoChart) {
    const demoMembers = [
      { name: "Ana", initial: "A", cls: "" },
      { name: "Marco", initial: "M", cls: "b" },
      { name: "Jules", initial: "J", cls: "c" },
      { name: "Kira", initial: "K", cls: "d" },
    ];
    const items = Array.from(demoChart.querySelectorAll("[data-demo-item]"));
    const bar = demoChart.querySelector("[data-demo-bar]");
    const countEl = demoChart.querySelector("[data-demo-count]");
    const weekLabel = demoChart.querySelector("[data-demo-week-label]");
    const footEl = demoChart.querySelector("[data-demo-foot]");
    const rotateBtn = demoChart.querySelector("[data-demo-rotate]");
    let demoWeek = 1;

    const spawnSparks = (el) => spawnGlobalSparks(el, 7);

    const syncDemo = () => {
      const total = items.length;
      let done = 0;
      items.forEach((li) => {
        if (li.classList.contains("done")) done += 1;
      });
      if (bar) bar.style.width = `${Math.round((done / total) * 100)}%`;
      if (countEl) countEl.textContent = `${done}/${total}`;
      const allDone = done === total;
      demoChart.classList.toggle("is-celebrating", allDone);
      if (footEl) {
        footEl.innerHTML = allDone
          ? "All chores complete! Press <strong>Next Mon</strong> to rotate everyone forward."
          : "Click checkboxes or press <strong>Next Mon</strong> to preview rotation";
      }
    };

    items.forEach((li) => {
      const btn = li.querySelector("button.state");
      const toggle = () => {
        const isDone = li.classList.toggle("done");
        if (btn) btn.classList.toggle("done", isDone);
        if (isDone) spawnSparks(btn || li);
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

    if (rotateBtn) {
      rotateBtn.addEventListener("click", () => {
        demoWeek += 1;
        const offset = (demoWeek - 1) % demoMembers.length;
        if (weekLabel) {
          weekLabel.textContent = demoWeek === 1 ? "Week 1 · This week" : `Week ${demoWeek} · Rotated`;
        }
        if (!prefersReducedMotion) {
          rotateBtn.classList.remove("is-spinning");
          void rotateBtn.offsetWidth;
          rotateBtn.classList.add("is-spinning");
        }
        items.forEach((li, idx) => {
          const cur = demoMembers[(idx + offset) % demoMembers.length];
          const nxt = demoMembers[(idx + offset + 1) % demoMembers.length];
          const avatar = li.querySelector("[data-demo-avatar]");
          const sub = li.querySelector("[data-demo-sub]");
          const btn = li.querySelector("button.state");
          if (avatar) {
            avatar.textContent = cur.initial;
            avatar.className = `who${cur.cls ? " " + cur.cls : ""}`;
          }
          if (sub) {
            sub.textContent = `${cur.name} · Next Mon: ${nxt.name}`;
          }
          li.classList.remove("done");
          if (btn) btn.classList.remove("done");
          if (!prefersReducedMotion) {
            li.classList.remove("is-rotating");
            li.style.animationDelay = `${idx * 55}ms`;
            void li.offsetWidth;
            li.classList.add("is-rotating");
          }
        });
        syncDemo();
      });
    }

    // Subtle 3D tilt on desktop pointer move
    if (!prefersReducedMotion && window.matchMedia("(hover: hover)").matches) {
      demoChart.addEventListener("pointermove", (e) => {
        const r = demoChart.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        demoChart.style.transform = `perspective(900px) rotateX(${(-py * 5).toFixed(2)}deg) rotateY(${(px * 5).toFixed(2)}deg)`;
      });
      demoChart.addEventListener("pointerleave", () => {
        demoChart.style.transform = "";
      });
    }
  }

  // 10b. Global Anime.js-Inspired Kinetic Effects (Active Across ALL Pages)
  // 1) Global scroll progress bar (GPU scaleX at native refresh rate, zero lag)
  const progressBar = document.querySelector("[data-scroll-progress]");
  if (progressBar) {
    let progressTicking = false;
    const syncScrollProgress = () => {
      progressTicking = false;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      const ratio = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
      progressBar.style.transform = `scaleX(${ratio})`;
    };
    const onScrollProgress = () => {
      if (!progressTicking) {
        progressTicking = true;
        requestAnimationFrame(syncScrollProgress);
      }
    };
    window.addEventListener("scroll", onScrollProgress, { passive: true });
    window.addEventListener("resize", onScrollProgress, { passive: true });
    syncScrollProgress();
  }

  // 2) Staggered word-by-word spring headline (landing + page headers)
  const headlineTargets = document.querySelectorAll("[data-stagger-words], .page-head h1");
  if (!prefersReducedMotion) {
    headlineTargets.forEach((h1) => {
      // Only split pure text headings (preserve inline badges/tags if any)
      if (h1.children.length > 0) return;
      const words = h1.textContent.trim().split(/\s+/);
      if (!words.length || !words[0]) return;
      h1.textContent = "";
      words.forEach((word, i) => {
        const span = document.createElement("span");
        span.className = "kinetic-word";
        span.style.setProperty("--wd", `${Math.min(i * 65, 320)}ms`);
        span.textContent = word;
        h1.appendChild(span);
        if (i < words.length - 1) h1.appendChild(document.createTextNode(" "));
      });
    });
  }

  // 3) Interactive stagger dot grid (hero on landing, subtle ambient grid on page-head & auth pages)
  const heroGrid = document.querySelector("[data-kinetic-grid]");
  if (heroGrid) {
    initKineticGrid(heroGrid, heroGrid.closest(".landing-hero"), 11, 6, 6, 5);
  } else if (!prefersReducedMotion) {
    const pageHead = document.querySelector(".page-head");
    const authBox = document.querySelector(".auth.auth-centered");
    if (pageHead) {
      const g = document.createElement("div");
      g.className = "kinetic-grid kinetic-grid-subtle";
      g.setAttribute("aria-hidden", "true");
      pageHead.prepend(g);
      initKineticGrid(g, pageHead, 12, 3, 6, 3);
    } else if (authBox) {
      const g = document.createElement("div");
      g.className = "kinetic-grid kinetic-grid-subtle";
      g.setAttribute("aria-hidden", "true");
      authBox.prepend(g);
      initKineticGrid(g, authBox, 10, 6, 6, 5);
    }
  }

  // 4) Global subtle magnetic spring pull on primary CTAs & action buttons
  if (!prefersReducedMotion && window.matchMedia("(hover: hover)").matches) {
    const magTargets = document.querySelectorAll(
      "[data-magnetic], .head-actions .btn-link, .btn-done, .landing-cta .btn-link"
    );
    magTargets.forEach((btn) => {
      btn.addEventListener("pointermove", (e) => {
        const r = btn.getBoundingClientRect();
        const dx = ((e.clientX - r.left) / r.width - 0.5) * 7;
        const dy = ((e.clientY - r.top) / r.height - 0.5) * 5;
        btn.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px)`;
      });
      btn.addEventListener("pointerleave", () => {
        btn.style.transform = "";
      });
    });
  }

  // 6) Global staggered row/item cascade on tables, member bars & info lists
  if (!prefersReducedMotion) {
    document.querySelectorAll("tbody, .member-bars, .info-list, .quick-links").forEach((group) => {
      Array.from(group.children).forEach((child, idx) => {
        if (idx > 12) return;
        child.classList.add("kinetic-row");
        child.style.setProperty("--rd", `${idx * 38}ms`);
      });
    });
  }

  // 7) Celebratory spark burst on clicking real "Mark done ✓" buttons
  document.querySelectorAll(".btn-done").forEach((btn) => {
    btn.addEventListener("click", () => {
      spawnGlobalSparks(btn, 8);
    });
  });

  // 7b) Sliding spring indicator pill in desktop topbar navigation
  const topNav = document.getElementById("mainNav");
  if (topNav) {
    const navLinks = Array.from(topNav.querySelectorAll("a:not(.nav-cta):not(.nav-login)"));
    if (navLinks.length) {
      const glider = document.createElement("span");
      glider.className = "nav-glider";
      glider.setAttribute("aria-hidden", "true");
      topNav.prepend(glider);
      topNav.classList.add("has-glider");

      const moveNavGlider = (target) => {
        const drawerBp = topNav.querySelector(".nav-group-primary") ? 900 : 860;
        if (!target || window.innerWidth <= drawerBp) {
          glider.style.opacity = "0";
          return;
        }
        glider.style.width = `${target.offsetWidth}px`;
        glider.style.height = `${target.offsetHeight}px`;
        glider.style.transform = `translate(${target.offsetLeft}px, ${target.offsetTop}px)`;
        glider.style.opacity = "1";
      };

      const syncToActiveNav = () => {
        const active = topNav.querySelector("a.active:not(.nav-cta):not(.nav-login)");
        moveNavGlider(active);
      };

      navLinks.forEach((link) => {
        link.addEventListener("mouseenter", () => moveNavGlider(link));
        link.addEventListener("focus", () => moveNavGlider(link));
      });
      topNav.addEventListener("mouseleave", syncToActiveNav);
      window.addEventListener("resize", syncToActiveNav, { passive: true });
      window.addEventListener("load", syncToActiveNav);
      // Keep glider synced whenever scroll-spy updates .active
      const navClassObs = new MutationObserver(syncToActiveNav);
      navLinks.forEach((l) => navClassObs.observe(l, { attributes: true, attributeFilter: ["class"] }));
      requestAnimationFrame(syncToActiveNav);
    }
  }

  // 7c) Sliding spring indicator inside segmented filter pills (Dashboard & Analytics)
  document.querySelectorAll(".filter-pills").forEach((group) => {
    const pills = Array.from(group.querySelectorAll(".pill"));
    if (pills.length < 2) return;
    const pillGlider = document.createElement("span");
    pillGlider.className = "pill-glider";
    pillGlider.setAttribute("aria-hidden", "true");
    group.prepend(pillGlider);
    group.classList.add("has-pill-glider");

    const movePillGlider = (target) => {
      if (!target) return;
      pillGlider.style.width = `${target.offsetWidth}px`;
      pillGlider.style.height = `${target.offsetHeight}px`;
      pillGlider.style.transform = `translate(${target.offsetLeft}px, ${target.offsetTop}px)`;
      pillGlider.style.opacity = "1";
    };

    const syncActivePill = () => {
      const active = group.querySelector(".pill.active") || pills[0];
      movePillGlider(active);
    };

    pills.forEach((p) => {
      p.addEventListener("click", () => requestAnimationFrame(syncActivePill));
    });
    window.addEventListener("resize", syncActivePill, { passive: true });
    window.addEventListener("load", syncActivePill);
    requestAnimationFrame(syncActivePill);
  });

  // 8) Staggered card reveals for grids
  const staggerContainers = document.querySelectorAll("[data-stagger-reveal]");
  staggerContainers.forEach((container) => {
    Array.from(container.children).forEach((child, idx) => {
      child.style.setProperty("--sd", `${idx * 85}ms`);
    });
    if (prefersReducedMotion || !("IntersectionObserver" in window)) {
      container.classList.add("in-view");
    } else {
      const obs = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              container.classList.add("in-view");
              obs.unobserve(container);
            }
          });
        },
        { threshold: 0.14 }
      );
      obs.observe(container);
    }
  });

  // 9) Landing-only interactive widgets (Scroll-Spy Nav, Timeline Playground & Audience Strip)
  const landingRoot = document.querySelector("[data-landing-enhanced]");
  if (landingRoot) {
    // Smooth animated scroll + Scroll-spy for top navigation section links
    const navSectionLinks = Array.from(document.querySelectorAll("[data-nav-section]"));
    const trackedSections = ["how-it-works", "interactive-timeline", "features"]
      .map((id) => document.getElementById(id))
      .filter(Boolean);

    if (navSectionLinks.length && trackedSections.length) {
      let scrollAnimId = null;
      let isProgrammaticScroll = false;

      const cancelScrollAnim = () => {
        if (scrollAnimId !== null) {
          cancelAnimationFrame(scrollAnimId);
          scrollAnimId = null;
        }
        isProgrammaticScroll = false;
      };

      // Never fight manual user scroll
      window.addEventListener("wheel", cancelScrollAnim, { passive: true });
      window.addEventListener("touchstart", cancelScrollAnim, { passive: true });

      const setActiveNav = (key) => {
        navSectionLinks.forEach((link) => {
          link.classList.toggle("active", link.getAttribute("data-nav-section") === key);
        });
      };

      const playSectionArrival = (sectionEl) => {
        if (!sectionEl) return;
        sectionEl.classList.remove("section-arrived");
        void sectionEl.offsetWidth;
        sectionEl.classList.add("section-arrived");

        // Gentle continuous accent glow pulse across cards (zero jump or opacity dip)
        const cards = sectionEl.querySelectorAll(".step-card, .feature-card, .playground-card");
        cards.forEach((card, idx) => {
          card.classList.remove("card-arrive-pop");
          card.style.setProperty("--ad", `${idx * 75}ms`);
          void card.offsetWidth;
          card.classList.add("card-arrive-pop");
        });
      };

      const smoothScrollTo = (targetY, targetSection) => {
        cancelScrollAnim();
        const startY = window.scrollY;
        const distance = targetY - startY;
        if (Math.abs(distance) < 2) {
          if (targetSection) playSectionArrival(targetSection);
          return;
        }
        // Longer, velvety glide duration so motion feels fluid and never abrupt
        const duration = Math.min(1250, Math.max(780, Math.abs(distance) * 0.7));
        const startTime = performance.now();
        let arrivalFired = false;
        isProgrammaticScroll = true;

        // Smooth quintic S-curve: gentle take-off + silky, prolonged landing
        const easeInOutQuint = (t) =>
          t < 0.5 ? 16 * t * t * t * t * t : 1 - Math.pow(-2 * t + 2, 5) / 2;

        const step = (now) => {
          const elapsed = now - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const eased = easeInOutQuint(progress);
          window.scrollTo({ top: startY + distance * eased, behavior: "instant" });

          // Fire subtle arrival glow seamlessly near the end of deceleration
          if (!arrivalFired && progress >= 0.8 && targetSection) {
            arrivalFired = true;
            playSectionArrival(targetSection);
          }

          if (progress < 1) {
            scrollAnimId = requestAnimationFrame(step);
          } else {
            scrollAnimId = null;
            isProgrammaticScroll = false;
          }
        };

        scrollAnimId = requestAnimationFrame(step);
      };

      const syncActiveSection = () => {
        if (isProgrammaticScroll) return;
        const y = window.scrollY + 140;
        let currentKey = "top";
        trackedSections.forEach((sec) => {
          if (y >= sec.offsetTop) {
            currentKey = sec.id;
          }
        });
        setActiveNav(currentKey);
      };

      navSectionLinks.forEach((link) => {
        link.addEventListener("click", (e) => {
          const href = link.getAttribute("href") || "";
          if (!href.startsWith("#")) return;
          e.preventDefault();

          const key = link.getAttribute("data-nav-section");
          setActiveNav(key);

          if (key === "top") {
            if (history.replaceState) history.replaceState(null, "", window.location.pathname);
            smoothScrollTo(0, document.querySelector(".landing-hero"));
            return;
          }

          const targetSection = document.getElementById(key);
          if (!targetSection) return;

          if (history.replaceState) history.replaceState(null, "", `#${key}`);
          const headerOffset = (topbar ? topbar.offsetHeight : 64) + 20;
          const targetY = Math.max(0, targetSection.getBoundingClientRect().top + window.scrollY - headerOffset);

          smoothScrollTo(targetY, targetSection);
        });
      });

      window.addEventListener("scroll", syncActiveSection, { passive: true });
      syncActiveSection();
    }

    // Interactive Timeline Rotation Playground
    const playground = document.querySelector("[data-rotation-playground]");
    if (playground) {
      const pgMembers = [
        { name: "Ana", initial: "A", cls: "" },
        { name: "Marco", initial: "M", cls: "avatar-c1" },
        { name: "Jules", initial: "J", cls: "avatar-c2" },
        { name: "Kira", initial: "K", cls: "avatar-c3" },
      ];
      const range = playground.querySelector("[data-pg-range]");
      const badge = playground.querySelector("[data-pg-week-badge]");
      const weeksCount = playground.querySelector("[data-pg-weeks-count]");
      const chipsWrap = playground.querySelector("[data-pg-chips]");
      const lanes = Array.from(playground.querySelectorAll("[data-pg-lane]"));
      const playBtn = playground.querySelector("[data-pg-play]");
      const playLabel = playground.querySelector("[data-pg-play-label]");
      const iconPlay = playground.querySelector(".pg-icon-play");
      const iconPause = playground.querySelector(".pg-icon-pause");
      let playTimer = null;

      const renderWeek = (weekNum) => {
        const w = Math.max(1, Math.min(8, Number(weekNum) || 1));
        const offset = (w - 1) % pgMembers.length;
        if (range) range.value = String(w);
        if (badge) {
          badge.textContent = `Week ${w}`;
          if (!prefersReducedMotion) {
            badge.classList.add("pop");
            window.setTimeout(() => badge.classList.remove("pop"), 220);
          }
        }
        if (weeksCount) {
          weeksCount.textContent = w === 1 ? "1 week" : `${w} weeks`;
        }
        lanes.forEach((lane, idx) => {
          const m = pgMembers[(idx + offset) % pgMembers.length];
          const av = lane.querySelector("[data-pg-avatar]");
          const nameEl = lane.querySelector("[data-pg-member]");
          if (av) {
            av.textContent = m.initial;
            av.className = `avatar avatar-sm${m.cls ? " " + m.cls : ""}`;
          }
          if (nameEl) nameEl.textContent = m.name;
          if (!prefersReducedMotion) {
            lane.classList.remove("is-shifting");
            lane.style.animationDelay = `${idx * 45}ms`;
            void lane.offsetWidth;
            lane.classList.add("is-shifting");
          }
        });
        if (chipsWrap) {
          chipsWrap.innerHTML = pgMembers
            .map((m) => `<span class="fairness-chip">${m.name} <b>${w}</b></span>`)
            .join("");
        }
      };

      if (range) {
        range.addEventListener("input", () => renderWeek(range.value));
      }

      if (playBtn) {
        const setPlaying = (playing) => {
          playBtn.setAttribute("aria-pressed", String(playing));
          if (playLabel) playLabel.textContent = playing ? "Pause" : "Auto-play";
          if (iconPlay) iconPlay.hidden = playing;
          if (iconPause) iconPause.hidden = !playing;
          window.clearInterval(playTimer);
          if (playing) {
            playTimer = window.setInterval(() => {
              const cur = Number(range?.value || 1);
              renderWeek(cur >= 8 ? 1 : cur + 1);
            }, 1300);
          }
        };

        playBtn.addEventListener("click", () => {
          const isPlaying = playBtn.getAttribute("aria-pressed") === "true";
          setPlaying(!isPlaying);
        });
      }
    }

    // Interactive Audience Strip
    const audiencePicker = document.querySelector("[data-audience-picker]");
    if (audiencePicker) {
      const tags = audiencePicker.querySelectorAll(".audience-tag");
      const output = audiencePicker.querySelector("[data-audience-output]");
      tags.forEach((tag) => {
        tag.addEventListener("click", () => {
          tags.forEach((t) => t.classList.toggle("active", t === tag));
          const tip = tag.getAttribute("data-audience-tip");
          if (output && tip) {
            output.textContent = tip;
            if (!prefersReducedMotion) {
              output.style.animation = "none";
              void output.offsetWidth;
              output.style.animation = "";
            }
          }
        });
      });
    }
  }

  // 11. Analytics: interactive Donut <-> Legend hover highlight + dynamic center readout
  const donutGroup = document.querySelector("[data-donut-group]");
  if (donutGroup) {
    const segs = donutGroup.querySelectorAll("[data-seg]");
    const cards = donutGroup.querySelectorAll("[data-legend]");
    const centerPct = donutGroup.querySelector("[data-donut-pct]");
    const centerLabel = donutGroup.querySelector("[data-donut-label]");
    const defaultPct = donutGroup.getAttribute("data-default-pct") || "";
    const defaultLabel = donutGroup.getAttribute("data-default-label") || "Completed";

    const highlight = (key) => {
      segs.forEach((s) => {
        const match = s.getAttribute("data-seg") === key;
        s.classList.toggle("is-highlighted", match);
        s.classList.toggle("is-dimmed", Boolean(key) && !match);
      });
      cards.forEach((c) => {
        c.classList.toggle("is-highlighted", c.getAttribute("data-legend") === key);
      });
      if (centerPct && centerLabel) {
        if (key === "done") {
          centerPct.textContent = donutGroup.getAttribute("data-done-pct") || defaultPct;
          centerLabel.textContent = donutGroup.getAttribute("data-done-label") || defaultLabel;
        } else if (key === "missed") {
          centerPct.textContent = donutGroup.getAttribute("data-missed-pct") || defaultPct;
          centerLabel.textContent = donutGroup.getAttribute("data-missed-label") || "Missed";
        } else {
          centerPct.textContent = defaultPct;
          centerLabel.textContent = defaultLabel;
        }
      }
    };

    const clear = () => highlight(null);

    cards.forEach((card) => {
      const key = card.getAttribute("data-legend");
      card.addEventListener("mouseenter", () => highlight(key));
      card.addEventListener("focus", () => highlight(key));
      card.addEventListener("mouseleave", clear);
      card.addEventListener("blur", clear);
    });
    segs.forEach((seg) => {
      const key = seg.getAttribute("data-seg");
      seg.addEventListener("mouseenter", () => highlight(key));
      seg.addEventListener("mouseleave", clear);
    });
  }

  // 11b. Analytics: Interactive SVG Area Chart hover crosshair + Area/Bars & Chore toggles
  const areaChart = document.querySelector("[data-area-chart]");
  if (areaChart) {
    const svg = areaChart.querySelector("svg");
    const crosshair = areaChart.querySelector("[data-area-crosshair]");
    const tooltip = areaChart.querySelector("[data-area-tooltip]");
    const ttTitle = areaChart.querySelector("[data-at-title]");
    const ttDetail = areaChart.querySelector("[data-at-detail]");
    const nodes = areaChart.querySelectorAll("[data-area-node]");

    const showNode = (node) => {
      nodes.forEach((n) => n.classList.toggle("is-active", n === node));
      const x = parseFloat(node.getAttribute("data-x") || "0");
      const y = parseFloat(node.getAttribute("data-y") || "0");
      if (crosshair) {
        crosshair.setAttribute("x1", String(x));
        crosshair.setAttribute("x2", String(x));
        crosshair.classList.add("is-visible");
      }
      if (tooltip && svg) {
        const rect = svg.getBoundingClientRect();
        const leftPx = (x / 520) * rect.width;
        const topPx = (y / 170) * rect.height;
        tooltip.style.left = `${Math.max(66, Math.min(rect.width - 66, leftPx))}px`;
        tooltip.style.top = `${Math.max(40, topPx)}px`;
        if (ttTitle) ttTitle.textContent = node.getAttribute("data-label") || "";
        if (ttDetail) ttDetail.textContent = node.getAttribute("data-detail") || "";
        tooltip.hidden = false;
      }
    };

    const hideNode = () => {
      nodes.forEach((n) => n.classList.remove("is-active"));
      if (crosshair) crosshair.classList.remove("is-visible");
      if (tooltip) tooltip.hidden = true;
    };

    nodes.forEach((node) => {
      node.addEventListener("mouseenter", () => showNode(node));
      node.addEventListener("focus", () => showNode(node));
      node.addEventListener("click", () => showNode(node));
    });
    areaChart.addEventListener("mouseleave", hideNode);
  }

  // Trend chart mode toggle (Area vs Bars)
  const trendModeGroup = document.querySelector("[data-trend-mode]");
  if (trendModeGroup) {
    const modeBtns = trendModeGroup.querySelectorAll(".pill");
    const panels = document.querySelectorAll("[data-trend-panel]");
    modeBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-mode");
        modeBtns.forEach((b) => b.classList.toggle("active", b === btn));
        panels.forEach((p) => {
          p.hidden = p.getAttribute("data-trend-panel") !== mode;
        });
      });
    });
  }

  // Chore reliability view toggle (Most missed vs All chores)
  const choreViewGroup = document.querySelector("[data-chore-view]");
  if (choreViewGroup) {
    const viewBtns = choreViewGroup.querySelectorAll(".pill");
    const panels = document.querySelectorAll("[data-chore-panel]");
    viewBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const view = btn.getAttribute("data-view");
        viewBtns.forEach((b) => b.classList.toggle("active", b === btn));
        panels.forEach((p) => {
          p.hidden = p.getAttribute("data-chore-panel") !== view;
        });
      });
    });
  }

  // 12. Analytics: Member leaderboard sort toggle (Most done vs Best rate)
  const sortGroup = document.querySelector("[data-member-sort]");
  const memberList = document.querySelector("[data-member-list]");
  if (sortGroup && memberList) {
    const sortButtons = sortGroup.querySelectorAll(".pill");
    sortButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const mode = btn.getAttribute("data-sort");
        sortButtons.forEach((b) => b.classList.toggle("active", b === btn));

        const items = Array.from(memberList.querySelectorAll(".member-bar-item"));
        items.sort((a, b) => {
          const valA = parseInt(a.getAttribute(`data-${mode}`), 10) || 0;
          const valB = parseInt(b.getAttribute(`data-${mode}`), 10) || 0;
          if (valB !== valA) return valB - valA;
          const nameA = a.querySelector(".member-bar-name")?.textContent || "";
          const nameB = b.querySelector(".member-bar-name")?.textContent || "";
          return nameA.localeCompare(nameB);
        });

        items.forEach((item, idx) => {
          const rank = item.querySelector(".rank-badge");
          if (rank) {
            rank.textContent = `#${idx + 1}`;
            rank.className = `rank-badge rank-${idx + 1}`;
          }
          const fill = item.querySelector(".bar-fill");
          if (fill) {
            const w = item.getAttribute(`data-width-${mode}`) || "0";
            fill.style.width = `${w}%`;
            fill.classList.toggle("is-zero", parseInt(w, 10) === 0);
          }
          memberList.appendChild(item);
        });
      });
    });
  }

  // 13. Signup & Change-Password live password checklist
  const pwRulesBox = document.querySelector("[data-pw-rules]");
  if (pwRulesBox) {
    const pw1Id = pwRulesBox.getAttribute("data-pw1-id") || "id_password1";
    const pw2Id = pwRulesBox.getAttribute("data-pw2-id") || "id_password2";
    const pw1 = document.getElementById(pw1Id);
    const pw2 = document.getElementById(pw2Id);
    const userInput = document.getElementById("id_username");
    const emailInput = document.getElementById("id_email");

    const setRule = (name, ok) => {
      const el = pwRulesBox.querySelector(`[data-rule="${name}"]`);
      if (el) el.classList.toggle("met", Boolean(ok));
    };

    const checkPassword = () => {
      const v1 = pw1 ? pw1.value : "";
      const v2 = pw2 ? pw2.value : "";
      const uname = (userInput ? userInput.value : "").trim().toLowerCase();
      const emailLocal = ((emailInput ? emailInput.value : "").split("@")[0] || "").trim().toLowerCase();

      setRule("length", v1.length >= 8);
      setRule("not-numeric", v1.length > 0 && !/^\d+$/.test(v1));
      const lower = v1.toLowerCase();
      const tooSimilar =
        (uname.length >= 3 && lower.includes(uname)) ||
        (emailLocal.length >= 3 && lower.includes(emailLocal));
      setRule("personal", v1.length >= 8 && !tooSimilar);
      setRule("match", v1.length > 0 && v1 === v2);
    };

    [pw1, pw2, userInput, emailInput].forEach((input) => {
      if (input) input.addEventListener("input", checkPassword);
    });
  }

  // 14. Show / Hide password eye toggle
  const eyeOpenSvg =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>';
  const eyeOffSvg =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" y1="2" x2="22" y2="22"/></svg>';

  document.querySelectorAll("[data-pw-toggle]").forEach((btn) => {
    const input = btn.parentElement?.querySelector("input");
    if (!input) return;
    btn.innerHTML = eyeOpenSvg;
    btn.addEventListener("click", () => {
      const showing = input.type === "text";
      input.type = showing ? "password" : "text";
      btn.innerHTML = showing ? eyeOpenSvg : eyeOffSvg;
      btn.setAttribute("aria-label", showing ? "Show password" : "Hide password");
    });
  });

  // 15. Phone Number Input Mask (Principle 07: Use Input Masks In Fields)
  const formatPhoneValue = (raw) => {
    const trimmed = raw.trim();
    if (!trimmed) return "";
    const startsPlus = trimmed.startsWith("+");
    const digits = trimmed.replace(/\D/g, "");
    if (!digits) return startsPlus ? "+" : "";

    // International PH format: (+63) 917 123 4567
    if (startsPlus || digits.startsWith("63")) {
      const cc = digits.slice(0, 2);
      const rest = digits.slice(2, 12);
      if (!rest) return `(+${cc})`;
      const p1 = rest.slice(0, 3);
      const p2 = rest.slice(3, 6);
      const p3 = rest.slice(6, 10);
      return `(+${cc}) ${[p1, p2, p3].filter(Boolean).join(" ")}`;
    }

    // Standard local format: 0917 123 4567
    const local = digits.slice(0, 11);
    const p1 = local.slice(0, 4);
    const p2 = local.slice(4, 7);
    const p3 = local.slice(7, 11);
    return [p1, p2, p3].filter(Boolean).join(" ");
  };

  document.querySelectorAll("[data-phone-mask]").forEach((input) => {
    if (input.value) {
      input.value = formatPhoneValue(input.value);
    }
    input.addEventListener("input", () => {
      const formatted = formatPhoneValue(input.value);
      if (input.value !== formatted) {
        input.value = formatted;
      }
    });
  });

  // 16. Live Table Search + Coordinated Filters for Members & Chores tables
  const memberFilterGroup = document.querySelector("[data-member-filter]");
  const memberSearchInput = document.querySelector('[data-table-search=".member-row"]');
  if (memberFilterGroup || memberSearchInput) {
    const buttons = memberFilterGroup ? memberFilterGroup.querySelectorAll(".pill") : [];
    const rows = document.querySelectorAll(".member-row");
    const emptyMsg = document.querySelector(".filter-empty");
    let activeMode = "all";
    let searchQuery = "";

    const applyMemberFilters = () => {
      let visible = 0;
      rows.forEach((row) => {
        const role = row.getAttribute("data-role");
        const linked = row.getAttribute("data-linked") === "true";
        let show = true;
        if (activeMode === "admin") show = role === "admin";
        else if (activeMode === "linked") show = linked;
        else if (activeMode === "unlinked") show = !linked;
        if (show && searchQuery) {
          show = (row.textContent || "").toLowerCase().includes(searchQuery);
        }
        row.hidden = !show;
        if (show) visible += 1;
      });
      if (emptyMsg) emptyMsg.hidden = visible > 0;
    };

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        activeMode = btn.getAttribute("data-filter") || "all";
        buttons.forEach((b) => b.classList.toggle("active", b === btn));
        applyMemberFilters();
      });
    });
    if (memberSearchInput) {
      memberSearchInput.addEventListener("input", () => {
        searchQuery = memberSearchInput.value.trim().toLowerCase();
        applyMemberFilters();
      });
    }
  }

  const choreListFilterGroup = document.querySelector("[data-chore-list-filter]");
  const choreListSearchInput = document.querySelector('[data-table-search=".chore-list-row"]');
  if (choreListFilterGroup || choreListSearchInput) {
    const buttons = choreListFilterGroup ? choreListFilterGroup.querySelectorAll(".pill") : [];
    const rows = document.querySelectorAll(".chore-list-row");
    const emptyMsg = document.querySelector(".filter-empty");
    let activeMode = "all";
    let searchQuery = "";

    const applyChoreListFilters = () => {
      let visible = 0;
      rows.forEach((row) => {
        const status = row.getAttribute("data-status");
        let show = true;
        if (activeMode === "pending") show = status === "pending";
        else if (activeMode === "completed") show = status === "completed";
        if (show && searchQuery) {
          show = (row.textContent || "").toLowerCase().includes(searchQuery);
        }
        row.hidden = !show;
        if (show) visible += 1;
      });
      if (emptyMsg) emptyMsg.hidden = visible > 0;
    };

    buttons.forEach((btn) => {
      btn.addEventListener("click", () => {
        activeMode = btn.getAttribute("data-filter") || "all";
        buttons.forEach((b) => b.classList.toggle("active", b === btn));
        applyChoreListFilters();
      });
    });
    if (choreListSearchInput) {
      choreListSearchInput.addEventListener("input", () => {
        searchQuery = choreListSearchInput.value.trim().toLowerCase();
        applyChoreListFilters();
      });
    }
  }

  document.querySelectorAll("[data-table-search]").forEach((input) => {
    const selector = input.getAttribute("data-table-search");
    if (!selector || selector === ".chore-row" || selector === ".member-row" || selector === ".chore-list-row") return;
    const card = input.closest(".card") || document;
    const rows = card.querySelectorAll(selector);
    const emptyMsg = card.querySelector(".filter-empty");

    input.addEventListener("input", () => {
      const q = input.value.trim().toLowerCase();
      let visible = 0;
      rows.forEach((row) => {
        const show = !q || (row.textContent || "").toLowerCase().includes(q);
        row.hidden = !show;
        if (show) visible += 1;
      });
      if (emptyMsg) {
        emptyMsg.hidden = visible > 0;
      }
    });
  });

  // 17. Searchable + Scrollable Select Combobox (Principle 11)
  const chevronSvg =
    '<svg class="combo-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="6 9 12 15 18 9"/></svg>';

  document.querySelectorAll("select[data-searchable-select]").forEach((select) => {
    const options = Array.from(select.options).map((opt) => ({
      value: opt.value,
      label: opt.textContent.trim(),
    }));
    const placeholder = select.getAttribute("data-search-placeholder") || "Type to search or scroll...";

    const wrap = document.createElement("div");
    wrap.className = "combo-wrap";

    const inputWrap = document.createElement("div");
    inputWrap.className = "combo-input-wrap";

    const input = document.createElement("input");
    input.type = "text";
    input.className = "combo-input";
    input.autocomplete = "off";
    input.placeholder = placeholder;
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-autocomplete", "list");
    input.setAttribute("aria-expanded", "false");

    const selectedOpt = options.find((o) => o.value === select.value) || options[0];
    if (selectedOpt) input.value = selectedOpt.label;

    inputWrap.appendChild(input);
    inputWrap.insertAdjacentHTML("beforeend", chevronSvg);

    const menu = document.createElement("ul");
    menu.className = "combo-menu";
    menu.setAttribute("role", "listbox");
    menu.hidden = true;

    wrap.appendChild(inputWrap);
    wrap.appendChild(menu);

    select.classList.add("sr-only-select");
    select.tabIndex = -1;
    select.parentNode.insertBefore(wrap, select.nextSibling);

    let filtered = options.slice();
    let activeIdx = -1;

    const getCurrentLabel = () => {
      const match = options.find((o) => o.value === select.value);
      return match ? match.label : "";
    };

    const renderOptions = (query) => {
      const q = (query || "").trim().toLowerCase();
      filtered = q ? options.filter((o) => o.label.toLowerCase().includes(q)) : options.slice();
      activeIdx = -1;
      menu.innerHTML = "";

      if (!filtered.length) {
        const empty = document.createElement("li");
        empty.className = "combo-empty";
        empty.textContent = "No matching options";
        menu.appendChild(empty);
        return;
      }

      filtered.forEach((opt, idx) => {
        const li = document.createElement("li");
        li.className = "combo-option";
        if (opt.value === select.value) li.classList.add("is-selected");
        li.textContent = opt.label;
        li.setAttribute("role", "option");
        li.setAttribute("aria-selected", String(opt.value === select.value));
        li.addEventListener("mousedown", (e) => {
          e.preventDefault();
          chooseOption(opt);
        });
        li.addEventListener("mouseenter", () => setActive(idx));
        menu.appendChild(li);
      });
    };

    const setActive = (idx) => {
      const items = menu.querySelectorAll(".combo-option");
      if (!items.length) return;
      activeIdx = (idx + items.length) % items.length;
      items.forEach((el, i) => {
        el.classList.toggle("is-active", i === activeIdx);
      });
      items[activeIdx].scrollIntoView({ block: "nearest" });
    };

    const openMenu = (showAll) => {
      renderOptions(showAll ? "" : input.value);
      menu.hidden = false;
      wrap.classList.add("is-open");
      input.setAttribute("aria-expanded", "true");
    };

    const closeMenu = (restore) => {
      menu.hidden = true;
      wrap.classList.remove("is-open");
      input.setAttribute("aria-expanded", "false");
      if (restore) input.value = getCurrentLabel();
    };

    const chooseOption = (opt) => {
      const changed = select.value !== opt.value;
      select.value = opt.value;
      input.value = opt.label;
      closeMenu(false);
      if (changed) {
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
    };

    input.addEventListener("focus", () => {
      input.select();
      openMenu(true);
    });

    input.addEventListener("click", () => {
      if (menu.hidden) openMenu(true);
    });

    input.addEventListener("input", () => {
      openMenu(false);
    });

    input.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        if (menu.hidden) openMenu(true);
        setActive(activeIdx + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        if (menu.hidden) openMenu(true);
        setActive(activeIdx - 1);
      } else if (e.key === "Enter") {
        if (!menu.hidden && filtered.length) {
          e.preventDefault();
          chooseOption(filtered[activeIdx >= 0 ? activeIdx : 0]);
        }
      } else if (e.key === "Escape") {
        closeMenu(true);
        input.blur();
      }
    });

    document.addEventListener("click", (e) => {
      if (!wrap.contains(e.target) && !menu.hidden) {
        closeMenu(true);
      }
    });
  });

  // 18. Skeleton Loading Screen on Navigation (Principle 12)
  const pageSkeleton = document.getElementById("pageSkeleton");
  const pageContent = document.getElementById("pageContent");
  let skelTimer = null;

  const scheduleSkeleton = () => {
    if (!pageSkeleton || !pageContent) return;
    window.clearTimeout(skelTimer);
    skelTimer = window.setTimeout(() => {
      pageContent.hidden = true;
      pageSkeleton.hidden = false;
    }, 120);
  };

  const resetSkeleton = () => {
    window.clearTimeout(skelTimer);
    if (pageSkeleton) pageSkeleton.hidden = true;
    if (pageContent) pageContent.hidden = false;
  };

  window.addEventListener("pageshow", resetSkeleton);

  document.addEventListener("click", (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) {
      return;
    }
    const link = e.target.closest("a[href]");
    if (!link) return;
    const href = link.getAttribute("href");
    if (!href || href.startsWith("#") || href.startsWith("javascript:") || link.target === "_blank" || link.hasAttribute("download")) {
      return;
    }
    if (link.origin === window.location.origin) {
      scheduleSkeleton();
    }
  });

  document.querySelectorAll('form[method="get"]').forEach((form) => {
    form.addEventListener("submit", scheduleSkeleton);
  });
})();
