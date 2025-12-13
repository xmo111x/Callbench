import os
import sys
import threading
import subprocess
from pathlib import Path
from datetime import datetime

import keyring
from tkinter import *
from tkinter import ttk, messagebox, filedialog

from openai import OpenAI
from pydub import AudioSegment
from pydub.utils import which

# ========= Basis-Konfiguration =========
TTS_MODEL = "gpt-4o-mini-tts"
VALID_VOICES = [
    "nova", "alloy", "shimmer", "coral", "echo", "verse",
    "fable", "onyx", "ballad", "ash", "sage", "marin", "cedar"
]

APP_NAME = "Callbench"
SERVICE_NAME = "Callbench"
KEY_NAME = "OPENAI_API_KEY"

# ========= Pfad-/Bundle-Helper =========
def resolve_tool(name: str) -> str | None:
    # 1) Systemweit (Terminal-Run)
    p = which(name)
    if p:
        return p

    # 2) Gebündelt (PyInstaller)
    exe = f"{name}.exe" if os.name == "nt" else name
    candidate = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / "ffmpeg" / exe
    return str(candidate) if candidate.exists() else None

ffmpeg_path = resolve_tool("ffmpeg")
ffprobe_path = resolve_tool("ffprobe")

if not ffmpeg_path or not ffprobe_path:
    raise RuntimeError("ffmpeg/ffprobe wurden nicht gefunden. App ist unvollständig gebaut.")

AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

