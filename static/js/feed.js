document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-save-post]").forEach((button) => {
    button.addEventListener("click", async () => {
      button.disabled = true;
      try {
        const response = await fetch(button.dataset.saveUrl, {
          method: "POST",
          headers: {
            "X-CSRFToken": document.querySelector('meta[name="csrf-token"]').content,
            Accept: "application/json",
          },
        });
        if (!response.ok) throw new Error(`Could not save this post (${response.status}).`);
        const { saved } = await response.json();
        button.classList.toggle("is-saved", saved);
        button.setAttribute("aria-pressed", String(saved));
        button.setAttribute("aria-label", saved ? "Remove saved post" : "Save post");
        button.title = saved ? "Remove saved post" : "Save";
      } catch (error) {
        console.error(error);
        window.alert("Could not update saved posts. Please try again.");
      } finally {
        button.disabled = false;
      }
    });
  });

  document.querySelectorAll("[data-share-url]").forEach((button) => {
    button.addEventListener("click", async () => {
      const status = button.closest(".post-content").querySelector(".share-status");
      const postUrl = button.dataset.shareUrl;
      try {
        await navigator.clipboard.writeText(postUrl);
        status.textContent = "Post link copied.";
      } catch {
        status.textContent = `Copy this link: ${postUrl}`;
      }
      window.setTimeout(() => { status.textContent = ""; }, 4000);
    });
  });

  document.addEventListener("click", (event) => {
    document.querySelectorAll(".post-menu[open]").forEach((menu) => {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
});
