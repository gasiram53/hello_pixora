document.addEventListener("DOMContentLoaded", () => {
  const menuTrigger = document.querySelector("[data-profile-menu-trigger]");
  const profileMenu = document.querySelector("[data-profile-menu]");
  const shareButton = document.querySelector("[data-profile-share]");
  const copyButton = document.querySelector("[data-copy-profile]");
  const qrButton = document.querySelector("[data-open-profile-qr]");
  const qrDialog = document.querySelector("[data-profile-qr-dialog]");
  const reportButton = document.querySelector("[data-open-profile-report]");
  const reportDialog = document.querySelector("[data-profile-report-dialog]");
  const status = document.querySelector(".profile-share-status");
  const profileUrl = window.location.href.split("#")[0];

  const closeMenu = (returnFocus = false) => {
    if (!profileMenu || !menuTrigger) return;
    profileMenu.hidden = true;
    menuTrigger.setAttribute("aria-expanded", "false");
    if (returnFocus) menuTrigger.focus();
  };

  const showStatus = (message) => {
    if (!status) return;
    status.textContent = message;
    window.clearTimeout(showStatus.timeoutId);
    showStatus.timeoutId = window.setTimeout(() => { status.textContent = ""; }, 5000);
  };

  const copyProfileUrl = async () => {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(profileUrl);
      return true;
    }

    const temporaryInput = document.createElement("textarea");
    temporaryInput.value = profileUrl;
    temporaryInput.setAttribute("readonly", "");
    temporaryInput.className = "profile-copy-fallback";
    document.body.append(temporaryInput);
    temporaryInput.select();
    const copied = document.execCommand("copy");
    temporaryInput.remove();
    if (!copied) throw new Error("Clipboard access is unavailable.");
    return true;
  };

  const openDialog = (dialog) => {
    if (dialog && typeof dialog.showModal === "function") dialog.showModal();
  };

  menuTrigger?.addEventListener("click", () => {
    const isOpening = profileMenu.hidden;
    profileMenu.hidden = !isOpening;
    menuTrigger.setAttribute("aria-expanded", String(isOpening));
  });

  shareButton?.addEventListener("click", async () => {
    closeMenu(true);
    try {
      if (navigator.share) {
        await navigator.share({ title: document.title, url: profileUrl });
      } else {
        await copyProfileUrl();
        showStatus("Profile link copied.");
      }
    } catch (error) {
      if (error.name === "AbortError") return;
      try {
        await copyProfileUrl();
        showStatus("Profile link copied.");
      } catch {
        showStatus(`Copy this profile link: ${profileUrl}`);
      }
    }
  });

  copyButton?.addEventListener("click", async () => {
    closeMenu(true);
    try {
      await copyProfileUrl();
      showStatus("Profile link copied.");
    } catch {
      showStatus(`Copy this profile link: ${profileUrl}`);
    }
  });

  qrButton?.addEventListener("click", () => {
    closeMenu();
    openDialog(qrDialog);
  });

  reportButton?.addEventListener("click", () => {
    closeMenu();
    openDialog(reportDialog);
  });

  document.querySelectorAll("[data-close-profile-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog")?.close());
  });

  document.querySelectorAll(".profile-page dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => menuTrigger?.focus());
  });

  document.addEventListener("click", (event) => {
    if (profileMenu && !profileMenu.hidden && !profileMenu.contains(event.target) && !menuTrigger.contains(event.target)) {
      closeMenu();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && profileMenu && !profileMenu.hidden) {
      closeMenu(true);
      return;
    }
    if (!profileMenu || profileMenu.hidden) return;
    const menuItems = Array.from(profileMenu.querySelectorAll('[role="menuitem"]:not([disabled])'));
    const currentIndex = menuItems.indexOf(document.activeElement);
    if (event.key === "ArrowDown" && (document.activeElement === menuTrigger || currentIndex >= 0)) {
      event.preventDefault();
      menuItems[(currentIndex + 1) % menuItems.length]?.focus();
    } else if (event.key === "ArrowUp" && currentIndex >= 0) {
      event.preventDefault();
      menuItems[(currentIndex - 1 + menuItems.length) % menuItems.length]?.focus();
    } else if (event.key === "Tab") {
      window.setTimeout(() => {
        if (!profileMenu.contains(document.activeElement) && document.activeElement !== menuTrigger) closeMenu();
      }, 0);
    }
  });

  const profileTabs = document.querySelectorAll("[data-profile-tab]");
  if (profileTabs.length) {
    profileTabs.forEach((tab) => tab.addEventListener("click", () => {
      const postsPanel = document.querySelector("#profile-posts");
      const taggedPanel = document.querySelector("#tagged-panel");
      document.querySelectorAll(".profile-tab[data-profile-tab]").forEach((profileTab) => {
        profileTab.setAttribute("aria-selected", "false");
        profileTab.classList.remove("is-active");
      });
      tab.setAttribute("aria-selected", "true");
      tab.classList.add("is-active");
      postsPanel.hidden = tab.dataset.profileTab !== "posts";
      taggedPanel.hidden = tab.dataset.profileTab !== "tagged";
    }));
  }
});