def resource_path(rel_path: str) -> str:
    """
    Liefert Pfade für PyInstaller-Bundles (sys._MEIPASS) und für normalen Dev-Run.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / rel_path)
    
def bundled_frameworks_ffmpeg_dir() -> Path | None:
    """
    In der macOS .app liegt ffmpeg/ffprobe typischerweise unter:
    Callbench.app/Contents/Frameworks/ffmpeg/
    """
    try:
        exe = Path(sys.executable).resolve()  # .../Callbench.app/Contents/MacOS/Callbench
        contents = exe.parents[1]            # .../Callbench.app/Contents
        d = contents / "Frameworks" / "ffmpeg"
        return d if d.exists() else None
    except Exception:
        return None

def resolve_tool(name: str) -> str | None:
    # 1) Systemweit (Terminal-Run)
    p = which(name)
    if p:
        return p

    # 2) PyInstaller _MEIPASS (manche Layouts)
    exe_name = f"{name}.exe" if os.name == "nt" else name
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    cand1 = base / "ffmpeg" / exe_name
    if cand1.exists():
        return str(cand1)

    # 3) macOS .app Frameworks (dein aktuelles Layout)
    d = bundled_frameworks_ffmpeg_dir()
    if d:
        cand2 = d / name
        if cand2.exists():
            return str(cand2)

    return None

ffmpeg_path = resolve_tool("ffmpeg")
ffprobe_path = resolve_tool("ffprobe")

if not ffmpeg_path or not ffprobe_path:
    raise RuntimeError(
        f"ffmpeg/ffprobe nicht gefunden. ffmpeg={ffmpeg_path}, ffprobe={ffprobe_path}"
    )

# pydub explizit setzen
AudioSegment.converter = ffmpeg_path
AudioSegment.ffprobe = ffprobe_path

# Zusätzlich: PATH erweitern, damit Subprocess-Aufrufe 'ffprobe' sicher finden
ff_dir = str(Path(ffprobe_path).parent)
os.environ["PATH"] = ff_dir + os.pathsep + os.environ.get("PATH", "")

def output_dir(app_name: str = APP_NAME) -> Path:
    """
    Standard-Ausgabeordner: ~/Downloads/Callbench
    """
    d = Path.home() / "Downloads" / app_name
    d.mkdir(parents=True, exist_ok=True)
    return d

def resolve_ffmpeg_tools() -> tuple[str | None, str | None]:
    # 1) Systemweit (Terminal)
    ffmpeg_p = which("ffmpeg")
    ffprobe_p = which("ffprobe")

    # 2) Bundled (PyInstaller) als Fallback
    if not ffmpeg_p:
        ffmpeg_p = resource_path("ffmpeg/ffmpeg.exe" if os.name == "nt" else "ffmpeg/ffmpeg")
    if not ffprobe_p:
        ffprobe_p = resource_path("ffmpeg/ffprobe.exe" if os.name == "nt" else "ffmpeg/ffprobe")

    if ffmpeg_p and not Path(ffmpeg_p).exists():
        ffmpeg_p = None
    if ffprobe_p and not Path(ffprobe_p).exists():
        ffprobe_p = None

    return ffmpeg_p, ffprobe_p

_ffmpeg, _ffprobe = resolve_ffmpeg_tools()
if _ffmpeg:
    AudioSegment.converter = _ffmpeg
if _ffprobe:
    AudioSegment.ffprobe = _ffprobe
    
# ========= Keyring / API-Key =========
def load_api_key() -> str | None:
    return keyring.get_password(SERVICE_NAME, KEY_NAME)

def save_api_key(api_key: str) -> None:
    keyring.set_password(SERVICE_NAME, KEY_NAME, api_key)

def prompt_for_api_key(parent) -> str | None:
    win = Toplevel(parent)
    win.title("OpenAI API Key")
    win.geometry("560x200")
    win.grab_set()

    Label(win, text="Bitte OpenAI API Key eingeben:", font=("Arial", 11, "bold")).pack(anchor=W, padx=12, pady=(12, 6))

    key_var = StringVar(value="")
    ent = Entry(win, textvariable=key_var, show="*", width=72)
    ent.pack(padx=12, pady=6)
    ent.focus_set()

    Label(
        win,
        text="Der Key wird sicher im System-Schlüsselbund gespeichert (Keychain / Credential Manager).",
        anchor=W,
        justify=LEFT
    ).pack(fill=X, padx=12, pady=(0, 10))

    result = {"key": None}

    def on_ok():
        k = key_var.get().strip()
        if not k:
            messagebox.showwarning("Hinweis", "Bitte einen Key eingeben.")
            return
        result["key"] = k
        win.destroy()

    def on_cancel():
        win.destroy()

    btns = Frame(win)
    btns.pack(pady=6)
    Button(btns, text="Speichern", command=on_ok, width=14).grid(row=0, column=0, padx=6)
    Button(btns, text="Abbrechen", command=on_cancel, width=14).grid(row=0, column=1, padx=6)

    win.wait_window()
    return result["key"]

# ========= OS-Helper =========
def open_folder(path: Path):
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(path)], check=False)
        elif os.name == "nt":
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(path)], check=False)
    except Exception:
        pass

# ========= Hilfsfunktionen Audio =========
def adjust_voice(segment: AudioSegment, speed: float = 1.0, pitch_semitones: float = 0.0) -> AudioSegment:
    """
    Tempo und Tonhöhe anpassen (einfaches Resampling).
    - speed: 1.0 = normal, >1 schneller, <1 langsamer
    - pitch_semitones: +1 = einen Halbton höher, -1 = tiefer
    """
    # Tempo
    if speed != 1.0:
        new_frame_rate = int(segment.frame_rate * speed)
        segment = segment._spawn(segment.raw_data, overrides={"frame_rate": new_frame_rate})
        segment = segment.set_frame_rate(44100)

    # Pitch
    if pitch_semitones != 0.0:
        factor = 2 ** (pitch_semitones / 12.0)
        new_rate = int(segment.frame_rate * factor)
        segment = segment._spawn(segment.raw_data, overrides={"frame_rate": new_rate})
        segment = segment.set_frame_rate(44100)

    return segment

def stylize_text(raw: str, style: str) -> str:
    """
    Stil „freundlich/neutral/lebendig“ durch minimale Prosodiezeichen im Text.
    """
    text = raw.strip()

    if style == "freundlich & ruhig":
        text = text.replace("Hallo,", "Hallo …")
        text = text.replace("Leider", "Leider …")
    elif style == "neutral":
        pass
    elif style == "hell & freundlich":
        text = text.replace("Hallo,", "Hallo,")
    elif style == "lebendig":
        text = text.replace("Hallo,", "Hallo –")

    return text

# ========= TTS + Mix =========
def synthesize_tts_to_wav(text: str, voice: str, out_wav: Path, api_key: str):
    client = OpenAI(api_key=api_key)
    with client.audio.speech.with_streaming_response.create(
        model=TTS_MODEL,
        voice=voice,
        input=text,
        response_format="wav"
    ) as resp:
        resp.stream_to_file(out_wav)

def make_mix(
    voice_wav: Path,
    music_path: Path | None,
    delay_ms: int,
    music_gain_db: int,
    out_wav: Path,
    out_mp3: Path,
    speed: float = 1.0,
    pitch_semitones: float = 0.0
):
    voice = AudioSegment.from_file(voice_wav)

    # Speed/Pitch (nach dem TTS)
    voice = adjust_voice(voice, speed=speed, pitch_semitones=pitch_semitones)

    # Stimme später starten lassen
    voice = AudioSegment.silent(duration=delay_ms) + voice

    if music_path and music_path.exists():
        music = AudioSegment.from_file(music_path) + music_gain_db
        if len(music) < len(voice):
            loops = (len(voice) // len(music)) + 1
            music = music * loops
        music = music[:len(voice)].fade_in(300)
        mix = voice.overlay(music)
    else:
        mix = voice

    mix = mix.fade_out(400)
    mix.export(out_wav, format="wav")
    mix.export(out_mp3, format="mp3", bitrate="192k")

# ========= GUI =========
class App(Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("680x640")

        Label(self, text="Ansagetext:", font=("Arial", 11, "bold")).pack(anchor=W, padx=12, pady=(12, 4))
        self.text_box = Text(self, height=10, width=70, wrap=WORD)
        self.text_box.pack(padx=12, pady=(0, 10))
        self.text_box.insert(
            END,
            "Hallo, hier ist der Anrufbeantworter der Praxis. Leider können wir Ihren Anruf nicht entgegennehmen. "
            "Bitte hinterlassen Sie Ihren Namen und Ihre Telefonnummer. "
            "Wir rufen Sie sobald wie möglich zurück."
        )

        frm = Frame(self)
        frm.pack(fill=X, padx=12, pady=6)

        Label(frm, text="Stimme:", width=16).grid(row=0, column=0, sticky=W, pady=3)
        self.voice_var = StringVar(value="nova")
        ttk.Combobox(frm, textvariable=self.voice_var, values=VALID_VOICES, width=18, state="readonly") \
            .grid(row=0, column=1, sticky=W)

        Label(frm, text="Stil:", width=16).grid(row=1, column=0, sticky=W, pady=3)
        self.style_var = StringVar(value="freundlich & ruhig")
        ttk.Combobox(
            frm,
            textvariable=self.style_var,
            values=["freundlich & ruhig", "neutral", "hell & freundlich", "lebendig"],
            width=18,
            state="readonly"
        ).grid(row=1, column=1, sticky=W)

        Label(frm, text="Start-Delay (ms):", width=16).grid(row=2, column=0, sticky=W, pady=3)
        self.delay_var = StringVar(value="1000")
        Entry(frm, textvariable=self.delay_var, width=10).grid(row=2, column=1, sticky=W)

        Label(frm, text="Musik-Lautstärke (dB):", width=16).grid(row=3, column=0, sticky=W, pady=3)
        self.gain_var = StringVar(value="-18")
        Entry(frm, textvariable=self.gain_var, width=10).grid(row=3, column=1, sticky=W)

        Label(frm, text="Musik-Datei:", width=16).grid(row=4, column=0, sticky=W, pady=3)
        # Default leer oder im Projektordner "musik.mp3"
        default_music = str((Path.cwd() / "musik.mp3").resolve())
        self.music_var = StringVar(value="")
        Entry(frm, textvariable=self.music_var, width=40).grid(row=4, column=1, sticky=W)
        Button(frm, text="Durchsuchen…", command=self.browse_music).grid(row=4, column=2, padx=6)

        Label(frm, text="Tempo-Faktor:", width=16).grid(row=5, column=0, sticky=W, pady=3)
        self.speed_var = StringVar(value="1.0")
        Entry(frm, textvariable=self.speed_var, width=10).grid(row=5, column=1, sticky=W)

        Label(frm, text="Pitch (Halbtöne):", width=16).grid(row=6, column=0, sticky=W, pady=3)
        self.pitch_var = StringVar(value="0")
        Entry(frm, textvariable=self.pitch_var, width=10).grid(row=6, column=1, sticky=W)

        btn_frame = Frame(self)
        btn_frame.pack(pady=10)

        self.gen_btn = Button(
            btn_frame,
            text="Ansage erzeugen",
            command=self.on_generate,
            bg="#4CAF50",
            fg="black",
            font=("Arial", 12, "bold")
        )
        self.gen_btn.grid(row=0, column=0, padx=8)

        # optional: API Key ändern
        self.key_btn = Button(
            btn_frame,
            text="API-Key ändern",
            command=self.on_change_key
        )
        self.key_btn.grid(row=0, column=1, padx=8)

        self.status_var = StringVar(value="Bereit.")
        Label(self, textvariable=self.status_var, anchor=W).pack(fill=X, padx=12, pady=(6, 12))

    # ---------- UI helper (thread-safe) ----------
    def ui(self, fn, *args, **kwargs):
        self.after(0, lambda: fn(*args, **kwargs))

    def set_busy(self, busy: bool):
        self.gen_btn.config(state=DISABLED if busy else NORMAL)
        self.key_btn.config(state=DISABLED if busy else NORMAL)
        self.status_var.set("Bitte warten …" if busy else "Bereit.")

    # ---------- actions ----------
    def browse_music(self):
        path = filedialog.askopenfilename(
            title="Musikdatei wählen",
            filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg"), ("Alle Dateien", "*.*")]
        )
        if path:
            self.music_var.set(path)

    def on_change_key(self):
        k = prompt_for_api_key(self)
        if k:
            save_api_key(k)
            messagebox.showinfo("OK", "API-Key wurde gespeichert.")

    def on_generate(self):
        # API Key laden/abfragen
        api_key = load_api_key()
        if not api_key:
            api_key = prompt_for_api_key(self)
            if not api_key:
                return
            save_api_key(api_key)

        text = self.text_box.get("1.0", END).strip()
        if not text:
            messagebox.showwarning("Hinweis", "Bitte Text eingeben.")
            return

        voice = self.voice_var.get().strip()
        if voice not in VALID_VOICES:
            messagebox.showerror("Ungültige Stimme", f"Bitte eine der verfügbaren Stimmen wählen:\n{', '.join(VALID_VOICES)}")
            return

        try:
            delay = int(self.delay_var.get())
            gain = int(self.gain_var.get())
            speed = float(self.speed_var.get())
            pitch = float(self.pitch_var.get())
        except ValueError:
            messagebox.showerror("Eingabefehler", "Bitte gültige Zahlen für Delay, Lautstärke, Tempo, Pitch eingeben.")
            return

        style = self.style_var.get()
        tts_text = stylize_text(text, style)
        music_path = Path(self.music_var.get()) if self.music_var.get().strip() else None

        # Dateinamen pro Klick
        out_dir = output_dir(APP_NAME)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        output_mp3 = out_dir / f"ansage_{ts}.mp3"
        output_wav = out_dir / f"ansage_{ts}.wav"
        tmp_voice = out_dir / f"voice_{ts}.wav"

        def worker():
            success = False
            try:
                self.ui(self.set_busy, True)
                self.ui(self.status_var.set, "Erzeuge Sprachdatei …")

                synthesize_tts_to_wav(tts_text, voice, tmp_voice, api_key)

                self.ui(self.status_var.set, "Mische Musik …")
                make_mix(tmp_voice, music_path, delay, gain, output_wav, output_mp3,
                        speed=speed, pitch_semitones=pitch)

                success = True
                self.ui(self.status_var.set, "Fertig. Dateien gespeichert.")
                self.ui(messagebox.showinfo, "Fertig",
                        f"Gespeichert in:\n{output_wav}\n{output_mp3}")

            except Exception as e:
                self.ui(messagebox.showerror, "Fehler", str(e))
                self.ui(self.status_var.set, "Fehler.")
            finally:
                self.ui(self.set_busy, False)
                if success:
                    open_folder(out_dir)

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    app = App()
    app.mainloop()

