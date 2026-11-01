(() => {
  const activeLink = document.querySelector(".sidebar-link.is-active");
  activeLink?.setAttribute("aria-current", "page");
})();
