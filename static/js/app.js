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
      themeMeta.setAttribute("content", theme === "dark" ? "#1c1e21" : "#fcfcfd");
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

  // 16. Live Table Search for Members & Chores tables (Principle 11)
  document.querySelectorAll("[data-table-search]").forEach((input) => {
    const selector = input.getAttribute("data-table-search");
    if (!selector || selector === ".chore-row") return;
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
