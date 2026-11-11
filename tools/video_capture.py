"""Records the real site (temporary demo server) into JPEG frame sequences for tools/make_videos.py.

Every scene is a list of frame files at 30 fps plus "taps" (where a finger/cursor touched, for the ripple drawn later).
Scrolling and typing are captured frame by frame (deterministic, smooth); "live" moments are captured in real time."""
import json
import math
import os
import time

from video_cdp import Browser

FPS = 30


def ease(t):
    return 4 * t * t * t if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


class Rec:
    def __init__(self, b, root, scale):
        self.b, self.root, self.scale = b, root, scale
        self.scenes, self.cur = {}, None
        self.n = 0

    def scene(self, name):
        self.cur = {"frames": [], "taps": [], "marks": {}}
        self.scenes[name] = self.cur
        os.makedirs(os.path.join(self.root, name), exist_ok=True)
        self.dir = os.path.join(self.root, name)

    def snap(self):
        self.n += 1
        p = os.path.join(self.dir, f"{self.n:05d}.jpg")
        import base64
        data = self.b.send("Page.captureScreenshot", {"format": "jpeg", "quality": 90}, timeout=60)["data"]
        with open(p, "wb") as f:
            f.write(base64.b64decode(data))
        return os.path.relpath(p, self.root)

    def mark(self, key):
        self.cur["marks"][key] = len(self.cur["frames"])

    def hold(self, sec):
        p = self.snap()
        self.cur["frames"] += [p] * max(1, round(sec * FPS))

    def live(self, sec):
        """Real-time capture: screenshots as fast as possible, each repeated to keep 30 fps wall-clock timing."""
        frames, base, t0 = self.cur["frames"], len(self.cur["frames"]), time.time()
        while True:
            el = time.time() - t0
            p = self.snap()
            add = round(min(el, sec) * FPS) - (len(frames) - base)
            if add > 0:
                frames += [p] * add
            if el >= sec:
                break

    def scroll_y(self):
        return self.b.js("window.scrollY")

    def scroll(self, to, sec, el=None):
        """Smoothly scroll the window (or an element) to `to` px over `sec` seconds, one screenshot per frame."""
        target = f"document.querySelector({json.dumps(el)})" if el else "document.scrollingElement"
        y0 = self.b.js(f"{target}.scrollTop")
        if isinstance(to, str):  # a selector: bring it near the top third
            to = self.b.js(f"""(() => {{ const e = document.querySelector({json.dumps(to)});
                return e ? Math.max(0, e.getBoundingClientRect().top + window.scrollY - innerHeight * 0.18) : {y0}; }})()""")
        n = max(1, round(sec * FPS))
        for i in range(1, n + 1):
            y = y0 + (to - y0) * ease(i / n)
            self.b.js(f"{target}.scrollTo(0, {y:.1f})", await_promise=False)
            self.cur["frames"].append(self.snap())

    def tap(self, selector=None, js_find=None, settle=0.5, frames_after=0):
        """Click like a user and remember where (CSS px of the viewport) for the ripple."""
        b = self.b
        find = js_find or f"document.querySelector({json.dumps(selector)})"
        r = b.js(f"""(() => {{ const e = {find}; if (!e) return null; const r0 = e.getBoundingClientRect();
            if (r0.top < 70 || r0.bottom > innerHeight - 70) e.scrollIntoView({{block: 'center', behavior: 'instant'}});
            const r = e.getBoundingClientRect(); return {{x: r.x + r.width / 2, y: r.y + r.height / 2}}; }})()""")
        if not r:
            raise RuntimeError(f"tap target not found: {selector or js_find}")
        self.hold(0.25)
        self.cur["taps"].append({"f": len(self.cur["frames"]), "x": r["x"] * self.scale, "y": r["y"] * self.scale})
        b.click_xy(r["x"], r["y"])
        b.idle(settle)
        if frames_after:
            self.hold(frames_after / FPS)

    def type(self, text, per_char=3):
        for ch in text:
            self.b.send("Input.insertText", {"text": ch})
            self.b.idle(0.02)
            p = self.snap()
            self.cur["frames"] += [p] * per_char

    def done(self):
        with open(os.path.join(self.root, "scenes.json"), "w", encoding="utf-8") as f:
            json.dump(self.scenes, f)


