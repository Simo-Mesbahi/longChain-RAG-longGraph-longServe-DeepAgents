"use strict";

// Resolve appearance before CSS paints; no inline script or relaxed CSP is needed.
(() => {
  const key = "atlasdocai_theme";
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const root = document.documentElement;
  const valid = (value) => ["light", "dark", "system"].includes(value);
  let preference = "system";
  try {
    const saved = localStorage.getItem(key);
    if (valid(saved)) preference = saved;
  } catch {
    // Private or restricted storage must not prevent the interface from loading.
  }

  function apply() {
    const theme = preference === "system" ? (media.matches ? "dark" : "light") : preference;
    root.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]').content =
      theme === "dark" ? "#161819" : "#fafbfc";
    document.querySelectorAll('input[name="theme"]').forEach((input) => {
      input.checked = input.value === preference;
    });
  }

  apply();
  media.addEventListener("change", apply);
  window.addEventListener("storage", (event) => {
    if (event.key !== key && event.key !== null) return;
    preference = valid(event.newValue) ? event.newValue : "system";
    apply();
  });
  document.addEventListener("DOMContentLoaded", () => {
    apply();
    document.querySelectorAll('input[name="theme"]').forEach((input) => {
      input.addEventListener("change", () => {
        preference = input.value;
        try {
          if (preference === "system") localStorage.removeItem(key);
          else localStorage.setItem(key, preference);
        } catch {
          // The selected appearance still works for this page without storage.
        }
        apply();
      });
    });
  });
})();
