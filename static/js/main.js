document.addEventListener("submit", (event) => {
  const form = event.target.closest("form[data-confirm]");
  if (form && !window.confirm(form.dataset.confirm)) {
    event.preventDefault();
  }
});

(() => {
  const toggle = document.querySelector("[data-theme-toggle]");
  if (!toggle) return;

  let isDark = false;
  try {
    isDark = localStorage.getItem("pixora:theme") === "dark";
  } catch (error) {
    console.error("Could not read the saved theme preference.", error);
  }

  const applyTheme = () => {
    document.body.dataset.theme = isDark ? "dark" : "light";
    toggle.setAttribute("aria-pressed", String(isDark));
    const label = isDark ? "Switch to light mode" : "Switch to dark mode";
    toggle.setAttribute("aria-label", label);
    toggle.querySelector("[data-theme-label]").textContent = isDark ? "Light mode" : "Dark mode";
  };
  applyTheme();

  toggle.addEventListener("click", () => {
    isDark = !isDark;
    applyTheme();
    try {
      localStorage.setItem("pixora:theme", isDark ? "dark" : "light");
    } catch (error) {
      console.error("Could not save the theme preference.", error);
    }
  });
})();
