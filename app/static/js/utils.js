/**
 * Utility functions for the Stimulus Generator
 */

// ========== DOM HELPERS ==========

function $(selector) {
  return document.querySelector(selector);
}

function $$(selector) {
  return document.querySelectorAll(selector);
}

function createElement(tag, attrs = {}, children = []) {
  const el = document.createElement(tag);
  Object.entries(attrs).forEach(([key, value]) => {
    if (key === "class") {
      el.className = value;
    } else if (key === "dataset") {
      Object.entries(value).forEach(([dataKey, dataValue]) => {
        el.dataset[dataKey] = dataValue;
      });
    } else if (key.startsWith("on")) {
      el.addEventListener(key.slice(2).toLowerCase(), value);
    } else {
      el.setAttribute(key, value);
    }
  });
  children.forEach((child) => {
    if (typeof child === "string") {
      el.appendChild(document.createTextNode(child));
    } else if (child) {
      el.appendChild(child);
    }
  });
  return el;
}

// ========== TOAST NOTIFICATIONS ==========

const toastContainer = createElement("div", { class: "toast-container" });
document.body.appendChild(toastContainer);

function showToast(message, type = "info", duration = 4000) {
  const toast = createElement("div", { class: `toast toast-${type}` }, [
    message,
  ]);
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(100%)";
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

function showSuccess(message) {
  showToast(message, "success");
}

function showError(message) {
  showToast(message, "error", 6000);
}

function showInfo(message) {
  showToast(message, "info");
}

// ========== FORMATTING ==========

function formatDuration(ms) {
  if (!ms) return "--:--";
  const seconds = Math.floor(ms / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFileSize(bytes) {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let unitIndex = 0;
  let size = bytes;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`;
}

function truncateText(text, maxLength = 100) {
  if (!text || text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "...";
}

// ========== SLIDER HELPERS ==========

function initSlider(sliderId, options = {}) {
  const slider = $(`#${sliderId}`);
  const valueDisplay = $(`#${sliderId}-value`);

  if (!slider) return;

  const {
    min = 0,
    max = 100,
    step = 1,
    value = 50,
    unit = "",
    decimals = 0,
    onChange = null,
  } = options;

  slider.min = min;
  slider.max = max;
  slider.step = step;
  slider.value = value;

  function updateDisplay() {
    const val = parseFloat(slider.value);
    if (valueDisplay) {
      valueDisplay.textContent = val.toFixed(decimals) + unit;
    }
  }

  updateDisplay();

  slider.addEventListener("input", () => {
    updateDisplay();
    if (onChange) onChange(parseFloat(slider.value));
  });

  return {
    getValue: () => parseFloat(slider.value),
    setValue: (val) => {
      slider.value = val;
      updateDisplay();
    },
  };
}

// ========== COLLAPSIBLE CARDS ==========

function initCollapsibleCards() {
  $$(".card-header").forEach((header) => {
    header.addEventListener("click", () => {
      const card = header.closest(".card");
      card.classList.toggle("collapsed");
    });
  });
}

// ========== TABS ==========

function initTabs(containerId) {
  const container = $(`#${containerId}`);
  if (!container) return;

  const tabs = container.querySelectorAll(".tab");
  const contents = container.querySelectorAll(".tab-content");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const targetId = tab.dataset.tab;

      tabs.forEach((t) => t.classList.remove("active"));
      contents.forEach((c) => c.classList.remove("active"));

      tab.classList.add("active");
      const target = container.querySelector(`#${targetId}`);
      if (target) target.classList.add("active");
    });
  });
}

// ========== MODAL HELPERS ==========

function openModal(modalId) {
  const modal = $(`#${modalId}`);
  if (modal) {
    modal.classList.add("active");
    document.body.style.overflow = "hidden";
  }
}

function closeModal(modalId) {
  const modal = $(`#${modalId}`);
  if (modal) {
    modal.classList.remove("active");
    document.body.style.overflow = "";
  }
}

function initModals() {
  // Close modal when clicking overlay
  $$(".modal-overlay").forEach((overlay) => {
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) {
        overlay.classList.remove("active");
        document.body.style.overflow = "";
      }
    });
  });

  // Close modal buttons
  $$(".modal-close").forEach((btn) => {
    btn.addEventListener("click", () => {
      const modal = btn.closest(".modal-overlay");
      if (modal) {
        modal.classList.remove("active");
        document.body.style.overflow = "";
      }
    });
  });
}

// ========== DEBOUNCE / THROTTLE ==========

function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function throttle(func, limit = 300) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

// ========== LOCAL STORAGE ==========

function saveToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (e) {
    console.warn("localStorage not available:", e);
  }
}

function loadFromStorage(key, defaultValue = null) {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (e) {
    console.warn("localStorage not available:", e);
    return defaultValue;
  }
}

// ========== COPY TO CLIPBOARD ==========

async function copyToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    showSuccess("Copied to clipboard!");
    return true;
  } catch (err) {
    console.error("Failed to copy:", err);
    showError("Failed to copy to clipboard");
    return false;
  }
}

// ========== URL HELPERS ==========

function getUrlParam(name) {
  const params = new URLSearchParams(window.location.search);
  return params.get(name);
}

function setUrlParam(name, value) {
  const url = new URL(window.location);
  url.searchParams.set(name, value);
  window.history.replaceState({}, "", url);
}

// ========== LOADING STATE ==========

function setLoading(element, isLoading, loadingText = "Loading...") {
  if (typeof element === "string") {
    element = $(element);
  }
  if (!element) return;

  if (isLoading) {
    element.dataset.originalText = element.textContent;
    element.textContent = loadingText;
    element.disabled = true;
    element.classList.add("loading");
  } else {
    element.textContent = element.dataset.originalText || element.textContent;
    element.disabled = false;
    element.classList.remove("loading");
  }
}

// ========== WORD COUNT ==========

function countWords(text) {
  if (!text) return 0;
  return text
    .trim()
    .split(/\s+/)
    .filter((w) => w.length > 0).length;
}

function estimateSpeechDuration(text, wordsPerMinute = 140) {
  const words = countWords(text);
  const minutes = words / wordsPerMinute;
  return Math.round(minutes * 60 * 1000); // Return in ms
}

// ========== EXPORT ==========

window.utils = {
  $,
  $$,
  createElement,
  showToast,
  showSuccess,
  showError,
  showInfo,
  formatDuration,
  formatDate,
  formatFileSize,
  truncateText,
  initSlider,
  initCollapsibleCards,
  initTabs,
  openModal,
  closeModal,
  initModals,
  debounce,
  throttle,
  saveToStorage,
  loadFromStorage,
  copyToClipboard,
  getUrlParam,
  setUrlParam,
  setLoading,
  countWords,
  estimateSpeechDuration,
};
