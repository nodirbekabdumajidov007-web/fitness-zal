"""The home-page promo video: one URL from the settings -> what the page needs to show a click-to-load player.

Nothing from a third party is loaded until the visitor presses play (a poster + button "facade"), so the page stays fast and
YouTube / Instagram learn nothing about visitors who only scroll past. Only https links of three known shapes are accepted;
anything else returns None and the section stays hidden."""
import re
from urllib.parse import parse_qs, urlparse

YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
IG_ID = re.compile(r"^[A-Za-z0-9_-]{5,40}$")
YT_HOSTS = {"youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com"}
VIDEO_EXT = (".mp4", ".webm")


def parse_promo(url):
    """-> {"kind": "youtube"|"instagram"|"file", "src": embed/file URL, "vertical": bool, "thumb": str} or None."""
    url = (url or "").strip()
    if not url:
        return None
    u = urlparse(url)
    if u.scheme != "https" or not u.hostname:
        return None
    host = u.hostname.lower().removeprefix("www.")
    parts = [p for p in u.path.split("/") if p]

    vid, short = "", False
    if host in YT_HOSTS:
        if u.path == "/watch":
            vid = parse_qs(u.query).get("v", [""])[0]
        elif len(parts) >= 2 and parts[0] in ("embed", "shorts", "live"):
            vid, short = parts[1], parts[0] == "shorts"
    elif host == "youtu.be" and parts:
        vid = parts[0]
    if YT_ID.match(vid):
        # youtube-nocookie.com = privacy-enhanced mode: no cookies until the visitor plays. rel=0: related videos only from this channel.
        return {"kind": "youtube", "src": f"https://www.youtube-nocookie.com/embed/{vid}?autoplay=1&rel=0&playsinline=1&modestbranding=1",
                "vertical": short, "thumb": f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"}

    if host == "instagram.com" and len(parts) >= 2 and parts[0] in ("reel", "reels", "p", "tv") and IG_ID.match(parts[1]):
        kind = "p" if parts[0] == "p" else "reel"
        return {"kind": "instagram", "src": f"https://www.instagram.com/{kind}/{parts[1]}/embed", "vertical": kind == "reel", "thumb": ""}

    if u.path.lower().endswith(VIDEO_EXT):
        return {"kind": "file", "src": url, "vertical": False, "thumb": ""}
    return None
