(() => {
  const groupsElement = document.querySelector("[data-story-groups]");
  const groups = groupsElement ? JSON.parse(groupsElement.textContent) : [];
  const composer = document.querySelector("[data-story-dialog]");
  const viewer = document.querySelector("[data-story-viewer]");
  const fileInput = document.querySelector("[data-story-file]");
  const preview = document.querySelector("[data-story-preview]");
  const captionInput = document.querySelector("[data-caption-input]");
  const overlayInput = document.querySelector("[data-overlay-input]");
  const submitButton = document.querySelector("[data-story-submit]");
  const viewerStage = document.querySelector("[data-story-stage]");
  const progressContainer = document.querySelector("[data-story-progress]");
  const viewerAvatar = document.querySelector("[data-viewer-avatar]");
  const viewerName = document.querySelector("[data-viewer-name]");
  const viewerTime = document.querySelector("[data-viewer-time]");
  const viewerOverlay = document.querySelector("[data-viewer-overlay]");
  const viewerCaption = document.querySelector("[data-viewer-caption]");
  const viewerLoading = document.querySelector("[data-viewer-loading]");
  const ownerTools = document.querySelector("[data-owner-tools]");
  const viewCount = document.querySelector("[data-view-count]");
  const viewersButton = document.querySelector("[data-story-viewers]");
  const viewerList = document.querySelector("[data-story-viewer-list]");
  const deleteForm = document.querySelector("[data-story-delete-form]");
  const replyForm = document.querySelector("[data-story-reply-form]");
  const replyInput = document.querySelector("[data-reply-input]");
  const pauseButton = document.querySelector("[data-story-pause]");
  const errorMessage = document.querySelector("[data-story-error]");

  let previewUrl;
  let activeGroupIndex = -1;
  let activeStoryIndex = 0;
  let activeMedia;
  let animationFrame;
  let storyStartedAt = 0;
  let storyElapsed = 0;
  let storyDuration = 6000;
  let isPaused = false;
  let endMessageTimer;

  const closeDialog = (dialog) => {
    if (dialog?.open && dialog.close) dialog.close();
    else dialog?.removeAttribute("open");
  };

  const updatePreviewOverlay = () => {
    const text = overlayInput?.value.trim();
    let overlay = preview?.querySelector(".story-preview-overlay");
    if (text) {
      if (!overlay) {
        overlay = document.createElement("span");
        overlay.className = "story-preview-overlay";
        preview.append(overlay);
      }
      overlay.textContent = text;
    } else {
      overlay?.remove();
    }
  };

  document.querySelectorAll("[data-open-story-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      if (composer?.showModal) composer.showModal();
      else composer?.setAttribute("open", "");
    });
  });

  document.querySelectorAll("[data-cancel-story]").forEach((button) => {
    button.addEventListener("click", () => closeDialog(composer));
  });

  if (composer) {
    composer.addEventListener("click", (event) => {
      if (event.target === composer) closeDialog(composer);
    });
    composer.addEventListener("close", () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      preview?.replaceChildren();
      if (preview) preview.hidden = true;
      if (fileInput) fileInput.value = "";
      if (captionInput) captionInput.value = "";
      if (overlayInput) overlayInput.value = "";
      if (submitButton) submitButton.disabled = true;
    });
  }

  if (fileInput && preview) {
    fileInput.addEventListener("change", () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      previewUrl = null;
      preview.replaceChildren();
      preview.hidden = true;
      const file = fileInput.files?.[0];
      if (!file) {
        submitButton.disabled = true;
        return;
      }
      if (file.size > 16 * 1024 * 1024) {
        fileInput.value = "";
        submitButton.disabled = true;
        window.alert("Choose a file smaller than 16 MB.");
        return;
      }
      previewUrl = URL.createObjectURL(file);
      const media = document.createElement(file.type.startsWith("video/") ? "video" : "img");
      media.src = previewUrl;
      if (media instanceof HTMLVideoElement) {
        media.controls = true;
        media.muted = true;
        media.playsInline = true;
      } else {
        media.alt = "Selected story preview";
      }
      preview.append(media);
      preview.hidden = false;
      submitButton.disabled = false;
      updatePreviewOverlay();
    });
  }

  overlayInput?.addEventListener("input", updatePreviewOverlay);

  const currentGroup = () => groups[activeGroupIndex];
  const currentStory = () => currentGroup()?.stories[activeStoryIndex];

  const formatAge = (isoTime) => {
    if (!isoTime) return "";
    const ageMinutes = Math.max(0, Math.floor((Date.now() - new Date(isoTime).getTime()) / 60000));
    if (ageMinutes < 1) return "now";
    if (ageMinutes < 60) return `${ageMinutes}m`;
    const ageHours = Math.floor(ageMinutes / 60);
    if (ageHours < 24) return `${ageHours}h`;
    return `${Math.floor(ageHours / 24)}d`;
  };

  const updateGroupRing = (group) => {
    if (group.stories.every((story) => story.is_viewed)) {
      document.querySelectorAll("[data-open-story-group]").forEach((button) => {
        if (Number(button.dataset.openStoryGroup) === activeGroupIndex) {
          button.classList.add("is-viewed");
        }
      });
    }
  };

  const markViewed = async (story) => {
    if (story.is_viewed) return;
    const csrfToken = document.querySelector('.story-compose-form input[name="csrf_token"]')?.value
      || document.querySelector('input[name="csrf_token"]')?.value;
    try {
      const response = await fetch(story.view_url, {
        method: "POST",
        headers: { "X-CSRFToken": csrfToken, Accept: "application/json" },
      });
      if (!response.ok) throw new Error(`Could not record story view (${response.status}).`);
      story.is_viewed = true;
      updateGroupRing(currentGroup());
    } catch (error) {
      if (error.name !== "AbortError") console.error(error);
    }
  };

  const pauseMedia = () => {
    if (activeMedia instanceof HTMLVideoElement) activeMedia.pause();
  };

  const clearStory = () => {
    window.clearTimeout(endMessageTimer);
    endMessageTimer = undefined;
    if (animationFrame) cancelAnimationFrame(animationFrame);
    animationFrame = null;
    pauseMedia();
    activeMedia?.remove();
    activeMedia = null;
  };

  const renderProgress = (group) => {
    progressContainer.replaceChildren();
    group.stories.forEach((_story, index) => {
      const track = document.createElement("span");
      track.className = "story-progress-track";
      const fill = document.createElement("span");
      fill.className = "story-progress-fill";
      if (index < activeStoryIndex) fill.style.width = "100%";
      track.append(fill);
      progressContainer.append(track);
    });
  };

  const setError = (text) => {
    errorMessage.textContent = text;
    errorMessage.hidden = false;
    window.setTimeout(() => { errorMessage.hidden = true; }, 4000);
  };

  const progressTick = (now) => {
    const story = currentStory();
    if (!story || isPaused) return;
    if (activeMedia instanceof HTMLVideoElement
      && !activeMedia.dataset.storyFallback
      && Number.isFinite(activeMedia.duration)
      && activeMedia.duration > 0) {
      const fill = progressContainer.children[activeStoryIndex]?.firstElementChild;
      if (fill) fill.style.width = `${Math.min(100, activeMedia.currentTime / activeMedia.duration * 100)}%`;
      animationFrame = requestAnimationFrame(progressTick);
      return;
    }
    const elapsed = storyElapsed + now - storyStartedAt;
    const fill = progressContainer.children[activeStoryIndex]?.firstElementChild;
    if (fill) fill.style.width = `${Math.min(100, elapsed / storyDuration * 100)}%`;
    if (elapsed >= storyDuration) {
      advanceStory(1);
      return;
    }
    animationFrame = requestAnimationFrame(progressTick);
  };

  const renderStory = () => {
    const group = currentGroup();
    const story = currentStory();
    if (!group || !story) {
      closeDialog(viewer);
      return;
    }
    clearStory();
    errorMessage.classList.remove("is-complete");
    isPaused = false;
    storyElapsed = 0;
    storyStartedAt = performance.now();
    storyDuration = 6000;
    pauseButton.textContent = "Ⅱ";
    pauseButton.setAttribute("aria-label", "Pause stories");
    viewerLoading.hidden = false;
    viewerStage.querySelectorAll(".story-media").forEach((media) => media.remove());
    viewerList.hidden = true;
    viewerList.replaceChildren();
    errorMessage.hidden = true;

    viewerAvatar.replaceChildren();
    if (group.avatar_url) {
      const avatar = document.createElement("img");
      avatar.src = group.avatar_url;
      avatar.alt = "";
      viewerAvatar.append(avatar);
    } else {
      viewerAvatar.textContent = group.username.slice(0, 1).toLocaleUpperCase();
    }
    viewerName.textContent = group.is_own ? "Your Story" : `@${group.username}`;
    viewerTime.textContent = formatAge(story.created_at);
    viewerOverlay.textContent = story.overlay_text;
    viewerOverlay.hidden = !story.overlay_text;
    viewerCaption.textContent = story.caption;
    viewerCaption.hidden = !story.caption;

    const media = document.createElement(story.media_type === "video" ? "video" : "img");
    media.className = "story-media";
    media.src = story.media_url;
    if (media instanceof HTMLVideoElement) {
      media.muted = true;
      media.playsInline = true;
      media.preload = "auto";
      media.addEventListener("ended", () => advanceStory(1), { once: true });
      media.addEventListener("loadedmetadata", () => {
        viewerLoading.hidden = true;
        animationFrame = requestAnimationFrame(progressTick);
      }, { once: true });
      media.addEventListener("error", () => {
        viewerLoading.hidden = true;
        media.dataset.storyFallback = "true";
        setError("This video could not be loaded.");
        animationFrame = requestAnimationFrame(progressTick);
      }, { once: true });
      const playPromise = media.play();
      if (playPromise?.catch) playPromise.catch(() => {
        if (activeMedia === media) {
          viewerLoading.hidden = true;
          media.dataset.storyFallback = "true";
          animationFrame = requestAnimationFrame(progressTick);
        }
      });
    } else {
      media.alt = `Story by ${group.username}`;
      media.addEventListener("load", () => { viewerLoading.hidden = true; }, { once: true });
      media.addEventListener("error", () => {
        viewerLoading.hidden = true;
        setError("This photo could not be loaded.");
      }, { once: true });
    }
    activeMedia = media;
    viewerStage.prepend(media);
    renderProgress(group);
    markViewed(story);

    ownerTools.hidden = !group.is_own;
    if (group.is_own) {
      viewCount.textContent = String(story.view_count);
      deleteForm.action = story.delete_url;
      viewersButton.dataset.viewersUrl = story.viewers_url;
    }
    replyForm.action = story.reply_url;
    replyForm.hidden = group.is_own;
    if (!group.is_own) replyInput.value = "";

    if (media instanceof HTMLImageElement) {
      animationFrame = requestAnimationFrame(progressTick);
      viewerLoading.hidden = true;
    }
  };

  const openGroup = (index) => {
    if (!groups[index]) return;
    activeGroupIndex = index;
    activeStoryIndex = 0;
    if (viewer.showModal) viewer.showModal();
    else viewer.setAttribute("open", "");
    renderStory();
  };

  const advanceStory = (direction) => {
    const group = currentGroup();
    if (!group) return;
    const nextStoryIndex = activeStoryIndex + direction;
    if (nextStoryIndex >= 0 && nextStoryIndex < group.stories.length) {
      activeStoryIndex = nextStoryIndex;
      renderStory();
      return;
    }
    const nextGroupIndex = activeGroupIndex + direction;
    if (nextGroupIndex >= 0 && nextGroupIndex < groups.length) {
      activeGroupIndex = nextGroupIndex;
      activeStoryIndex = direction > 0 ? 0 : groups[nextGroupIndex].stories.length - 1;
      renderStory();
      return;
    }
    if (direction > 0) {
      if (animationFrame) cancelAnimationFrame(animationFrame);
      animationFrame = null;
      pauseMedia();
      isPaused = true;
      errorMessage.textContent = "You’re all caught up on stories.";
      errorMessage.classList.add("is-complete");
      errorMessage.hidden = false;
      endMessageTimer = window.setTimeout(() => closeDialog(viewer), 1400);
    }
    else if (direction < 0 && activeStoryIndex === 0) closeDialog(viewer);
  };

  document.querySelectorAll("[data-open-story-group]").forEach((button) => {
    button.addEventListener("click", () => openGroup(Number(button.dataset.openStoryGroup)));
  });

  viewer?.querySelector("[data-story-close]")?.addEventListener("click", () => closeDialog(viewer));
  viewer?.querySelector("[data-story-next]")?.addEventListener("click", () => advanceStory(1));
  viewer?.querySelector("[data-story-prev]")?.addEventListener("click", () => advanceStory(-1));

  pauseButton?.addEventListener("click", () => {
    isPaused = !isPaused;
    if (isPaused) {
      storyElapsed += performance.now() - storyStartedAt;
      pauseMedia();
      if (animationFrame) cancelAnimationFrame(animationFrame);
      animationFrame = null;
      pauseButton.textContent = "▶";
      pauseButton.setAttribute("aria-label", "Resume stories");
    } else {
      storyStartedAt = performance.now();
      if (activeMedia instanceof HTMLVideoElement) activeMedia.play().catch(() => {});
      animationFrame = requestAnimationFrame(progressTick);
      pauseButton.textContent = "Ⅱ";
      pauseButton.setAttribute("aria-label", "Pause stories");
    }
  });

  viewer?.addEventListener("close", clearStory);
  viewer?.addEventListener("click", (event) => {
    if (event.target === viewer) closeDialog(viewer);
  });

  document.addEventListener("keydown", (event) => {
    if (!viewer?.open) return;
    if (event.key === "ArrowRight") advanceStory(1);
    if (event.key === "ArrowLeft") advanceStory(-1);
    if (event.key === "Escape") closeDialog(viewer);
    if (event.code === "Space" && event.target.tagName !== "INPUT") {
      event.preventDefault();
      pauseButton.click();
    }
  });

  viewersButton?.addEventListener("click", async () => {
    const story = currentStory();
    if (!story) return;
    if (!viewerList.hidden) {
      viewerList.hidden = true;
      return;
    }
    viewerList.hidden = false;
    viewerList.textContent = "Loading viewers…";
    try {
      const response = await fetch(story.viewers_url, { headers: { Accept: "application/json" } });
      if (!response.ok) throw new Error(`Could not load story viewers (${response.status}).`);
      const viewers = await response.json();
      viewerList.replaceChildren();
      if (viewers.length === 0) {
        viewerList.textContent = "No views yet.";
        return;
      }
      viewers.forEach((person) => {
        const row = document.createElement("div");
        row.className = "story-viewer-person";
        const avatar = document.createElement("span");
        avatar.className = "story-viewer-avatar";
        if (person.avatar_url) {
          const image = document.createElement("img");
          image.src = person.avatar_url;
          image.alt = "";
          avatar.append(image);
        } else {
          avatar.textContent = person.username.slice(0, 1).toLocaleUpperCase();
        }
        const name = document.createElement("span");
        name.textContent = `${person.full_name} · @${person.username}`;
        row.append(avatar, name);
        viewerList.append(row);
      });
    } catch (error) {
      viewerList.textContent = "Viewers could not be loaded. Please try again.";
      console.error(error);
    }
  });

  deleteForm?.addEventListener("submit", (event) => {
    if (!window.confirm("Delete this story? This cannot be undone.")) event.preventDefault();
  });

  if (fileInput) fileInput.setAttribute("accept", "image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm,video/quicktime");
})();
