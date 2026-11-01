(() => {
  const app = document.querySelector(".messages-app");
  if (!app) return;

  const conversationSearch = app.querySelector("[data-conversation-filter]");
  const conversationItems = [...app.querySelectorAll(".conversation-item")];
  const searchEmpty = app.querySelector("[data-search-empty]");
  const noConversations = app.querySelector("[data-no-conversations]");

  if (conversationSearch) {
    conversationSearch.addEventListener("input", () => {
      const query = conversationSearch.value.trim().toLocaleLowerCase();
      let visibleCount = 0;
      if (noConversations) noConversations.hidden = query.length > 0;
      conversationItems.forEach((item) => {
        const visible = item.dataset.conversationName.includes(query);
        item.hidden = !visible;
        if (visible) visibleCount += 1;
      });
      if (searchEmpty) searchEmpty.hidden = !query || visibleCount > 0;
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "/" && !event.ctrlKey && !event.metaKey && !event.altKey) {
        const tag = document.activeElement?.tagName;
        if (tag !== "INPUT" && tag !== "TEXTAREA") {
          event.preventDefault();
          conversationSearch.focus();
        }
      }
    });
  }

  const chatScroll = document.querySelector("[data-chat-scroll]");
  if (chatScroll) chatScroll.scrollTop = chatScroll.scrollHeight;

  const input = document.querySelector("[data-message-input]");
  const sendButton = document.querySelector("[data-send-button]");
  const length = document.querySelector("[data-message-length]");
  const form = document.querySelector("[data-message-form]");
  const emojiToggle = document.querySelector("[data-emoji-toggle]");
  const emojiPicker = document.querySelector("[data-emoji-picker]");
  const attachmentInput = document.querySelector("[data-message-attachment]");

  const updateComposer = () => {
    if (!input) return;
    const value = input.value;
    if (sendButton) sendButton.disabled = value.trim().length === 0 && !attachmentInput?.files.length;
    if (length) length.textContent = `${value.length}/2000`;
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  };

  if (input) {
    updateComposer();
    input.addEventListener("input", updateComposer);
    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
        event.preventDefault();
        if (input.value.trim() && form?.requestSubmit) form.requestSubmit();
      }
    });
  }

  attachmentInput?.addEventListener("change", updateComposer);

  if (form && input) {
    form.addEventListener("submit", (event) => {
      if ((!input.value.trim() && !attachmentInput?.files.length) || input.value.length > 2000) {
        event.preventDefault();
        input.focus();
      }
    });
  }

  if (emojiToggle && emojiPicker && input) {
    emojiToggle.addEventListener("click", () => {
      emojiPicker.hidden = !emojiPicker.hidden;
    });
    emojiPicker.addEventListener("click", (event) => {
      const button = event.target.closest("[data-emoji]");
      if (!button) return;
      const start = input.selectionStart;
      const end = input.selectionEnd;
      input.setRangeText(button.dataset.emoji, start, end, "end");
      input.focus();
      emojiPicker.hidden = true;
      updateComposer();
    });
    document.addEventListener("click", (event) => {
      if (!emojiPicker.contains(event.target) && !emojiToggle.contains(event.target)) {
        emojiPicker.hidden = true;
      }
    });
  }

  const dialog = document.querySelector("[data-compose-dialog]");
  const openComposeButtons = document.querySelectorAll("[data-open-compose]");
  const peopleSearch = document.querySelector("[data-people-search]");
  const peopleResults = document.querySelector("[data-people-results]");
  const peopleStatus = document.querySelector("[data-people-status]");
  const searchUrl = app.dataset.searchUrl;
  const staticUrl = app.dataset.staticUrl;
  let searchTimer;
  let activeRequest;

  const createAvatar = (person) => {
    const avatar = document.createElement("span");
    avatar.className = "dm-avatar";
    if (person.avatar_path) {
      const image = document.createElement("img");
      image.src = `${staticUrl}${person.avatar_path}`;
      image.alt = "";
      avatar.append(image);
    } else {
      avatar.textContent = person.username.slice(0, 1).toLocaleUpperCase();
    }
    return avatar;
  };

  const searchPeople = async () => {
    const query = peopleSearch.value.trim();
    peopleResults.replaceChildren();
    if (activeRequest) activeRequest.abort();
    if (query.length < 2) {
      activeRequest = null;
      peopleStatus.textContent = "Type at least two characters to search.";
      return;
    }
    activeRequest = new AbortController();
    peopleStatus.textContent = "Searching people…";

    try {
      const response = await fetch(`${searchUrl}?q=${encodeURIComponent(query)}`, {
        headers: { Accept: "application/json" },
        signal: activeRequest.signal,
      });
      if (!response.ok) throw new Error(`People search failed (${response.status}).`);
      const people = await response.json();
      if (people.length === 0) {
        peopleStatus.textContent = "No people found. Try another name or username.";
        return;
      }
      peopleStatus.textContent = `${people.length} ${people.length === 1 ? "person" : "people"} found`;
      people.forEach((person) => {
        const link = document.createElement("a");
        link.className = "person-result";
        const conversationUrl = new URL(searchUrl, window.location.href);
        conversationUrl.pathname = conversationUrl.pathname.replace(/people\/?$/, "");
        conversationUrl.searchParams.set("user_id", person.id);
        link.href = conversationUrl.toString();
        link.append(createAvatar(person));

        const copy = document.createElement("span");
        copy.className = "person-result-copy";
        const fullName = document.createElement("strong");
        fullName.textContent = person.full_name;
        const username = document.createElement("span");
        username.textContent = `@${person.username}`;
        copy.append(fullName, username);

        const arrow = document.createElement("span");
        arrow.className = "person-result-arrow";
        arrow.setAttribute("aria-hidden", "true");
        arrow.textContent = "›";
        link.append(copy, arrow);
        peopleResults.append(link);
      });
    } catch (error) {
      if (error.name === "AbortError") return;
      peopleStatus.textContent = "People search is unavailable. Please try again.";
      console.error(error);
    }
  };

  openComposeButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!dialog) return;
      if (dialog.showModal) dialog.showModal();
      else dialog.setAttribute("open", "");
      peopleSearch?.focus();
    });
  });

  if (peopleSearch) {
    peopleSearch.addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(searchPeople, 250);
    });
    peopleSearch.addEventListener("keydown", (event) => {
      if (event.key === "Escape") dialog?.close();
    });
  }

  if (dialog) {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
    dialog.addEventListener("close", () => {
      if (activeRequest) activeRequest.abort();
      activeRequest = null;
      if (peopleSearch) peopleSearch.value = "";
      if (peopleResults) peopleResults.replaceChildren();
      if (peopleStatus) peopleStatus.textContent = "Search for a person to message.";
    });
  }

  const thread = document.querySelector(".message-thread");
  const recipientId = Number(app.dataset.recipientId);
  const currentUserId = Number(app.dataset.currentUserId);
  let lastMessageId = Number(app.dataset.lastMessageId) || 0;
  let appendMessage = () => {};
  let messagingSocket;
  if (thread && recipientId) {
    appendMessage = (message) => {
      const senderId = Number(message.sender_id);
      if (senderId !== recipientId && senderId !== currentUserId) return;
      if (Number(message.id) <= lastMessageId) return;
      lastMessageId = Number(message.id);
      const emptyState = thread.querySelector(".thread-empty");
      emptyState?.remove();

      const row = document.createElement("div");
      row.className = `message-row${senderId === currentUserId ? " is-mine" : ""}`;
      row.dataset.messageId = String(message.id);
      const content = document.createElement("div");
      content.className = "message-content";
      if (senderId !== currentUserId) {
        const avatar = document.createElement("span");
        avatar.className = "dm-avatar dm-avatar-tiny";
        avatar.textContent = message.sender_username.slice(0, 1).toLocaleUpperCase();
        row.append(avatar);
      }
      if (message.body) {
        const bubble = document.createElement("p");
        bubble.className = "message-bubble";
        bubble.textContent = message.body;
        content.append(bubble);
      }
      if (message.media_url) {
        const image = document.createElement("img");
        image.className = "message-attachment";
        image.src = message.media_url;
        image.alt = "Photo attachment";
        content.append(image);
      }
      const time = document.createElement("time");
      time.className = "message-time";
      time.textContent = message.created_at || "Just now";
      content.append(time);
      row.append(content);
      thread.append(row);
      if (chatScroll) chatScroll.scrollTop = chatScroll.scrollHeight;
    };

    const connectSocket = () => {
      if (!window.io || messagingSocket) return;
      messagingSocket = window.io("/messages");
      messagingSocket.on("new_message", appendMessage);
    };
    if (window.io) connectSocket();
    else document.querySelector("#socket-io-client")?.addEventListener("load", connectSocket, { once: true });

    const pollMessages = async () => {
      try {
        const response = await fetch(
          `/messages/${recipientId}/updates?after_id=${lastMessageId}`,
          { headers: { Accept: "application/json" } },
        );
        if (!response.ok) throw new Error(`Message refresh failed (${response.status}).`);
        const messages = await response.json();
        messages.forEach(appendMessage);
      } catch (error) {
        console.error(error);
      }
    };
    window.setInterval(pollMessages, 3000);
  }

  const callOverlay = document.querySelector("[data-call-overlay]");
  if (!callOverlay || !recipientId) return;

  const callName = callOverlay.querySelector("[data-call-name]");
  const callAvatar = callOverlay.querySelector("[data-call-avatar]");
  const callEyebrow = callOverlay.querySelector("[data-call-eyebrow]");
  const callStatus = callOverlay.querySelector("[data-call-status]");
  const callVideoStage = callOverlay.querySelector("[data-call-video-stage]");
  const remoteVideo = callOverlay.querySelector("[data-call-remote]");
  const localVideo = callOverlay.querySelector("[data-call-local]");
  const incomingActions = callOverlay.querySelector("[data-incoming-actions]");
  const activeActions = callOverlay.querySelector("[data-active-actions]");
  const outgoingActions = callOverlay.querySelector("[data-outgoing-actions]");
  const noticeActions = callOverlay.querySelector("[data-notice-actions]");
  const muteButton = callOverlay.querySelector("[data-call-mute]");
  const speakerButton = callOverlay.querySelector("[data-call-speaker]");
  const cameraButton = callOverlay.querySelector("[data-call-camera]");
  let activeCall = null;
  let noticeTimer;
  let callTimer;
  let callSocketBound = false;
  let callScreenVersion = 0;

  const setCallMode = (mode) => {
    incomingActions.hidden = mode !== "incoming";
    activeActions.hidden = mode !== "active";
    outgoingActions.hidden = mode !== "outgoing";
    noticeActions.hidden = mode !== "notice";
    callOverlay.hidden = false;
  };

  const setCallStatus = (message, isError = false) => {
    callStatus.textContent = message;
    callStatus.classList.toggle("is-error", isError);
    callStatus.setAttribute("role", isError ? "alert" : "status");
    callStatus.setAttribute("aria-live", isError ? "assertive" : "polite");
  };

  const setCallPerson = (name, avatarUrl, username = "") => {
    callName.textContent = name || username || "PIXORA user";
    callAvatar.replaceChildren();
    if (avatarUrl) {
      const image = document.createElement("img");
      image.src = avatarUrl;
      image.alt = "";
      callAvatar.append(image);
    } else {
      callAvatar.textContent = (username || name || "P").slice(0, 1).toLocaleUpperCase();
    }
  };

  const releaseCall = () => {
    window.clearTimeout(callTimer);
    callTimer = null;
    const finishedCall = activeCall;
    activeCall = null;
    if (finishedCall?.peerConnection) {
      finishedCall.peerConnection.onicecandidate = null;
      finishedCall.peerConnection.ontrack = null;
      finishedCall.peerConnection.onconnectionstatechange = null;
      finishedCall.peerConnection.close();
    }
    finishedCall?.localStream?.getTracks().forEach((track) => track.stop());
    if (remoteVideo) {
      remoteVideo.srcObject = null;
      remoteVideo.muted = false;
    }
    if (localVideo) localVideo.srcObject = null;
    if (muteButton) {
      muteButton.setAttribute("aria-pressed", "false");
      muteButton.querySelector("span").textContent = "Mute";
    }
    if (speakerButton) {
      speakerButton.setAttribute("aria-pressed", "false");
      speakerButton.querySelector("span").textContent = "Speaker";
    }
    if (cameraButton) {
      cameraButton.setAttribute("aria-pressed", "false");
      cameraButton.querySelector("span").textContent = "Camera";
    }
  };

  const showCallNotice = (message, { isError = false, duration = 2200 } = {}) => {
    releaseCall();
    window.clearTimeout(noticeTimer);
    callScreenVersion += 1;
    callVideoStage.hidden = true;
    setCallMode("notice");
    setCallStatus(message, isError);
    const version = callScreenVersion;
    noticeTimer = window.setTimeout(() => {
      if (version === callScreenVersion && !activeCall) callOverlay.hidden = true;
    }, duration);
  };

  const setCallMediaMode = (type) => {
    callEyebrow.textContent = type === "video" ? "PIXORA VIDEO CALL" : "PIXORA VOICE CALL";
    callVideoStage.hidden = type !== "video";
    cameraButton.hidden = type !== "video";
  };

  const acquireLocalMedia = async (call) => {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: true,
      video: call.type === "video",
    });
    if (activeCall !== call) {
      stream.getTracks().forEach((track) => track.stop());
      return false;
    }
    call.localStream = stream;
    if (call.type === "video") localVideo.srcObject = stream;
    return true;
  };

  const mediaErrorMessage = (error, type) => {
    if (error.name === "NotAllowedError" || error.name === "PermissionDeniedError") {
      return "Allow microphone and camera access in your browser to continue.";
    }
    if (error.name === "NotFoundError" || error.name === "DevicesNotFoundError") {
      return type === "video"
        ? "A microphone or camera could not be found on this device."
        : "A microphone could not be found on this device.";
    }
    return "Your microphone or camera could not be started. Please try again.";
  };

  const formatCallDuration = (milliseconds) => {
    const seconds = Math.floor(milliseconds / 1000);
    return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
  };

  const startCallTimer = (call) => {
    call.connectedAt = Date.now();
    const update = () => {
      if (activeCall === call && call.connectedAt) {
        setCallStatus(`In call · ${formatCallDuration(Date.now() - call.connectedAt)}`);
      }
    };
    update();
    callTimer = window.setInterval(update, 1000);
  };

  const sendCallEvent = (eventName, call, extra = {}) => {
    if (!messagingSocket || !call) return false;
    messagingSocket.emit(eventName, { call_id: call.id, ...extra });
    return true;
  };

  const createPeerConnection = (call) => {
    if (call.peerConnection) return call.peerConnection;
    const peerConnection = new RTCPeerConnection({
      iceServers: [
        { urls: "stun:stun.l.google.com:19302" },
        { urls: "stun:stun1.l.google.com:19302" },
      ],
    });
    call.peerConnection = peerConnection;
    call.localStream.getTracks().forEach((track) => peerConnection.addTrack(track, call.localStream));
    peerConnection.onicecandidate = (event) => {
      if (event.candidate && activeCall === call) {
        sendCallEvent("call:ice", call, { signal: event.candidate.toJSON() });
      }
    };
    peerConnection.ontrack = (event) => {
      if (activeCall !== call) return;
      remoteVideo.srcObject = event.streams[0] || new MediaStream([event.track]);
      remoteVideo.play().catch((error) => {
        console.warn("Remote call audio could not start automatically.", error);
        setCallStatus("Connected · tap the video to enable sound");
      });
    };
    peerConnection.onconnectionstatechange = () => {
      if (activeCall !== call) return;
      if (peerConnection.connectionState === "connected") {
        startCallTimer(call);
      } else if (peerConnection.connectionState === "disconnected") {
        setCallStatus("Reconnecting…");
      } else if (peerConnection.connectionState === "failed") {
        sendCallEvent("call:end", call);
        showCallNotice("The connection was lost.", { isError: true });
      }
    };
    return peerConnection;
  };

  const flushIceCandidates = async (call) => {
    if (!call.peerConnection?.remoteDescription) return;
    const pending = call.pendingIce.splice(0);
    for (const candidate of pending) {
      await call.peerConnection.addIceCandidate(candidate);
    }
  };

  const acceptIncomingCall = async () => {
    const call = activeCall;
    if (!call || call.role !== "callee" || call.status !== "ringing") return;
    call.status = "connecting";
    setCallMode("active");
    setCallStatus("Connecting…");
    try {
      if (!(await acquireLocalMedia(call))) return;
      createPeerConnection(call);
      sendCallEvent("call:accept", call);
    } catch (error) {
      console.error("Could not access call media.", error);
      sendCallEvent("call:reject", call);
      showCallNotice(mediaErrorMessage(error, call.type), { isError: true, duration: 5000 });
    }
  };

  const startCall = async (type) => {
    if (activeCall) return;
    window.clearTimeout(noticeTimer);
    if (!window.isSecureContext && !["localhost", "127.0.0.1"].includes(window.location.hostname)) {
      showCallNotice("Calls require a secure HTTPS connection.", { isError: true, duration: 5000 });
      return;
    }
    if (!messagingSocket || !window.RTCPeerConnection || !navigator.mediaDevices?.getUserMedia) {
      showCallNotice("Calls are unavailable in this browser right now.", { isError: true, duration: 5000 });
      return;
    }
    const callId = window.crypto?.randomUUID
      ? window.crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2, 14)}`;
    const call = {
      id: callId,
      type,
      role: "caller",
      status: "preparing",
      peerId: recipientId,
      peerName: callName.textContent,
      peerAvatarUrl: callAvatar.querySelector("img")?.src || "",
      pendingIce: [],
    };
    activeCall = call;
    callScreenVersion += 1;
    setCallPerson(call.peerName, call.peerAvatarUrl);
    setCallMediaMode(type);
    setCallMode("outgoing");
    setCallStatus("Preparing your microphone…");
    try {
      if (!(await acquireLocalMedia(call))) return;
      call.status = "ringing";
      setCallStatus("Calling…");
      sendCallEvent("call:invite", call, { to_user_id: recipientId, call_type: type });
      callTimer = window.setTimeout(() => {
        if (activeCall !== call || call.status !== "ringing") return;
        sendCallEvent("call:cancel", call);
        showCallNotice("No answer. Try again later.");
      }, 45_000);
    } catch (error) {
      console.error("Could not start call.", error);
      showCallNotice(mediaErrorMessage(error, type), { isError: true, duration: 5000 });
    }
  };

  const cancelOrEndCall = () => {
    const call = activeCall;
    if (!call) return;
    sendCallEvent(call.status === "ringing" ? "call:cancel" : "call:end", call);
    showCallNotice("Call ended.");
  };

  callOverlay.querySelectorAll("[data-start-call]").forEach((button) => {
    button.addEventListener("click", () => startCall(button.dataset.startCall));
  });
  callOverlay.querySelector("[data-call-accept]").addEventListener("click", acceptIncomingCall);
  callOverlay.querySelector("[data-call-reject]").addEventListener("click", () => {
    const call = activeCall;
    if (!call) return;
    sendCallEvent("call:reject", call);
    showCallNotice("Call declined.");
  });
  callOverlay.querySelector("[data-call-cancel]").addEventListener("click", cancelOrEndCall);
  callOverlay.querySelector("[data-call-end]").addEventListener("click", cancelOrEndCall);
  callOverlay.querySelector("[data-call-close]").addEventListener("click", () => {
    window.clearTimeout(noticeTimer);
    callOverlay.hidden = true;
  });
  muteButton.addEventListener("click", () => {
    if (!activeCall?.localStream) return;
    const muted = muteButton.getAttribute("aria-pressed") !== "true";
    activeCall.localStream.getAudioTracks().forEach((track) => { track.enabled = !muted; });
    muteButton.setAttribute("aria-pressed", String(muted));
    muteButton.setAttribute("aria-label", muted ? "Unmute microphone" : "Mute microphone");
    muteButton.querySelector("span").textContent = muted ? "Unmute" : "Mute";
  });
  speakerButton.addEventListener("click", () => {
    const muted = speakerButton.getAttribute("aria-pressed") !== "true";
    remoteVideo.muted = muted;
    speakerButton.setAttribute("aria-pressed", String(muted));
    speakerButton.setAttribute("aria-label", muted ? "Unmute speaker" : "Mute speaker");
    speakerButton.querySelector("span").textContent = muted ? "Muted" : "Speaker";
  });
  cameraButton.addEventListener("click", () => {
    if (!activeCall?.localStream) return;
    const cameraOff = cameraButton.getAttribute("aria-pressed") !== "true";
    activeCall.localStream.getVideoTracks().forEach((track) => { track.enabled = !cameraOff; });
    cameraButton.setAttribute("aria-pressed", String(cameraOff));
    cameraButton.setAttribute("aria-label", cameraOff ? "Turn camera on" : "Turn camera off");
    cameraButton.querySelector("span").textContent = cameraOff ? "Camera off" : "Camera";
  });
  callOverlay.addEventListener("click", () => {
    if (activeCall && remoteVideo.srcObject) {
      remoteVideo.play().catch((error) => console.warn("Call audio is still blocked.", error));
    }
  });

  const bindCallSocket = (socket) => {
    if (callSocketBound) return;
    callSocketBound = true;
    socket.on("call:incoming", (data) => {
      if (activeCall || !data?.call_id || !["audio", "video"].includes(data.call_type)) {
        if (data?.call_id) socket.emit("call:reject", { call_id: data.call_id });
        return;
      }
      window.clearTimeout(noticeTimer);
      const call = {
        id: data.call_id,
        type: data.call_type,
        role: "callee",
        status: "ringing",
        peerId: Number(data.from_user_id),
        peerName: data.from_name,
        peerAvatarUrl: data.from_avatar_url,
        pendingIce: [],
      };
      activeCall = call;
      callScreenVersion += 1;
      setCallPerson(call.peerName, call.peerAvatarUrl, data.from_username);
      setCallMediaMode(call.type);
      setCallMode("incoming");
      setCallStatus(`Incoming ${call.type} call…`);
      callOverlay.querySelector("[data-call-accept]").focus();
    });
    socket.on("call:accepted", async (data) => {
      const call = activeCall;
      if (!call || call.id !== data?.call_id || call.role !== "caller") return;
      call.status = "connecting";
      setCallMode("active");
      setCallStatus("Connecting…");
      try {
        const peerConnection = createPeerConnection(call);
        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        sendCallEvent("call:offer", call, { signal: peerConnection.localDescription.toJSON() });
      } catch (error) {
        console.error("Could not create a WebRTC offer.", error);
        sendCallEvent("call:end", call);
        showCallNotice("The call could not be connected.", { isError: true });
      }
    });
    socket.on("call:offer", async (data) => {
      const call = activeCall;
      if (!call || call.id !== data?.call_id || call.role !== "callee" || !data.signal) return;
      try {
        const peerConnection = createPeerConnection(call);
        await peerConnection.setRemoteDescription(data.signal);
        await flushIceCandidates(call);
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        sendCallEvent("call:answer", call, { signal: peerConnection.localDescription.toJSON() });
      } catch (error) {
        console.error("Could not accept the WebRTC offer.", error);
        sendCallEvent("call:end", call);
        showCallNotice("The call could not be connected.", { isError: true });
      }
    });
    socket.on("call:answer", async (data) => {
      const call = activeCall;
      if (!call || call.id !== data?.call_id || call.role !== "caller" || !data.signal) return;
      try {
        await call.peerConnection.setRemoteDescription(data.signal);
        await flushIceCandidates(call);
      } catch (error) {
        console.error("Could not apply the WebRTC answer.", error);
        sendCallEvent("call:end", call);
        showCallNotice("The call could not be connected.", { isError: true });
      }
    });
    socket.on("call:ice", async (data) => {
      const call = activeCall;
      if (!call || call.id !== data?.call_id || !data.signal || !call.peerConnection) return;
      try {
        if (call.peerConnection.remoteDescription) {
          await call.peerConnection.addIceCandidate(data.signal);
        } else {
          call.pendingIce.push(data.signal);
        }
      } catch (error) {
        console.error("Could not add a WebRTC ICE candidate.", error);
      }
    });
    socket.on("call:rejected", (data) => {
      if (activeCall?.id === data?.call_id) showCallNotice("Call declined.");
    });
    socket.on("call:taken", (data) => {
      if (activeCall?.id === data?.call_id && activeCall.role === "callee") {
        showCallNotice("Answered on another device.");
      }
    });
    socket.on("call:busy", (data) => {
      if (activeCall?.id === data?.call_id) showCallNotice("This person is already on another call.");
    });
    socket.on("call:unavailable", (data) => {
      if (activeCall?.id === data?.call_id) showCallNotice("This person is offline right now.");
    });
    socket.on("call:ended", (data) => {
      if (!activeCall || activeCall.id !== data?.call_id) return;
      const message = data.reason === "canceled" ? "Call canceled." : "Call ended.";
      showCallNotice(message);
    });
    socket.on("call:error", (data) => {
      if (activeCall && activeCall.id === data?.call_id) {
        showCallNotice(data.message || "The call could not be completed.", { isError: true, duration: 5000 });
      }
    });
    socket.on("disconnect", () => {
      if (activeCall) showCallNotice("Call connection lost.", { isError: true, duration: 5000 });
    });
  };

  if (messagingSocket) bindCallSocket(messagingSocket);
  else {
    const socketScript = document.querySelector("#socket-io-client");
    socketScript?.addEventListener("load", () => {
      if (!messagingSocket && window.io) {
        messagingSocket = window.io("/messages");
        messagingSocket.on("new_message", appendMessage);
      }
      if (messagingSocket) bindCallSocket(messagingSocket);
    }, { once: true });
  }
})();
