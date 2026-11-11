"""Original, procedurally generated soundtrack + sound effects + Windows TTS voice-over for tools/make_videos.py.

No samples, no copyrighted material: every sound is synthesised here from sine/saw/noise. Pure Python (no numpy), so
bars are rendered once per (section, chord) and then repeated. 44.1 kHz stereo, written with the `wave` module."""
import math
import operator
import os
import random
import struct
import subprocess
import wave
from array import array

SR = 44100
BPM = 120
BEAT = SR * 60 / BPM
BAR = int(BEAT * 4)
TAU = 2 * math.pi
RNG = random.Random(11)

# A minor: Am - F - C - G (roots, chord tones as MIDI)
CHORDS = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]
LEAD = [[76, 0, 72, 74, 76, 0, 79, 76], [77, 0, 76, 72, 74, 0, 72, 69], [76, 0, 72, 74, 79, 0, 76, 74], [74, 0, 71, 72, 74, 76, 74, 0]]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def zeros(n):
    return array("f", bytes(4 * n))


def add(dst, src, at, gain=1.0):
    at = int(at)
    if at >= len(dst):
        return
    n = min(len(src), len(dst) - at)
    if gain != 1.0:
        src = array("f", map(gain.__mul__, src[:n]))
    dst[at:at + n] = array("f", map(operator.add, dst[at:at + n], src[:n]))


def noise(n, seed=None):
    r = random.Random(seed) if seed is not None else RNG
    return array("f", (r.uniform(-1, 1) for _ in range(n)))


def onepole_lp(x, cutoff):
    a = math.exp(-TAU * cutoff / SR)
    y, out = 0.0, array("f", x)
    for i, v in enumerate(x):
        y = (1 - a) * v + a * y
        out[i] = y
    return out


def hp(x):
    out, p = array("f", x), 0.0
    for i, v in enumerate(x):
        out[i], p = v - p, v
    return out


# ---------- instruments (one-shots) ----------
def kick(boom=False):
    n = int(SR * (0.9 if boom else 0.32))
    out, ph = zeros(n), 0.0
    for i in range(n):
        t = i / SR
        f = 45 + 110 * math.exp(-t * 28)
        ph += TAU * f / SR
        out[i] = math.sin(ph) * math.exp(-t * (3.2 if boom else 9.0)) * 0.95
    for i in range(min(n, 220)):
        out[i] += RNG.uniform(-1, 1) * 0.35 * (1 - i / 220)
    return out


def snare():
    n = int(SR * 0.22)
    nz = hp(noise(n, 3))
    out = zeros(n)
    for i in range(n):
        t = i / SR
        out[i] = nz[i] * math.exp(-t * 18) * 0.55 + math.sin(TAU * 185 * t) * math.exp(-t * 30) * 0.4
    return out


def clap():
    n = int(SR * 0.25)
    nz = hp(hp(noise(n, 4)))
    out = zeros(n)
    for i in range(n):
        t = i / SR
        env = sum(math.exp(-max(0, t - d) * 60) * (t >= d) for d in (0, 0.011, 0.022)) * 0.33 + math.exp(-t * 12) * 0.5
        out[i] = nz[i] * env * 0.5
    return out


def hat(open_=False):
    n = int(SR * (0.16 if open_ else 0.045))
    nz = hp(hp(hp(noise(n, 5 if open_ else 6))))
    return array("f", (nz[i] * math.exp(-i / SR * (18 if open_ else 80)) * 0.32 for i in range(n)))


def saw_note(f, n, detunes=(0.0,), cutoff=2400, env=None, harm=12):
    out = zeros(n)
    for d in detunes:
        fr = f * (1 + d)
        ph = RNG.random()
        inc = fr / SR
        k = max(1, min(harm, int(SR / 2 / fr)))
        for i in range(n):
            ph += inc
            if ph >= 1:
                ph -= 1
            # band-limited-ish saw: sum of a few harmonics
            x = ph * TAU
            s = math.sin(x) + math.sin(2 * x) / 2 + math.sin(3 * x) / 3 + (math.sin(4 * x) / 4 if k > 3 else 0) + (math.sin(5 * x) / 5 if k > 4 else 0)
            out[i] += s
    g = 1 / len(detunes)
    out = onepole_lp(out, cutoff)
    if env:
        for i in range(n):
            out[i] *= env(i / SR) * g
    else:
        for i in range(n):
            out[i] *= g
    return out


def pump_env(n, depth=0.75):
    """Side-chain style ducking on every beat (the classic EDM pump)."""
    e = zeros(n)
    for i in range(n):
        t = (i % BEAT) / SR
        e[i] = 1 - depth * math.exp(-t * 9)
    return e


