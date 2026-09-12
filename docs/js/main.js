(function () {
  "use strict";

  // ===== Theme =====
  function getTheme() {
    const s = localStorage.getItem("qstack-docs-theme");
    if (s) return s;
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  function setTheme(t) {
    document.documentElement.setAttribute("data-theme", t);
    localStorage.setItem("qstack-docs-theme", t);
    updateThemeBtn(t);
  }
  function updateThemeBtn(t) {
    const btn = document.getElementById("theme-toggle");
    if (!btn) return;
    btn.querySelector(".theme-icon").textContent = t === "dark" ? "☀️" : "🌙";
  }
  document.getElementById("theme-toggle").addEventListener("click", () => {
    setTheme(getTheme() === "dark" ? "light" : "dark");
  });
  setTheme(getTheme());

  // ===== Sidebar =====
  const sidebar = document.querySelector(".sidebar");
  const overlay = document.querySelector(".sidebar-overlay");
  const menuToggle = document.querySelector(".menu-toggle");
  function openSidebar() { sidebar.classList.add("open"); overlay.classList.add("active"); }
  function closeSidebar() { sidebar.classList.remove("open"); overlay.classList.remove("active"); }
  if (menuToggle) menuToggle.addEventListener("click", () => sidebar.classList.contains("open") ? closeSidebar() : openSidebar());
  if (overlay) overlay.addEventListener("click", closeSidebar);

  // Active sidebar link
  const curPath = window.location.pathname.replace(/\/?$/, "");
  document.querySelectorAll(".sidebar-link").forEach(a => {
    if (a.href.replace(/\/?$/, "").endsWith(curPath)) a.classList.add("active");
  });

  // ===== Table of Contents =====
  const tocList = document.querySelector(".toc-list");
  if (tocList) {
    const headings = document.querySelectorAll(".content h2[id], .content h3[id]");
    const tocObserver = new IntersectionObserver(entries => {
      entries.forEach(e => {
        if (e.isIntersecting) {
          document.querySelectorAll(".toc-list a").forEach(a => a.classList.remove("active"));
          const link = document.querySelector(`.toc-list a[href="#${e.target.id}"]`);
          if (link) link.classList.add("active");
        }
      });
    }, { rootMargin: "-80px 0px -60% 0px", threshold: 0 });
    headings.forEach(h => tocObserver.observe(h));
  }

  // ===== Search =====
  const searchInput = document.getElementById("search-input");
  const searchResults = document.getElementById("search-results");
  if (searchInput && searchResults) {
    let searchData = [];
    // Build index from pages
    fetch("./search-index.json")
      .then(r => r.json())
      .then(data => { searchData = data; })
      .catch(() => {
        // Fallback: index current page
        const content = document.querySelector(".content");
        if (content) {
          const text = content.innerText;
          const paragraphs = content.querySelectorAll("h1, h2, h3, p, li, td");
          paragraphs.forEach(p => {
            searchData.push({
              title: p.tagName === "H1" || p.tagName === "H2" || p.tagName === "H3" ? p.textContent.trim() : "",
              text: p.textContent.trim(),
              url: window.location.href,
            });
          });
        }
      });

    let debounceTimer;
    searchInput.addEventListener("input", () => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(performSearch, 150);
    });
    searchInput.addEventListener("focus", () => { if (searchInput.value.length > 1) performSearch(); });
    document.addEventListener("click", e => {
      if (!e.target.closest(".header-search")) searchResults.classList.remove("active");
    });

    function performSearch() {
      const q = searchInput.value.trim().toLowerCase();
      if (q.length < 2) { searchResults.classList.remove("active"); return; }
      const results = [];
      searchData.forEach(item => {
        const text = (item.text || "").toLowerCase();
        const title = (item.title || "").toLowerCase();
        if (text.includes(q) || title.includes(q)) {
          results.push(item);
        }
      });
      if (results.length === 0) {
        searchResults.innerHTML = '<div style="padding:16px;color:var(--muted-foreground);text-align:center;font-size:0.85rem;">Результаты не найдены</div>';
      } else {
        searchResults.innerHTML = results.slice(0, 8).map(r => {
          const excerpt = r.text ? r.text.substring(0, 120) + (r.text.length > 120 ? "..." : "") : "";
          const hlExcerpt = excerpt.replace(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")})`, "gi"), "<mark>$1</mark>");
          return `<a href="${r.url}" class="search-result-item" onclick="document.getElementById('search-results').classList.remove('active')"><div class="sr-title">${r.title || r.url.split("/").pop()}</div><div class="sr-excerpt">${hlExcerpt}</div></a>`;
        }).join("");
      }
      searchResults.classList.add("active");
    }

    // Keyboard shortcut
    document.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") { e.preventDefault(); searchInput.focus(); }
      if (e.key === "Escape") { searchInput.blur(); searchResults.classList.remove("active"); }
    });
  }

  // ===== Language Toggle =====
  const langBtn = document.getElementById("lang-toggle");
  if (langBtn) {
    const html = document.documentElement;
    const curLang = html.getAttribute("lang") || "ru";
    langBtn.textContent = curLang === "ru" ? "EN" : "RU";
    langBtn.addEventListener("click", () => {
      // Placeholder: toggle visual indicator only
      const lang = html.getAttribute("lang") === "ru" ? "en" : "ru";
      html.setAttribute("lang", lang);
      langBtn.textContent = lang === "ru" ? "EN" : "RU";
      localStorage.setItem("qstack-docs-lang", lang);
    });
  }

  // ===== Copy code button =====
  document.querySelectorAll(".code-header").forEach(header => {
    const copyBtn = document.createElement("button");
    copyBtn.textContent = "Copy";
    copyBtn.style.cssText = "background:transparent;border:1px solid var(--border);border-radius:4px;padding:2px 8px;font-size:0.7rem;color:var(--muted-foreground);cursor:pointer;font-family:var(--font-mono);";
    header.appendChild(copyBtn);
    const pre = header.nextElementSibling;
    if (pre && pre.querySelector("code")) {
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(pre.querySelector("code").textContent);
        copyBtn.textContent = "Copied!";
        setTimeout(() => { copyBtn.textContent = "Copy"; }, 1500);
      });
    }
  });
})();
