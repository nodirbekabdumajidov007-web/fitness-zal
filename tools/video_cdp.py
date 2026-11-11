"""Tiny Chrome DevTools Protocol driver for tools/make_videos.py (stdlib + websockets only).

Launches a headless Chrome/Edge with its own throwaway profile, opens one tab and offers the few calls the video capture needs:
navigate, eval JS, click/type like a user, set the viewport, take PNG screenshots (viewport or full page)."""
import base64
import json
import os
import shutil
import subprocess
import tempfile
import time
import urllib.request

from websockets.sync.client import connect

BROWSERS = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]


class Browser:
    def __init__(self, port=9333):
        exe = next(p for p in BROWSERS if os.path.exists(p))
        self.profile = tempfile.mkdtemp(prefix="fzv-profile-")
        self.proc = subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={self.profile}",
                                      "--no-first-run", "--no-default-browser-check", "--disable-extensions", "--hide-scrollbars",
                                      "--force-color-profile=srgb", "--disable-features=Translate,MediaRouter", "--mute-audio",
                                      "--window-size=1440,900", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        base = f"http://127.0.0.1:{port}"
        for _ in range(100):
            try:
                tabs = json.load(urllib.request.urlopen(base + "/json/list", timeout=1))
                page = next(t for t in tabs if t.get("type") == "page")
                break
            except Exception:
                time.sleep(0.15)
        else:
            raise RuntimeError("browser did not start")
        self.ws = connect(page["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024, open_timeout=10)
        self.seq = 0
        self.events = []
        for dom in ("Page", "Runtime", "Network"):
            self.send(dom + ".enable")

    # ---------- protocol ----------
    def send(self, method, params=None, timeout=60):
        self.seq += 1
        mid = self.seq
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            msg = json.loads(self.ws.recv(timeout=max(0.1, end - time.time())))
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            if "method" in msg:
                self.events.append(msg)
        raise TimeoutError(method)

    def wait_event(self, name, timeout=20):
        end = time.time() + timeout
        while time.time() < end:
            for i, e in enumerate(self.events):
                if e["method"] == name:
                    del self.events[: i + 1]
                    return e
            try:
                msg = json.loads(self.ws.recv(timeout=0.5))
            except TimeoutError:
                continue
            if "method" in msg:
                self.events.append(msg)
        return None

    # ---------- helpers ----------
    def viewport(self, w, h, dpr=1, mobile=False):
        self.send("Emulation.setDeviceMetricsOverride", {"width": w, "height": h, "deviceScaleFactor": dpr, "mobile": mobile,
                                                          "screenWidth": w, "screenHeight": h})
        self.send("Emulation.setTouchEmulationEnabled", {"enabled": mobile, "maxTouchPoints": 5} if mobile else {"enabled": False})
        ua = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36"
              if mobile else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36")
        self.send("Emulation.setUserAgentOverride", {"userAgent": ua})

    def color_scheme(self, scheme):
        self.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-color-scheme", "value": scheme},
                                                              {"name": "prefers-reduced-motion", "value": "no-preference"}]})

    def go(self, url, settle=1.2):
        self.events.clear()
        self.send("Page.navigate", {"url": url})
        self.wait_event("Page.loadEventFired", 25)
        self.idle(settle)

    def idle(self, sec):
        end = time.time() + sec
        while time.time() < end:
            try:
                msg = json.loads(self.ws.recv(timeout=max(0.05, end - time.time())))
                if "method" in msg:
                    self.events.append(msg)
            except TimeoutError:
                pass
        self.events = self.events[-200:]

    def js(self, expr, await_promise=True):
        r = self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_promise})
        if r.get("exceptionDetails"):
            raise RuntimeError(f"JS error: {r['exceptionDetails'].get('exception', {}).get('description', r['exceptionDetails'])}")
        return r.get("result", {}).get("value")

    def rect(self, selector):
        return self.js(f"""(() => {{ const e = document.querySelector({json.dumps(selector)}); if (!e) return null;
            e.scrollIntoView({{block: 'center', behavior: 'instant'}}); const r = e.getBoundingClientRect();
            return {{x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height}}; }})()""")

    def click_xy(self, x, y):
        for t in ("mouseMoved", "mousePressed", "mouseReleased"):
            self.send("Input.dispatchMouseEvent", {"type": t, "x": x, "y": y, "button": "left", "clickCount": 1})

    def click(self, selector, settle=0.6):
        r = self.rect(selector)
        if not r:
            raise RuntimeError("no element " + selector)
        self.idle(0.15)
        r = self.js(f"""(() => {{ const r = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
            return {{x: r.x + r.width / 2, y: r.y + r.height / 2}}; }})()""")
        self.click_xy(r["x"], r["y"])
        self.idle(settle)
        return r

    def type_text(self, text):
        for ch in text:
            self.send("Input.insertText", {"text": ch})

    def key(self, key, code=None, vk=None):
        p = {"key": key, "code": code or key, "windowsVirtualKeyCode": vk or 0}
        self.send("Input.dispatchKeyEvent", {"type": "keyDown", **p, **({"text": "\r"} if key == "Enter" else {})})
        self.send("Input.dispatchKeyEvent", {"type": "keyUp", **p})

    def shot(self, path, full=False, clip=None):
        params = {"format": "png", "captureBeyondViewport": bool(full)}
        if full:
            m = self.send("Page.getLayoutMetrics")
            cs = m.get("cssContentSize") or m["contentSize"]
            params["clip"] = {"x": 0, "y": 0, "width": cs["width"], "height": cs["height"], "scale": 1}
        elif clip:
            params["clip"] = {**clip, "scale": 1}
        data = self.send("Page.captureScreenshot", params, timeout=120)["data"]
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        return path

    def close(self):
        try:
            self.send("Browser.close", timeout=5)
        except Exception:
            pass
        try:
            self.ws.close()
        except Exception:
            pass
        try:
            self.proc.wait(5)
        except Exception:
            self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)