def mul(a, b):
    return array("f", map(operator.mul, a, b))


# ---------- bars ----------
_cache = {}


def chord_bar(ci, kind, side):
    key = ("chord", ci, kind, side)
    if key in _cache:
        return _cache[key]
    _, notes = CHORDS[ci]
    det = (-0.006, 0.0, 0.007) if side == 0 else (-0.009, 0.003, 0.011)
    out = zeros(BAR)
    if kind == "pad":
        for m in notes:
            add(out, saw_note(hz(m), BAR, det, cutoff=1300,
                              env=lambda t: min(1, t / 0.25) * (0.9 + 0.1 * math.sin(t * 3))), 0, 0.16)
    else:  # stabs on the off-beats with pump
        stab = None
        for m in notes:
            s = saw_note(hz(m + 12), int(BEAT * 0.45), det, cutoff=3200, env=lambda t: math.exp(-t * 7))
            stab = s if stab is None else array("f", map(operator.add, stab, s))
        for k in (0.5, 1.5, 2.5, 3.5, 1.0 + 0.75, 3.0 + 0.75):
            add(out, stab, k * BEAT, 0.11)
        for m in notes:
            add(out, saw_note(hz(m), BAR, det, cutoff=900), 0, 0.07)
        out = mul(out, pump_env(BAR, 0.7))
    _cache[key] = out
    return out


def bass_bar(ci, kind):
    key = ("bass", ci, kind)
    if key in _cache:
        return _cache[key]
    root = CHORDS[ci][0] - 24
    out = zeros(BAR)
    n8 = int(BEAT / 2)
    note = saw_note(hz(root), n8, (0.0,), cutoff=420, env=lambda t: min(1, t / 0.008) * math.exp(-t * 3.5))
    sub = array("f", (math.sin(TAU * hz(root) * i / SR) * min(1, i / 300) * math.exp(-i / SR * 3) for i in range(n8)))
    both = array("f", map(lambda a, b: a * 0.6 + b * 0.8, note, sub))
    steps = range(8) if kind == "drive" else (0, 3, 4, 7)
    for s in steps:
        if kind == "drive" and s % 2 == 0:
            continue  # off-beat bass bounces against the kick
        add(out, both, s * n8, 0.55)
    if kind != "drive":
        long = array("f", (math.sin(TAU * hz(root) * i / SR) * min(1, i / 600) * math.exp(-i / SR * 0.9) for i in range(BAR)))
        add(out, long, 0, 0.35)
    _cache[key] = out
    return out


def lead_bar(ci):
    key = ("lead", ci)
    if key in _cache:
        return _cache[key]
    out = zeros(BAR)
    n8 = int(BEAT / 2)
    for s, m in enumerate(LEAD[ci]):
        if m:
            add(out, saw_note(hz(m), int(n8 * 1.6), (-0.004, 0.005), cutoff=4200,
                              env=lambda t: min(1, t / 0.005) * math.exp(-t * 5.5), harm=5), s * n8, 0.10)
    _cache[key] = out
    return out


def drums_bar(kind, fill=False):
    key = ("drums", kind, fill)
    if key in _cache:
        return _cache[key]
    out = zeros(BAR)
    K, S, C, H, O = KIT
    if kind in ("drop", "groove"):
        for b in range(4):
            add(out, K, b * BEAT, 0.9)
        for b in (1, 3):
            add(out, C if kind == "drop" else S, b * BEAT, 0.6)
        for s in range(16):
            if s % 4 == 2:
                add(out, O, s * BEAT / 4, 0.55)
            elif kind == "drop" or s % 2 == 0:
                add(out, H, s * BEAT / 4, 0.5 if s % 2 == 0 else 0.35)
        if fill:
            for s in (13, 14, 15):
                add(out, S, s * BEAT / 4, 0.45)
    elif kind == "break":
        add(out, K, 0, 0.7)
        for s in range(0, 16, 2):
            add(out, H, s * BEAT / 4, 0.3)
    elif kind == "build":
        for s in range(16):
            add(out, S, s * BEAT / 4, 0.18 + 0.4 * s / 16)
    _cache[key] = out
    return out


def riser(nbars):
    n = BAR * nbars
    nz = noise(n, 9)
    out, y, ph = zeros(n), 0.0, 0.0
    for i in range(n):
        t = i / n
        cut = 300 + 9000 * t * t
        a = math.exp(-TAU * cut / SR)
        y = (1 - a) * nz[i] + a * y
        ph += TAU * (220 + 900 * t * t) / SR
        out[i] = (y * 0.5 + math.sin(ph) * 0.12) * (t ** 1.6)
    return out


