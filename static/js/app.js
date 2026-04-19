(() => {
  "use strict";

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
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach((flash, index) => {
      setTimeout(() => {
        flash.style.opacity = "0";
        flash.style.transform = "translateY(-6px)";
        flash.style.transition = "all .25s ease";
        setTimeout(() => flash.remove(), 250);
      }, 3200 + index * 250);
    });
  }

  function setupCopyButtons() {
    const copyButtons = document.querySelectorAll("[data-copy-text]");

    copyButtons.forEach((button) => {
      button.addEventListener("click", async () => {
        const text = button.dataset.copyText || "";
        if (!text.trim()) {
          showToast("Нет текста для копирования", "warning");
          return;
        }

        try {
          await navigator.clipboard.writeText(text);
          showToast("Скопировано", "success");
        } catch (error) {
          console.error(error);
          showToast("Не удалось скопировать", "error");
        }
      });
    });
  }

  function setupConfirmActions() {
    const dangerForms = document.querySelectorAll("[data-confirm]");
    dangerForms.forEach((element) => {
      element.addEventListener("submit", (event) => {
        const message = element.dataset.confirm || "Вы уверены?";
        const ok = window.confirm(message);
        if (!ok) {
          event.preventDefault();
        }
      });
    });
  }

  function setupTextareaAutoResize() {
    const textareas = document.querySelectorAll("textarea.auto-resize");
    textareas.forEach((textarea) => {
      const resize = () => {
        textarea.style.height = "auto";
        textarea.style.height = `${textarea.scrollHeight}px`;
      };

      textarea.addEventListener("input", resize);
      resize();
    });
  }

  function setupSmoothAnchors() {
    const links = document.querySelectorAll('a[href^="#"]');
    links.forEach((link) => {
      link.addEventListener("click", (event) => {
        const id = link.getAttribute("href");
        if (!id || id === "#") return;

        const target = document.querySelector(id);
        if (!target) return;

        event.preventDefault();
        target.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      });
    });
  }

  function setupInputFocusState() {
    const fields = document.querySelectorAll(".input, .editor, select");
    fields.forEach((field) => {
      field.addEventListener("focus", () => {
        field.closest(".form-group")?.classList.add("is-focused");
      });

      field.addEventListener("blur", () => {
        field.closest(".form-group")?.classList.remove("is-focused");
      });
    });
  }

  function setupStatCounter() {
    const counters = document.querySelectorAll("[data-counter]");
    counters.forEach((counter) => {
      const target = Number(counter.dataset.counter || 0);
      const duration = 900;
      const start = 0;
      const startTime = performance.now();

      function update(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const value = Math.floor(start + (target - start) * progress);
        counter.textContent = value.toLocaleString();

        if (progress < 1) {
          requestAnimationFrame(update);
        } else {
          counter.textContent = target.toLocaleString();
        }
      }

      requestAnimationFrame(update);
    });
  }

  function exposeUIHelpers() {
    window.VoiceFlowUI = {
      toast: showToast
    };
  }

  ready(() => {
    autoHideFlashes();
    setupCopyButtons();
    setupConfirmActions();
    setupTextareaAutoResize();
    setupSmoothAnchors();
    setupInputFocusState();
    setupStatCounter();
    exposeUIHelpers();
  });
})();