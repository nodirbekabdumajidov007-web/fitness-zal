"""Turns a pasted video link into something safe to show. Only YouTube, Vimeo and direct video files are embedded; any other https link is shown as a plain link."""
import re
from urllib.parse import parse_qs, urlparse

from django.core.exceptions import ValidationError

YT_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")


def video_embed(url):
    """Returns {'kind': 'iframe'|'video'|'link', 'src': str} or None."""
    if not url:
        return None
    u = urlparse(url.strip())
    if u.scheme != "https" or not u.hostname:
        return None
    host = u.hostname.lower().removeprefix("www.")
    parts = [p for p in u.path.split("/") if p]
    vid = ""
    if host in ("youtube.com", "m.youtube.com", "youtube-nocookie.com"):
        if u.path == "/watch":
            vid = parse_qs(u.query).get("v", [""])[0]
        elif len(parts) >= 2 and parts[0] in ("embed", "shorts", "live"):
            vid = parts[1]
    elif host == "youtu.be" and parts:
        vid = parts[0]
    if YT_ID.match(vid):
        return {"kind": "iframe", "src": f"https://www.youtube-nocookie.com/embed/{vid}"}
    if host in ("vimeo.com", "player.vimeo.com"):
        nums = [p for p in parts if p.isdigit()]
        if nums:
            return {"kind": "iframe", "src": f"https://player.vimeo.com/video/{nums[0]}"}
    if u.path.lower().endswith((".mp4", ".webm", ".ogg")):
        return {"kind": "video", "src": url.strip()}
    return {"kind": "link", "src": url.strip()}


IMAGE_TYPES = ((b"\xff\xd8\xff", "image/jpeg"), (b"\x89PNG\r\n\x1a\n", "image/png"))


def image_type(head):
    """Content type from the file's first bytes (never from its name). Only JPEG, PNG and WebP; SVG is refused because it can carry scripts."""
    for magic, ctype in IMAGE_TYPES:
        if head.startswith(magic):
            return ctype
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    return None


def validate_image(f):
    from django.conf import settings
    if not f.name.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
        raise ValidationError("Faqat .jpg, .png yoki .webp rasm yuklash mumkin.")
    if f.size > settings.MAX_IMAGE_MB * 1024 * 1024:
        raise ValidationError(f"Rasm {settings.MAX_IMAGE_MB} MB dan oshmasin.")
    pos = f.tell() if hasattr(f, "tell") else 0
    f.seek(0)
    head = f.read(16)
    f.seek(pos)
    if not image_type(head):
        raise ValidationError("Bu fayl rasm emas (yoki buzilgan).")


def validate_video_file(f):
    from django.conf import settings
    if not f.name.lower().endswith((".mp4", ".webm")):
        raise ValidationError("Faqat .mp4 yoki .webm video yuklash mumkin.")
    if f.size > settings.MAX_VIDEO_MB * 1024 * 1024:
        raise ValidationError(f"Video {settings.MAX_VIDEO_MB} MB dan oshmasin. Kattaroq videoni YouTube'ga joylab, havolasini qo'ying.")


def ranged_file_response(request, path, content_type="video/mp4"):
    """Serves a file with HTTP Range support, which browsers need to seek inside a video."""
    import os
    import re
    from django.http import FileResponse, HttpResponse, StreamingHttpResponse
    size = os.path.getsize(path)
    rng = request.headers.get("Range")
    if not rng:
        resp = FileResponse(open(path, "rb"), content_type=content_type)
        resp["Accept-Ranges"] = "bytes"
        return resp
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", rng.strip())
    if not m or (not m.group(1) and not m.group(2)):
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
    if m.group(1):
        start = int(m.group(1))
        end = min(int(m.group(2)), size - 1) if m.group(2) else size - 1
    else:  # "-N": the last N bytes
        start, end = max(0, size - int(m.group(2))), size - 1
    if start > end or start >= size:
        return HttpResponse(status=416, headers={"Content-Range": f"bytes */{size}"})
    length = end - start + 1

    def chunks():
        with open(path, "rb") as fh:
            fh.seek(start)
            left = length
            while left > 0:
                data = fh.read(min(65536, left))
                if not data:
                    break
                left -= len(data)
                yield data

    resp = StreamingHttpResponse(chunks(), status=206, content_type=content_type)
    resp["Content-Range"] = f"bytes {start}-{end}/{size}"
    resp["Content-Length"] = str(length)
    resp["Accept-Ranges"] = "bytes"
    return resp


def validate_video_url(value):
    if value and not str(value).startswith("https://"):
        raise ValidationError("Video havolasi https:// bilan boshlanishi kerak.")


def video_storage():
    """Lesson and hero videos: the local disk, or Cloudinary's video storage when CLOUDINARY_URL is set (see settings.STORAGES)."""
    from django.core.files.storage import storages
    return storages["videos"]


def is_local(field_file):
    """True when the file sits on this server's disk; False for Cloudinary, whose files are served from their own URL."""
    from django.core.files.storage import FileSystemStorage
    return isinstance(field_file.storage, FileSystemStorage)
