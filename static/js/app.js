(() => {
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // 0. Light / Dark theme toggle
  const themeToggle = document.getElementById("themeToggle");
  const themeMeta = document.getElementById("themeColorMeta");
  const applyTheme = (theme, persist) => {
    document.documentElement.setAttribute("data-theme", theme);
    if (persist) {
      localStorage.setItem("hc-theme", theme);
    }
    if (themeMeta) {
      themeMeta.setAttribute("content", theme === "dark" ? "#132924" : "#1f6f5c");
    }
    if (themeToggle) {
      const isDark = theme === "dark";
      themeToggle.setAttribute("aria-pressed", String(isDark));
      themeToggle.setAttribute("aria-label", isDark ? "Switch to light mode" : "Switch to dark mode");
      themeToggle.setAttribute("title", isDark ? "Switch to light mode" : "Switch to dark mode");
    }
  };

  if (themeToggle) {
    const initial = document.documentElement.getAttribute("data-theme") || "light";
    applyTheme(initial, false);

    themeToggle.addEventListener("click", () => {
      const current = document.documentElement.getAttribute("data-theme") === "dark" ? "dark" : "light";
      applyTheme(current === "dark" ? "light" : "dark", true);
    });

    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
      if (!localStorage.getItem("hc-theme")) {
        applyTheme(e.matches ? "dark" : "light", false);
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

  // 11. Analytics: interactive Donut <-> Legend hover highlight
  const donutGroup = document.querySelector("[data-donut-group]");
  if (donutGroup) {
    const segs = donutGroup.querySelectorAll("[data-seg]");
    const cards = donutGroup.querySelectorAll("[data-legend]");

    const highlight = (key) => {
      segs.forEach((s) => {
        const match = s.getAttribute("data-seg") === key;
        s.classList.toggle("is-highlighted", match);
        s.classList.toggle("is-dimmed", Boolean(key) && !match);
      });
      cards.forEach((c) => {
        c.classList.toggle("is-highlighted", c.getAttribute("data-legend") === key);
      });
    };

    const clear = () => highlight(null);

    cards.forEach((card) => {
      const key = card.getAttribute("data-legend");
      card.addEventListener("mouseenter", () => highlight(key));
      card.addEventListener("mouseleave", clear);
    });
    segs.forEach((seg) => {
      const key = seg.getAttribute("data-seg");
      seg.addEventListener("mouseenter", () => highlight(key));
      seg.addEventListener("mouseleave", clear);
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
})();
