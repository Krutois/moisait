(() => {
  const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
  const nativeFetch = window.fetch.bind(window);

  window.fetch = (input, init = {}) => {
    const options = { ...init };
    const method = String(options.method || "GET").toUpperCase();

    if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method) && csrfToken) {
      const headers = new Headers(options.headers || {});
      if (!headers.has("X-CSRFToken")) {
        headers.set("X-CSRFToken", csrfToken);
      }
      options.headers = headers;
    }

    return nativeFetch(input, options);
  };

  function ready(fn) {
    if (document.readyState !== "loading") {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  function createToastContainer() {
    let container = document.querySelector(".toast-container");
    if (!container) {
      container = document.createElement("div");
      container.className = "toast-container";
      document.body.appendChild(container);
    }
    return container;
  }

  function showToast(message, type = "info", duration = 2600) {
    const container = createToastContainer();
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add("show");
    });

    setTimeout(() => {
      toast.classList.remove("show");
      setTimeout(() => toast.remove(), 260);
    }, duration);
  }

  function autoHideFlashes() {
    document.querySelectorAll(".flash").forEach((flash, index) => {
      setTimeout(() => {
        flash.style.opacity = "0";
        flash.style.transform = "translateY(-6px)";
        setTimeout(() => flash.remove(), 250);
      }, 3200 + index * 250);
    });
  }

  function setupConfirmActions() {
    document.querySelectorAll("[data-confirm]").forEach((form) => {
      form.addEventListener("submit", (event) => {
        const message = form.dataset.confirm || window.SmartLecture_I18N?.confirmDefault || "Are you sure?";
        if (!window.confirm(message)) {
          event.preventDefault();
        }
      });
    });
  }

  function setupMobileMenu() {
    const header = document.querySelector(".site-header");
    const button = document.getElementById("mobileMenuBtn");

    if (!header || !button) return;

    function closeMenu() {
      header.classList.remove("menu-open");
      document.body.classList.remove("menu-locked");
    }

    function toggleMenu() {
      header.classList.toggle("menu-open");
      document.body.classList.toggle("menu-locked", header.classList.contains("menu-open"));
    }

    button.addEventListener("click", (event) => {
      event.stopPropagation();
      toggleMenu();
    });

    document.querySelectorAll(".nav-links a, .nav-actions a").forEach((link) => {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu();
      }
    });

    window.addEventListener("resize", () => {
      if (window.innerWidth > 860) {
        closeMenu();
      }
    });
  }

  function setupAccountMenu() {
    const menu = document.querySelector(".account-menu");
    if (!menu) return;

    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) {
        menu.removeAttribute("open");
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        menu.removeAttribute("open");
      }
    });
  }

  function setupPasswordToggles() {
    document.querySelectorAll('input[type="password"]').forEach((input) => {
      if (input.dataset.toggleReady === "1") return;
      input.dataset.toggleReady = "1";
      const button = document.createElement("button");
      button.type = "button";
      button.className = "password-toggle";
      button.textContent = window.SmartLecture_I18N?.showPassword || "Show";
      button.addEventListener("click", () => {
        const shown = input.type === "text";
        input.type = shown ? "password" : "text";
        button.textContent = shown
          ? (window.SmartLecture_I18N?.showPassword || "Show")
          : (window.SmartLecture_I18N?.hidePassword || "Hide");
      });
      input.insertAdjacentElement("afterend", button);
    });
  }

  function registerServiceWorker() {
    const swUrl = window.SmartLecture_CONFIG?.serviceWorkerUrl;
    if ("serviceWorker" in navigator && swUrl) {
      navigator.serviceWorker.register(swUrl).catch(() => {});
    }
  }

  function setupNetworkState() {
    const offline = window.SmartLecture_I18N?.offline || "No internet connection";
    const online = window.SmartLecture_I18N?.online || "Connection restored";
    window.addEventListener("offline", () => showToast(offline, "warning", 3600));
    window.addEventListener("online", () => showToast(online, "success", 2200));
  }

  function applyAccessibilitySettings(settings = {}) {
    document.body.classList.toggle("access-text-large", settings.textSize === "large");
    document.body.classList.toggle("access-text-xl", settings.textSize === "xl");
    document.body.classList.toggle("access-high-contrast", settings.contrast === "high");
    document.body.classList.toggle("access-light", settings.theme === "light");
    document.body.classList.toggle("access-reduce-motion", settings.motion === "reduced");
  }

  function getAccessibilitySettings() {
    try {
      return JSON.parse(localStorage.getItem("smartlecture_accessibility") || "{}");
    } catch (error) {
      return {};
    }
  }

  function saveAccessibilitySettings(settings) {
    localStorage.setItem("smartlecture_accessibility", JSON.stringify(settings));
    applyAccessibilitySettings(settings);
  }

  function setupAccessibilitySettings() {
    const settings = getAccessibilitySettings();
    applyAccessibilitySettings(settings);

    document.querySelectorAll("[data-access-setting]").forEach((control) => {
      const key = control.dataset.accessSetting;
      if (settings[key]) {
        control.value = settings[key];
      }
      control.addEventListener("change", () => {
        const next = { ...getAccessibilitySettings(), [key]: control.value };
        saveAccessibilitySettings(next);
        if (next.visualAlerts !== "off") {
          showToast(window.SmartLecture_I18N?.accessibilitySaved || "Accessibility settings saved", "success", 1800);
        }
      });
    });
  }

  window.SmartLectureUI = {
    toast: showToast,
  };

  ready(() => {
    autoHideFlashes();
    setupConfirmActions();
    setupMobileMenu();
    setupAccountMenu();
    setupPasswordToggles();
    setupNetworkState();
    setupAccessibilitySettings();
    registerServiceWorker();
  });
})();
