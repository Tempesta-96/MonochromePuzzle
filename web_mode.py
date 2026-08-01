import json
import os
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pygame

from game import Game


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MonochromePuzzle</title>
  <style>
    :root { font-family: Georgia, serif; color-scheme: light; }
    * { box-sizing: border-box; }
    body { margin: 0; background: #f4efe5; color: #1f1c18; }
    .page {
      width: min(100vw, 1500px);
      margin: 0 auto;
      padding: 16px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }
    h1 { margin: 0; font-size: clamp(24px, 4vw, 30px); }
    .toolbar { display: flex; flex-wrap: wrap; gap: 10px; }
    button {
      border: 0;
      border-radius: 10px;
      padding: 10px 14px;
      background: #1f1c18;
      color: #fff;
      font: inherit;
      cursor: pointer;
    }
    button.alt { background: #72695b; }
    .viewport {
      border: 1px solid #cabfab;
      border-radius: 16px;
      overflow: hidden;
      background: #ddd4c6;
      box-shadow: 0 16px 40px rgba(0, 0, 0, 0.12);
      flex: 1;
      min-height: 320px;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 8px;
    }
    #game {
      display: block;
      width: auto;
      height: auto;
      max-width: 100%;
      max-height: calc(100vh - 190px);
      user-select: none;
      cursor: grab;
    }
    #game.dragging { cursor: grabbing; }
    .note { margin-top: 12px; color: #5f564b; font-size: 14px; }
    .status { margin-top: 8px; color: #7a2418; font-size: 13px; min-height: 18px; }
    @media (max-width: 720px) {
      .page { padding: 12px; }
      .viewport { padding: 4px; min-height: 220px; }
      #game { max-height: calc(100vh - 220px); }
    }
  </style>
</head>
<body>
  <div class="page">
    <h1>MonochromePuzzle</h1>
    <div class="toolbar">
      <button data-key="ArrowLeft">Prev</button>
      <button data-key="ArrowRight">Next</button>
      <button class="alt" data-key="r">Reset</button>
      <button class="alt" data-key="s">Solution</button>
      <button class="alt" data-key="Escape">Close Overlay</button>
    </div>
    <div class="viewport">
      <img id="game" alt="MonochromePuzzle board" draggable="false">
    </div>
    <div class="note">Drag pieces directly on the board. Keyboard shortcuts also work when the page is focused.</div>
    <div class="status" id="status"></div>
  </div>
  <script>
    const img = document.getElementById("game");
    const status = document.getElementById("status");
    let dragging = false;
    let frameUrl = null;
    let fetchInFlight = false;

    async function postJson(path, body) {
      await fetch(path, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body)
      });
    }

    let refreshTimer = null;

    function queueRefresh(delay = 120) {
      clearTimeout(refreshTimer);
      refreshTimer = setTimeout(refresh, delay);
    }

    async function refresh() {
      if (fetchInFlight) {
        return;
      }
      fetchInFlight = true;
      try {
        const response = await fetch("/frame.png?ts=" + Date.now(), { cache: "no-store" });
        if (!response.ok) {
          throw new Error("Frame request failed with status " + response.status);
        }
        const blob = await response.blob();
        const nextUrl = URL.createObjectURL(blob);
        if (frameUrl) {
          URL.revokeObjectURL(frameUrl);
        }
        frameUrl = nextUrl;
        img.src = frameUrl;
        status.textContent = "";
      } catch (error) {
        status.textContent = "Unable to load board image: " + error.message;
      } finally {
        fetchInFlight = false;
      }
    }

    function getPoint(event) {
      const rect = img.getBoundingClientRect();
      const scaleX = img.naturalWidth / rect.width;
      const scaleY = img.naturalHeight / rect.height;
      return {
        x: Math.round((event.clientX - rect.left) * scaleX),
        y: Math.round((event.clientY - rect.top) * scaleY)
      };
    }

    document.querySelectorAll("button[data-key]").forEach((button) => {
      button.addEventListener("click", async () => {
        await postJson("/key", { key: button.dataset.key });
        queueRefresh(20);
      });
    });

    img.addEventListener("mousedown", async (event) => {
      event.preventDefault();
      dragging = true;
      img.classList.add("dragging");
      await postJson("/mouse", { action: "down", ...getPoint(event) });
      queueRefresh(20);
    });

    img.addEventListener("dragstart", (event) => {
      event.preventDefault();
    });

    window.addEventListener("mousemove", async (event) => {
      if (!dragging) {
        return;
      }
      await postJson("/mouse", { action: "move", ...getPoint(event) });
      queueRefresh(20);
    });

    window.addEventListener("mouseup", async (event) => {
      if (!dragging) {
        return;
      }
      dragging = false;
      img.classList.remove("dragging");
      await postJson("/mouse", { action: "up", ...getPoint(event) });
      queueRefresh(20);
    });

    window.addEventListener("keydown", async (event) => {
      const allowed = ["ArrowLeft", "ArrowRight", "Escape", "r", "s", "R", "S"];
      if (!allowed.includes(event.key)) {
        return;
      }
      event.preventDefault();
      await postJson("/key", { key: event.key });
      queueRefresh(20);
    });

    img.addEventListener("load", () => queueRefresh(120));
    img.addEventListener("error", () => queueRefresh(400));
    refresh();
  </script>
</body>
</html>
"""


KEY_MAP = {
    "ArrowLeft": pygame.K_LEFT,
    "ArrowRight": pygame.K_RIGHT,
    "Escape": pygame.K_ESCAPE,
    "r": pygame.K_r,
    "R": pygame.K_r,
    "s": pygame.K_s,
    "S": pygame.K_s,
}


class LocalhostGameServer:
    def __init__(self, host: str, port: int, level: int):
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        self.host = host
        self.port = port
        self.lock = threading.Lock()
        self.game = Game()
        self.game.current_level = max(0, min(100, level))
        self.game.load_level(self.game.current_level)

    def run(self):
        with self.lock:
            self.game.draw()

        outer = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/" or self.path.startswith("/?"):
                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(HTML.encode("utf-8"))
                    return
                if self.path.startswith("/frame.png"):
                    outer.serve_frame(self)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self):
                if self.path == "/mouse":
                    outer.handle_mouse(self)
                    return
                if self.path == "/key":
                    outer.handle_key(self)
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def log_message(self, format, *args):
                return

        server = ThreadingHTTPServer((self.host, self.port), Handler)
        stop_event = threading.Event()
        watcher = threading.Thread(
            target=self._watch_terminal_escape,
            args=(server, stop_event),
            daemon=True,
        )
        watcher.start()
        print(f"MonochromePuzzle web mode running at http://{self.host}:{self.port}")
        print("Press Esc in this terminal or Ctrl+C to stop the localhost server.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
            server.shutdown()
            server.server_close()

    def _watch_terminal_escape(self, server, stop_event):
        try:
            import msvcrt
        except ImportError:
            return

        while not stop_event.is_set():
            if not msvcrt.kbhit():
                time.sleep(0.05)
                continue
            key = msvcrt.getwch()
            if key == "\x1b":
                print("\nEscape pressed. Stopping localhost server...")
                stop_event.set()
                server.shutdown()
                return

    def _read_json(self, handler):
        length = int(handler.headers.get("Content-Length", "0"))
        payload = handler.rfile.read(length)
        return json.loads(payload.decode("utf-8"))

    def _respond_empty(self, handler):
        handler.send_response(HTTPStatus.NO_CONTENT)
        handler.end_headers()

    def serve_frame(self, handler):
        with self.lock:
            self.game.step()
            frame = self.game.frame_bytes()
        handler.send_response(HTTPStatus.OK)
        handler.send_header("Content-Type", "image/png")
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("Content-Length", str(len(frame)))
        handler.end_headers()
        try:
            handler.wfile.write(frame)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError, socket.error):
            return

    def handle_mouse(self, handler):
        payload = self._read_json(handler)
        event_type = {
            "down": pygame.MOUSEBUTTONDOWN,
            "move": pygame.MOUSEMOTION,
            "up": pygame.MOUSEBUTTONUP,
        }[payload["action"]]
        kwargs = {"pos": (int(payload["x"]), int(payload["y"]))}
        if event_type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            kwargs["button"] = 1
        if event_type == pygame.MOUSEMOTION:
            kwargs["rel"] = (0, 0)
            kwargs["buttons"] = (1, 0, 0)
        event = pygame.event.Event(event_type, **kwargs)
        with self.lock:
            self.game.process_event(event)
            self.game.draw()
        self._respond_empty(handler)

    def handle_key(self, handler):
        payload = self._read_json(handler)
        key = KEY_MAP.get(payload["key"])
        if key is None:
            handler.send_error(HTTPStatus.BAD_REQUEST, "Unsupported key")
            return
        event = pygame.event.Event(pygame.KEYDOWN, key=key)
        with self.lock:
            self.game.process_event(event)
            self.game.draw()
        self._respond_empty(handler)
