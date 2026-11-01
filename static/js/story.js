document.querySelectorAll(".story-card video").forEach((video) => {
  video.addEventListener("ended", () => video.currentTime = 0);
});