def crash():
    n = int(SR * 1.6)
    nz = hp(hp(noise(n, 12)))
    return array("f", (nz[i] * math.exp(-i / SR * 2.6) * 0.35 for i in range(n)))


KIT = None


def song(sections):
    """sections: list of section names, one per bar: intro, build, drop, groove, break, outro, end."""
    global KIT
    if KIT is None:
        KIT = (kick(), snare(), clap(), hat(), hat(True))
    n = BAR * len(sections) + SR * 2
    L, R = zeros(n), zeros(n)
    boom, cr = kick(True), crash()
    i = 0
    while i < len(sections):
        sec, at, ci = sections[i], i * BAR, i % 4
        nxt = sections[i + 1] if i + 1 < len(sections) else None
        if sec == "build" and (i == 0 or sections[i - 1] != "build"):
            nb = 1
            while i + nb < len(sections) and sections[i + nb] == "build":
                nb += 1
            r = riser(nb)
            add(L, r, at, 0.8)
            add(R, r, at, 0.8)
        if sec in ("drop", "groove") and (i == 0 or sections[i - 1] not in ("drop", "groove")):
            add(L, boom, at, 0.8)
            add(R, boom, at, 0.8)
            add(L, cr, at, 0.9)
            add(R, cr, at, 0.75)
        fill = nxt in ("build", "break", "outro", "end") or (i % 8 == 7)
        dr = drums_bar("drop" if sec == "drop" else "groove" if sec == "groove" else sec if sec in ("break", "build") else "break"
                       if sec == "outro" else "none", fill and sec in ("drop", "groove"))
        if sec not in ("intro", "end"):
            add(L, dr, at, 1.0)
            add(R, dr, at, 1.0)
        if sec in ("intro", "break", "outro", "build", "end"):
            add(L, chord_bar(ci, "pad", 0), at, 1.0 if sec != "end" else 0.8)
            add(R, chord_bar(ci, "pad", 1), at, 1.0 if sec != "end" else 0.8)
            if sec in ("break", "outro"):
                add(L, bass_bar(ci, "soft"), at, 0.8)
                add(R, bass_bar(ci, "soft"), at, 0.8)
        else:
            add(L, chord_bar(ci, "stab", 0), at, 1.0)
            add(R, chord_bar(ci, "stab", 1), at, 1.0)
            add(L, bass_bar(ci, "drive"), at, 1.0)
            add(R, bass_bar(ci, "drive"), at, 1.0)
            if sec == "drop":
                ld = lead_bar(ci)
                add(L, ld, at + int(BEAT * 0.02), 0.9)
                add(R, ld, at, 0.75)
        if sec == "end":
            add(L, boom, at, 0.7)
            add(R, boom, at, 0.7)
            add(L, cr, at, 0.7)
            add(R, cr, at, 0.7)
        i += 1
    # fade the tail of the last bar
    total = BAR * len(sections)
    fade = int(BAR * 0.9)
    for k in range(total - fade, n):
        g = max(0.0, 1 - (k - (total - fade)) / (fade + SR))
        L[k] *= g
        R[k] *= g
    return L[:total], R[:total]


# ---------- sound effects ----------
def sfx_whoosh(dur=0.55):
    n = int(SR * dur)
    nz = noise(n, 21)
    out, y = zeros(n), 0.0
    for i in range(n):
        t = i / n
        cut = 400 + 5000 * math.sin(math.pi * t)
        a = math.exp(-TAU * cut / SR)
        y = (1 - a) * nz[i] + a * y
        out[i] = y * math.sin(math.pi * t) ** 2 * 0.9
    return out


def sfx_click():
    n = int(SR * 0.05)
    return array("f", (math.sin(TAU * 2600 * i / SR) * math.exp(-i / SR * 140) * 0.5 + (RNG.uniform(-1, 1) * 0.3 if i < 60 else 0)
                       for i in range(n)))


def sfx_pop():
    n = int(SR * 0.09)
    ph, out = 0.0, zeros(n)
    for i in range(n):
        t = i / SR
        ph += TAU * (900 - 5000 * t) / SR
        out[i] = math.sin(ph) * math.exp(-t * 40) * 0.55
    return out