def login(b, base, user, pw, rec=None):
    b.send("Network.clearBrowserCookies")
    b.go(base + "/login/")
    if rec:  # typed visibly
        rec.tap("input[name=login]", settle=0.2)
        rec.type(user, 2)
        rec.tap("input[name=password]", settle=0.2)
        rec.type(pw[:12], 1)
        b.js(f"document.querySelector('input[name=password]').value = {json.dumps(pw)}")
        rec.hold(0.3)
        rec.tap(js_find="document.querySelector('input[name=password]').form.querySelector('button[type=submit], button:not([type])')",
                settle=0.1)
        b.wait_event("Page.loadEventFired", 20)
        b.idle(1.0)
    else:
        b.js(f"""document.querySelector('input[name=login]').value = {json.dumps(user)};
                 document.querySelector('input[name=password]').value = {json.dumps(pw)};
                 document.querySelector('input[name=password]').form.submit()""")
        b.wait_event("Page.loadEventFired", 20)
        b.idle(1.0)


def prep(b, reduced=True):
    b.send("Emulation.setEmulatedMedia", {"features": [{"name": "prefers-reduced-motion", "value": "reduce" if reduced else "no-preference"},
                                                       {"name": "prefers-color-scheme", "value": "light"}]})


def capture_mobile(root, base, member_pw):
    b = Browser(9333)
    try:
        b.viewport(390, 844, 2, True)
        prep(b)
        r = Rec(b, root, 2)
        login(b, base, "aziz", member_pw)
        b.js("localStorage.setItem('fz-theme','dark')")

        r.scene("m_home")
        b.go(base + "/", 1.5)
        r.hold(1.0)
        r.scroll(520, 2.2)
        r.hold(0.8)

        r.scene("m_plans")
        b.go(base + "/plans/", 1.2)
        b.js("window.scrollTo(0, 0)")
        r.hold(0.4)
        r.scroll("form[action*='/plans/m3/buy/']", 1.4)
        r.hold(0.2)
        r.tap(js_find="""(() => { const f = document.querySelector("form[action*='/plans/m3/buy/']");
            const i = [...f.querySelectorAll('input[type=radio]')].find(x => /payme/i.test(x.value)) || f.querySelector('input[type=radio]');
            return i.closest('label') || i; })()""", settle=0.4)
        r.hold(0.4)
        r.tap(js_find="""(() => { const f = document.querySelector("form[action*='/plans/m3/buy/']");
            const c = f.querySelector('input[type=checkbox]'); return c ? (c.closest('label') || c) : null; })()""", settle=0.3)
        r.hold(1.2)

        r.scene("m_card")
        b.go(base + "/card/", 1.5)
        r.hold(1.0)
        r.tap(js_find="[...document.querySelectorAll('button')].find(e => e.textContent.includes('3D'))", settle=0.2)
        r.live(1.6)
        r.tap(js_find="[...document.querySelectorAll('button')].find(e => e.textContent.includes('Skanerlash'))", settle=0.3)
        # offline: the service worker keeps the card available without internet
        b.send("Network.emulateNetworkConditions", {"offline": True, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})
        try:
            b.go(base + "/card/", 1.5)
            ok = b.js("!!document.querySelector('svg, canvas, img') && document.body.innerText.includes('FZ-')")
        except Exception:
            ok = False
        r.cur["offline_ok"] = bool(ok)
        r.mark("offline")
        r.hold(2.0)
        b.send("Network.emulateNetworkConditions", {"offline": False, "latency": 0, "downloadThroughput": -1, "uploadThroughput": -1})

        r.scene("m_cal")
        b.go(base + "/calories/", 1.2)
        r.hold(0.6)
        r.scroll("#calSearch", 0.9)
        r.tap("#calSearch", settle=0.2)
        r.type("osh", 6)
        b.idle(0.8)
        r.hold(1.3)
        r.tap("#calResults li", settle=0.6)
        r.hold(1.0)

        r.scene("m_prog")
        b.go(base + "/progress/", 1.8)
        r.hold(0.5)
        r.scroll(b.js("""(() => { const h = [...document.querySelectorAll('h2,h3')].find(e => /vazn/i.test(e.textContent) && e.closest('.card'));
            return h ? h.closest('.card').getBoundingClientRect().top + scrollY - 120 : 1400; })()"""), 2.2)
        r.hold(1.2)

        r.scene("m_ai")
        b.go(base + "/ai/", 1.0)
        if b.js("!!document.querySelector(\"form[action*='/ai/clear/']\")"):
            b.js("document.querySelector(\"form[action*='/ai/clear/']\").submit()")
            b.wait_event("Page.loadEventFired", 10)
        b.go(base + "/ai/", 1.2)
        r.hold(0.4)
        r.scroll(b.js("""(() => { const e = document.querySelector('[data-ai-log]'); return e.getBoundingClientRect().top + scrollY - 130; })()"""), 0.8)
        r.tap("[data-ai-form] textarea", settle=0.2)
        r.type("Kuniga necha soat mashq qilishim kerak?", 2)
        r.hold(0.3)
        r.tap("[data-ai-form] button", settle=0.05)
        r.mark("sent")
        r.live(2.0)
        r.hold(1.5)

        r.scene("m_support")
        b.go(base + "/dashboard/", 1.2)
        b.js("window.scrollTo(0, 0)")
        r.hold(0.8)
        r.tap("#sw-fab", settle=0.1)
        r.live(1.0)
        r.tap(js_find="[...document.querySelectorAll('#sw-panel button, #sw-panel a')].find(e => /muzlatsa/i.test(e.textContent))", settle=0.1)
        r.live(1.0)
        r.hold(0.8)

        r.scene("m_install")
        b.go(base + "/dashboard/", 1.2)
        b.js("document.querySelectorAll('[data-pwa-install]').forEach(e => e.hidden = false); window.scrollTo(0, 0)")
        b.idle(0.3)
        r.hold(1.0)
        r.tap("[data-pwa-banner] [data-pwa-install-btn]", settle=0.2)
        r.mark("install")
        r.hold(2.5)
        r.done()
    finally:
        b.close()


