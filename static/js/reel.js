document.addEventListener("DOMContentLoaded", () => {
  const entries = [...document.querySelectorAll(".reel-entry")];
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const setPlaybackState = (entry, playing) => {
    const stage = entry.querySelector(".reel-stage");
    const video = entry.querySelector(".reel-video");
    stage.classList.toggle("is-paused", !playing);
    entry.querySelectorAll("[data-reel-play]").forEach((button) => {
      button.setAttribute("aria-label", playing ? "Pause reel" : "Play reel");
      button.title = playing ? "Pause" : "Play";
      const label = button.querySelector(".reel-action-label");
      if (label) label.textContent = playing ? "Pause" : "Play";
      const icon = button.querySelector(".reel-icon");
      if (icon) {
        icon.innerHTML = playing
          ? '<path d="M8 5h3v14H8zm5 0h3v14h-3z"/>'
          : '<path d="m8 5 12 7-12 7z"/>';
      }
    });
    if (!playing) video.pause();
  };

  const togglePlayback = async (entry) => {
    const video = entry.querySelector(".reel-video");
    if (video.paused) {
      try {
        await video.play();
        setPlaybackState(entry, true);
      } catch (error) {
        console.warn("Reel autoplay was blocked by the browser.", error);
        setPlaybackState(entry, false);
      }
    } else {
      setPlaybackState(entry, false);
    }
  };

  entries.forEach((entry) => {
    const video = entry.querySelector(".reel-video");
    const progress = entry.querySelector(".reel-progress span");
    const fallback = entry.querySelector(".reel-video-fallback");

    video.addEventListener("play", () => setPlaybackState(entry, true));
    video.addEventListener("pause", () => setPlaybackState(entry, false));
    video.addEventListener("timeupdate", () => {
      if (Number.isFinite(video.duration) && video.duration > 0) {
        progress.style.width = `${(video.currentTime / video.duration) * 100}%`;
      }
    });
    video.addEventListener("error", () => {
      fallback.hidden = false;
      setPlaybackState(entry, false);
    });
    video.addEventListener("loadeddata", () => {
      fallback.hidden = true;
    });

    entry.querySelectorAll("[data-reel-play]").forEach((button) => {
      button.addEventListener("click", () => togglePlayback(entry));
    });
    video.addEventListener("click", () => togglePlayback(entry));

    entry.querySelectorAll("[data-reel-mute]").forEach((button) => {
      button.addEventListener("click", () => {
        video.muted = !video.muted;
        const iconName = video.muted ? "volume-off" : "volume";
        const iconMarkup = video.muted
          ? '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="m16 9 5 6m0-6-5 6"/>'
          : '<path d="M11 5 6 9H3v6h3l5 4z"/><path d="M15.5 8.5a5 5 0 0 1 0 7m3-10a9 9 0 0 1 0 13"/>';
        entry.querySelectorAll("[data-reel-mute]").forEach((muteButton) => {
          muteButton.setAttribute("aria-label", video.muted ? "Unmute video" : "Mute video");
          muteButton.title = video.muted ? "Unmute" : "Mute";
          const label = muteButton.querySelector(".reel-action-label");
          if (label) label.textContent = video.muted ? "Sound" : "Mute";
          const icon = muteButton.querySelector(".reel-icon");
          if (icon) {
            icon.dataset.icon = iconName;
            icon.innerHTML = iconMarkup;
          }
        });
      });
    });
  });

  if ("IntersectionObserver" in window) {
    const observer = new IntersectionObserver((records) => {
      records.forEach((record) => {
        const video = record.target.querySelector(".reel-video");
        if (record.isIntersecting && record.intersectionRatio >= 0.65) {
          if (!reducedMotion) {
            video.play().catch(() => setPlaybackState(record.target, false));
          }
        } else {
          video.pause();
        }
      });
    }, { threshold: [0, 0.2, 0.65, 1] });
    entries.forEach((entry) => observer.observe(entry));
  } else if (entries.length && !reducedMotion) {
    entries[0].querySelector(".reel-video").play().catch((error) => {
      console.warn("Reel autoplay was blocked by the browser.", error);
    });
  }

  document.querySelectorAll("[data-comments-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const panel = document.querySelector(`#comments-${CSS.escape(button.dataset.commentsToggle)}`);
      if (!panel) return;
      document.querySelectorAll(".reel-comments-panel[open]").forEach((openPanel) => {
        if (openPanel !== panel) openPanel.removeAttribute("open");
      });
      panel.open = !panel.open;
      if (panel.open) panel.querySelector("input[name='body']").focus();
    });
  });

  document.querySelectorAll("[data-comments-close]").forEach((button) => {
    button.addEventListener("click", () => {
      const panel = document.querySelector(`#comments-${CSS.escape(button.dataset.commentsClose)}`);
      if (panel) panel.removeAttribute("open");
    });
  });

  document.querySelectorAll("[data-reel-share]").forEach((button) => {
    button.addEventListener("click", async () => {
      const status = button.closest(".reel-entry").querySelector(".reel-interaction-status");
      try {
        await navigator.clipboard.writeText(button.dataset.reelShare);
        status.textContent = "Reel link copied.";
      } catch {
        status.textContent = `Copy this link: ${button.dataset.reelShare}`;
      }
      window.setTimeout(() => { status.textContent = ""; }, 4000);
    });
  });

  const commentsMatch = window.location.hash.match(/^#comments-(\d+)$/);
  if (commentsMatch) {
    const panel = document.querySelector(`#comments-${CSS.escape(commentsMatch[1])}`);
    if (panel) panel.open = true;
  }
});
