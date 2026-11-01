(() => {
  const createSocket = (namespace) => {
    const listeners = new Map();
    const pendingEvents = [];
    let websocket;
    let reconnectTimer;
    let handshakeTimer;
    let reconnectDelay = 500;
    let manuallyClosed = false;
    let connected = false;
    let engineOpened = false;
    let namespaceConnected = false;

    const socket = {
      connected: false,
      on(eventName, listener) {
        if (!listeners.has(eventName)) listeners.set(eventName, new Set());
        listeners.get(eventName).add(listener);
        return socket;
      },
      emit(eventName, ...args) {
        if (typeof eventName !== "string") return socket;
        const packet = `42${namespace},${JSON.stringify([eventName, ...args])}`;
        if (namespaceConnected && websocket?.readyState === WebSocket.OPEN) {
          websocket.send(packet);
        } else if (!manuallyClosed) {
          pendingEvents.push(packet);
        }
        return socket;
      },
      disconnect() {
        manuallyClosed = true;
        window.clearTimeout(reconnectTimer);
        window.clearTimeout(handshakeTimer);
        pendingEvents.length = 0;
        if (websocket && websocket.readyState < WebSocket.CLOSING) websocket.close();
        return socket;
      },
    };

    const dispatch = (eventName, ...args) => {
      listeners.get(eventName)?.forEach((listener) => {
        try {
          listener(...args);
        } catch (error) {
          console.error(`Socket.IO ${eventName} handler failed.`, error);
        }
      });
    };

    const closeConnection = (reason) => {
      window.clearTimeout(handshakeTimer);
      if (namespaceConnected) dispatch("disconnect", reason);
      connected = false;
      namespaceConnected = false;
      socket.connected = false;
      engineOpened = false;
      if (manuallyClosed) return;
      window.clearTimeout(reconnectTimer);
      reconnectTimer = window.setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 2, 10_000);
    };

    const sendNamespaceConnect = () => {
      if (namespaceConnected || !engineOpened || websocket?.readyState !== WebSocket.OPEN) return;
      websocket.send(`40${namespace},`);
    };

    const parseSocketPacket = (packet) => {
      if (!packet.startsWith("4")) return;
      const message = packet.slice(1);
      const type = message.charAt(0);
      if (type === "0") {
        namespaceConnected = true;
        connected = true;
        socket.connected = true;
        reconnectDelay = 500;
        pendingEvents.splice(0).forEach((event) => {
          if (websocket?.readyState === WebSocket.OPEN) websocket.send(event);
        });
        dispatch("connect");
        return;
      }
      if (type !== "2") return;
      const separator = message.indexOf(",");
      const packetNamespace = separator >= 0 ? message.slice(1, separator) : "/";
      if (packetNamespace !== namespace || separator < 0) return;
      try {
        const [eventName, ...args] = JSON.parse(message.slice(separator + 1));
        if (typeof eventName === "string") dispatch(eventName, ...args);
      } catch (error) {
        console.error("Could not decode a Socket.IO message.", error);
      }
    };

    function connect() {
      if (manuallyClosed || websocket?.readyState === WebSocket.CONNECTING) return;
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const url = `${protocol}//${window.location.host}/socket.io/?EIO=4&transport=websocket`;
      engineOpened = false;
      namespaceConnected = false;
      websocket = new WebSocket(url);

      handshakeTimer = window.setTimeout(() => {
        if (!engineOpened && websocket?.readyState === WebSocket.OPEN) {
          websocket.close();
        }
      }, 10_000);

      websocket.addEventListener("open", () => {
        handshakeTimer = window.setTimeout(() => {
          if (!namespaceConnected) websocket?.close();
        }, 10_000);
      });
      websocket.addEventListener("message", (event) => {
        if (typeof event.data !== "string") return;
        if (event.data.startsWith("0")) {
          engineOpened = true;
          window.clearTimeout(handshakeTimer);
          sendNamespaceConnect();
          return;
        }
        if (event.data.startsWith("2")) {
          websocket?.send(`3${event.data.slice(1)}`);
          return;
        }
        if (event.data.startsWith("1")) {
          websocket?.close();
          return;
        }
        if (event.data.startsWith("4")) parseSocketPacket(event.data);
      });
      websocket.addEventListener("error", () => {
        if (!connected) dispatch("connect_error", new Error("Could not connect to the messaging server."));
      });
      websocket.addEventListener("close", () => closeConnection("transport close"));
    }

    connect();
    return socket;
  };

  window.io = (namespace = "/") => createSocket(namespace);
})();
