(() => {
  const input = document.querySelector("[data-post-media]");
  const preview = document.querySelector("[data-post-preview]");
  if (!input || !preview) return;

  let objectUrl;
  input.addEventListener("change", () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl);
    preview.replaceChildren();
    const file = input.files?.[0];
    if (!file) {
      preview.hidden = true;
      return;
    }

    objectUrl = URL.createObjectURL(file);
    const media = document.createElement(file.type.startsWith("video/") ? "video" : "img");
    media.src = objectUrl;
    media.alt = file.type.startsWith("video/") ? "Selected video preview" : "Selected photo preview";
    if (media instanceof HTMLVideoElement) {
      media.controls = true;
      media.playsInline = true;
    }
    preview.append(media);
    preview.hidden = false;
  });
})();
