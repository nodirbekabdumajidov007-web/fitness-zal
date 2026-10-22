"""Compiles locale/*/LC_MESSAGES/*.po into .mo with plain Python, so no GNU gettext (msgfmt) has to be installed on Windows.

    python manage.py build_locale

The .po files only hold strings Django's own Uzbek translation leaves empty (mostly in the admin); Django merges them with
its built-in catalogue, and the project's LOCALE_PATHS win where both define a string."""
import ast
import re
import struct
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand


def parse_po(text):
    """Returns {msgid: msgstr}; plural entries become {"one\\0many": "form0\\0form1"} as the .mo format expects."""
    out = {}
    for block in re.split(r"\n\s*\n", text.strip()):
        fields, key = {}, None
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = re.match(r'^(msgctxt|msgid_plural|msgid|msgstr(?:\[\d+\])?)\s+(".*")$', line)
            if m:
                key = m.group(1)
                fields[key] = ast.literal_eval(m.group(2))
            elif line.startswith('"') and key:
                fields[key] += ast.literal_eval(line)
        if "msgid" not in fields:
            continue
        mid = fields["msgid"]
        if "msgctxt" in fields:
            mid = fields["msgctxt"] + "\x04" + mid
        if "msgid_plural" in fields:
            forms = [fields[k] for k in sorted(k for k in fields if k.startswith("msgstr["))]
            if all(forms):
                out[mid + "\x00" + fields["msgid_plural"]] = "\x00".join(forms)
        elif fields.get("msgstr") or mid == "":
            out[mid] = fields.get("msgstr", "")
    return out


def write_mo(messages, path):
    """The GNU .mo layout: a header, two tables of (length, offset) pairs, then the strings themselves."""
    keys = sorted(messages)
    ids = b"".join(k.encode() + b"\0" for k in keys)
    strs = b"".join(messages[k].encode() + b"\0" for k in keys)
    n = len(keys)
    start = 7 * 4 + n * 16
    offsets, pos_i, pos_s = [], 0, 0
    for k in keys:
        ki, vi = k.encode(), messages[k].encode()
        offsets.append((len(ki), start + pos_i, len(vi), start + len(ids) + pos_s))
        pos_i += len(ki) + 1
        pos_s += len(vi) + 1
    out = struct.pack("Iiiiiii", 0x950412DE, 0, n, 7 * 4, 7 * 4 + n * 8, 0, 0)
    out += b"".join(struct.pack("ii", a, b) for a, b, _, _ in offsets)
    out += b"".join(struct.pack("ii", c, d) for _, _, c, d in offsets)
    Path(path).write_bytes(out + ids + strs)


class Command(BaseCommand):
    help = "Compile the project's .po translation files into .mo (no gettext tools needed)."

    def handle(self, *args, **opts):
        done = 0
        for base in getattr(settings, "LOCALE_PATHS", []):
            for po in Path(base).rglob("*.po"):
                messages = parse_po(po.read_text(encoding="utf-8"))
                write_mo(messages, po.with_suffix(".mo"))
                done += 1
                self.stdout.write(f"{po} -> {len(messages) - 1} ta matn")
        self.stdout.write(self.style.SUCCESS(f"Tayyor: {done} ta fayl"))