def capture_desktop(root, base, member_pw, admin_pw):
    b = Browser(9334)
    try:
        b.viewport(1440, 900, 1.5, False)
        prep(b)
        r = Rec(b, root, 1.5)
        b.go(base + "/", 0.5)
        b.js("localStorage.setItem('fz-theme','light')")

        r.scene("d_home")
        b.go(base + "/", 1.5)
        r.hold(1.2)
        r.scroll(1150, 3.0)
        r.hold(0.6)
        r.scroll(2050, 2.4)
        r.hold(0.8)

        r.scene("d_plans")
        b.go(base + "/plans/", 1.2)
        r.hold(0.8)
        r.scroll(260, 1.5)
        r.hold(1.6)

        r.scene("d_shop")
        b.go(base + "/shop/", 1.5)
        r.hold(1.0)
        r.scroll(380, 1.8)
        r.hold(1.6)

        r.scene("d_classes")
        b.go(base + "/classes/", 1.5)
        r.hold(0.8)
        r.scroll(520, 2.0)
        r.hold(1.5)

        r.scene("d_tools")
        b.go(base + "/tools/", 1.2)
        r.hold(1.0)
        r.tap("#tl-tab-ovqat", settle=0.4)
        r.hold(1.3)
        r.tap("#tl-tab-mashq", settle=0.4)
        r.hold(1.3)

        r.scene("d_login")
        b.send("Network.clearBrowserCookies")
        b.go(base + "/login/", 1.0)
        r.hold(0.5)
        login(b, base, "aziz", member_pw, rec=r)
        r.hold(0.6)

        r.scene("d_dash")
        b.go(base + "/dashboard/", 1.5)
        r.hold(1.2)
        r.scroll(700, 2.2)
        r.hold(0.5)
        r.tap("#theme-btn", settle=0.6)
        r.mark("dark")
        r.hold(1.6)
        r.scroll(0, 1.4)
        r.hold(0.8)

        r.scene("d_prog")
        b.go(base + "/progress/", 2.0)
        r.hold(0.8)
        r.scroll(900, 2.4)
        r.hold(0.8)
        r.scroll(1800, 2.2)
        r.hold(1.0)

        r.scene("d_cal")
        b.go(base + "/calories/", 1.5)
        r.hold(0.8)
        r.tap("#calSearch", settle=0.2)
        r.type("osh", 6)
        b.idle(0.8)
        r.hold(1.6)

        r.scene("d_work")
        b.go(base + "/workouts/", 1.5)
        b.js("localStorage.setItem('fz-theme','light')")
        r.hold(1.0)
        r.scroll(600, 2.0)
        r.hold(1.4)

        r.scene("d_chat")
        b.js("localStorage.setItem('fz-theme','light')")
        b.go(base + "/chat/1/", 1.8)
        r.hold(0.8)
        row = "[...document.querySelectorAll('.m-row')].find(e => /squat/.test(e.textContent))"
        pt = b.js(f"(() => {{ const r = {row}.querySelector('.m-bubble').getBoundingClientRect(); return {{x: r.x + r.width / 2, y: r.y + r.height / 2}}; }})()")
        b.send("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": pt["x"], "y": pt["y"]})
        b.idle(0.3)
        r.hold(0.4)
        # the hover toolbar is CSS-hover only: open the reaction bar via its button (ripple drawn on the bubble)
        r.cur["taps"].append({"f": len(r.cur["frames"]), "x": pt["x"] * r.scale, "y": pt["y"] * r.scale})
        b.js(f"{row}.querySelector('[data-act=react]').click()")
        b.idle(0.4)
        r.hold(0.5)
        r.tap(js_find="[...document.querySelectorAll('.m-mrx .m-emo')].find(e => e.textContent.includes('👏')) || document.querySelector('.m-mrx .m-emo')", settle=0.6)
        r.hold(0.8)
        r.tap(js_find="[...document.querySelectorAll('textarea,input')].find(e => /xabar yozing/i.test(e.placeholder || ''))", settle=0.2)
        r.type("Ertaga ham kelaman! 💪", 2)
        r.hold(0.3)
        b.key("Enter", "Enter", 13)
        b.idle(0.2)
        r.live(1.2)
        r.hold(1.0)

        r.scene("a_login")
        b.send("Network.clearBrowserCookies")
        b.go(base + "/login/", 1.0)
        login(b, base, "admin", admin_pw + ".admin")

        r.scene("a_desk")
        b.go(base + "/django-admin/desk/", 1.8)
        r.hold(1.0)
        r.tap("#dk-q", settle=0.2)
        r.type("Aziz", 4)
        b.idle(0.8)
        r.hold(0.8)
        r.tap("#dk-results .dk-res", settle=0.8)
        r.hold(1.0)
        r.tap(js_find="[...document.querySelectorAll('#dk-member button')].find(e => /kirgiz/i.test(e.textContent))", settle=0.05)
        r.mark("checkin")
        r.live(1.6)
        r.hold(1.0)

        r.scene("a_analytics")
        b.go(base + "/django-admin/analytics/", 3.0)
        r.hold(1.2)
        r.scroll(700, 2.4)
        r.hold(0.8)
        r.scroll(1500, 2.4)
        r.hold(1.0)

        r.scene("a_ai")
        b.js("window.scrollTo(0, 0)")
        b.idle(0.3)
        r.hold(0.5)
        r.tap("#fz-ai-fab", settle=0.2)
        r.live(0.6)
        r.tap("#fz-ai form [name=q]", settle=0.1)
        r.type("Bu oy qancha tushum bo'ldi?", 2)
        r.hold(0.3)
        b.key("Enter", "Enter", 13)
        r.mark("asked")
        r.live(1.8)
        r.hold(2.0)

        r.scene("a_ig")
        b.go(base + "/django-admin/instagram/2/", 1.5)
        r.hold(1.6)
        b.go(base + "/django-admin/instagram/1/", 1.5)
        r.hold(2.0)
        r.done()
    finally:
        b.close()