def sfx_chime():
    n = int(SR * 1.2)
    out = zeros(n)
    for f, d in ((1318.5, 0.0), (1975.5, 0.09), (2637.0, 0.18)):
        s = int(d * SR)
        for i in range(s, n):
            t = (i - s) / SR
            out[i] += (math.sin(TAU * f * t) + 0.3 * math.sin(TAU * f * 2.01 * t)) * math.exp(-t * 4.5) * 0.22
    return out


def sfx_type():
    n = int(SR * 0.025)
    nz = hp(noise(n, RNG.randint(0, 999)))
    return array("f", (nz[i] * math.exp(-i / SR * 260) * 0.25 for i in range(n)))


SFX = {}


def sfx_track(events, total_sec):
    """events: list of (time_sec, kind, gain). Returns a mono track."""
    if not SFX:
        SFX.update(whoosh=sfx_whoosh(), click=sfx_click(), pop=sfx_pop(), chime=sfx_chime(), type=sfx_type())
    out = zeros(int(total_sec * SR) + SR)
    for t, kind, g in events:
        add(out, SFX[kind], t * SR, g)
    return out


# ---------- voice (Windows SAPI) ----------
def tts(lines, out_dir, voice="Microsoft Zira Desktop", rate=1):
    """lines: {key: text}. Writes key.wav (44.1 kHz mono 16-bit) with System.Speech; returns {key: path}."""
    os.makedirs(out_dir, exist_ok=True)
    ps = ["Add-Type -AssemblyName System.Speech",
          "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer",
          f"$s.SelectVoice('{voice}')", f"$s.Rate = {int(rate)}",
          "$fmt = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)"]
    paths = {}
    for k, text in lines.items():
        p = os.path.join(out_dir, f"{k}.wav")
        paths[k] = p
        t = text.replace("'", "''")
        ps += [f"$s.SetOutputToWaveFile('{p}', $fmt)", f"$s.Speak('{t}')"]
    ps.append("$s.SetOutputToNull(); $s.Dispose()")
    script = os.path.join(out_dir, "tts.ps1")
    with open(script, "w", encoding="utf-8-sig") as f:
        f.write("\n".join(ps))
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script], check=True)
    return paths


def read_wav_mono(path):
    with wave.open(path, "rb") as w:
        assert w.getframerate() == SR and w.getsampwidth() == 2
        raw = w.readframes(w.getnframes())
        ch = w.getnchannels()
    a = array("h", raw)
    if ch == 2:
        a = a[::2]
    return array("f", (v / 32768 for v in a))


def trim_silence(x, thr=0.01):
    s = next((i for i, v in enumerate(x) if abs(v) > thr), 0)
    e = len(x) - next((i for i, v in enumerate(reversed(x)) if abs(v) > thr), 0)
    return x[max(0, s - 200):min(len(x), e + 2000)]


def voice_track(clips, total_sec):
    """clips: list of (time_sec, samples). Mono track."""
    out = zeros(int(total_sec * SR) + SR)
    for t, x in clips:
        add(out, x, t * SR, 1.0)
    return out


def write_wav(path, L, R=None, peak=0.89):
    R = R if R is not None else L
    m = max(max(map(abs, L)), max(map(abs, R)), 1e-6)
    g = peak / m if m > peak else 1.0
    inter = array("h", bytes(4 * len(L)))
    inter[0::2] = array("h", (int(max(-1, min(1, v * g)) * 32767) for v in L))
    inter[1::2] = array("h", (int(max(-1, min(1, v * g)) * 32767) for v in R))
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(inter.tobytes())
    return path


def mix(ffmpeg, music, sfx, voice, out, voice_gain=1.6, duck=True):
    """Music ducked under the voice (side-chain compressor), plus SFX; loudness-normalised to about -14 LUFS."""
    if voice:
        fc = ("[0:a]volume=0.85[m];[2:a]volume=%.2f,asplit=2[v1][v2];" % voice_gain +
              ("[m][v1]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=350:makeup=1[md];" if duck else "[m]anull[md];[v1]anullsink;") +
              "[md][1:a][v2]amix=inputs=3:normalize=0:weights=1 0.9 1[mx];"
              "[mx]loudnorm=I=-14:TP=-1.2:LRA=11,aresample=44100[out]")
        ins = ["-i", music, "-i", sfx, "-i", voice]
    else:
        fc = "[0:a]volume=0.85[m];[m][1:a]amix=inputs=2:normalize=0:weights=1 0.9[mx];[mx]loudnorm=I=-14:TP=-1.2:LRA=11,aresample=44100[out]"
        ins = ["-i", music, "-i", sfx]
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[out]", "-ac", "2", "-c:a", "pcm_s16le", out],
                   check=True)
    return out
