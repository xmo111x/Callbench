import os
import threading
from pathlib import Path
from tkinter import *
from tkinter import ttk, messagebox, filedialog
from openai import OpenAI
from pydub import AudioSegment
import simpleaudio
import sys, subprocess

# ========= Basis-Konfiguration =========
TTS_MODEL = "gpt-4o-mini-tts"
VALID_VOICES = ["nova", "alloy", "shimmer", "coral", "echo", "verse",
                "fable", "onyx", "ballad", "ash", "sage", "marin", "cedar"]

OUTPUT_MP3 = Path("ansage_final.mp3")
OUTPUT_WAV = Path("ansage_final.wav")
TMP_VOICE = Path("voice.wav")

# ======== Hilfsfunktionen Audio ========
def adjust_voice(segment: AudioSegment, speed: float = 1.0, pitch_semitones: float = 0.0) -> AudioSegment:
    """
    Tempo und Tonhöhe anpassen (einfaches Resampling).
    - speed: 1.0 = normal, >1 schneller, <1 langsamer
    - pitch_semitones: +1 = einen Halbton höher, -1 = tiefer
    """
    # Tempo
    if speed != 1.0:
        new_frame_rate = int(segment.frame_rate * speed)
        segment = segment._spawn(segment.raw_data, overrides={'frame_rate': new_frame_rate})
        segment = segment.set_frame_rate(44100)

    # Pitch
    if pitch_semitones != 0.0:
        factor = 2 ** (pitch_semitones / 12.0)
        new_rate = int(segment.frame_rate * factor)
        segment = segment._spawn(segment.raw_data, overrides={'frame_rate': new_rate})
        segment = segment.set_frame_rate(44100)

    return segment

def stylize_text(raw: str, style: str) -> str:
    """
    Stil „freundlich/neutral/lebendig“ etc. NICHT per gesprochenem Hinweis,
    sondern durch minimale Prosodiezeichen im Text (… – ,) – so wird nichts mitgesprochen.
    """
    text = raw.strip()

    if style == "freundlich & ruhig":
        text = text.replace("Hallo,", "Hallo …")
        text = text.replace("Leider", "Leider …")
    elif style == "neutral":
        # keine Änderung
        pass
    elif style == "hell & freundlich":
        text = text.replace("Hallo,", "Hallo,")
    elif style == "lebendig":
        text = text.replace("Hallo,", "Hallo –")
    else:
        # fallback: keine Änderung
        pass

    return text

# ======== TTS + Mix ========
def synthesize_tts_to_wav(text: str, voice: str, out_wav: Path, api_key: str):
    client = OpenAI(api_key=api_key)
    with client.audio.speech.with_streaming_response.create(
        model=TTS_MODEL,
        voice=voice,
        input=text,
        response_format="wav"
    ) as resp:
        resp.stream_to_file(out_wav)

def make_mix(voice_wav: Path, music_path: Path, delay_ms: int, music_gain_db: int,
             out_wav: Path, out_mp3: Path,
             speed: float = 1.0, pitch_semitones: float = 0.0):
    voice = AudioSegment.from_file(voice_wav)

    # Speed/Pitch (nach dem TTS, damit nichts „roboterhaft“ wird)
    voice = adjust_voice(voice, speed=speed, pitch_semitones=pitch_semitones)

    # Stimme später starten lassen
    voice = AudioSegment.silent(duration=delay_ms) + voice

    if music_path and music_path.exists():
        music = AudioSegment.from_file(music_path) + music_gain_db
        # Loopen falls kürzer als Stimme
        if len(music) < len(voice):
            loops = (len(voice) // len(music)) + 1
            music = music * loops
        music = music[:len(voice)].fade_in(300)
        mix = voice.overlay(music)
    else:
        mix = voice

    # sanft ausblenden
    mix = mix.fade_out(400)

    # Export
    mix.export(out_wav, format="wav")
    mix.export(out_mp3, format="mp3", bitrate="192k")

# ======== GUI-Logik ========
class App(Tk):
    def __init__(self):
        super().__init__()
        self.title("Callbench")
        self.geometry("680x640")

        # --- Textfeld
        Label(self, text="Ansagetext:", font=("Arial", 11, "bold")).pack(anchor=W, padx=12, pady=(12,4))
        self.text_box = Text(self, height=10, width=70, wrap=WORD)
        self.text_box.pack(padx=12, pady=(0,10))
        self.text_box.insert(END,
            "Hallo, hier ist der Anrufbeantworter der Praxis. Leider können wir Ihren Anruf nicht entgegennehmen. "
            "Bitte hinterlassen Sie Ihren Namen und Ihre Telefonnummer. "
            "Wir rufen Sie sobald wie möglich zurück."
        )

        # --- Parameter-Frame
        frm = Frame(self)
        frm.pack(fill=X, padx=12, pady=6)

        # Stimme
        Label(frm, text="Stimme:", width=16).grid(row=0, column=0, sticky=W, pady=3)
        self.voice_var = StringVar(value="nova")
        ttk.Combobox(frm, textvariable=self.voice_var, values=VALID_VOICES, width=18, state="readonly").grid(row=0, column=1, sticky=W)

        # Stil (wir verändern Prosodie im Text)
        Label(frm, text="Stil:", width=16).grid(row=1, column=0, sticky=W, pady=3)
        self.style_var = StringVar(value="freundlich & ruhig")
        ttk.Combobox(frm, textvariable=self.style_var, values=["freundlich & ruhig", "neutral", "hell & freundlich", "lebendig"],
                     width=18, state="readonly").grid(row=1, column=1, sticky=W)

        # Start-Delay
        Label(frm, text="Start-Delay (ms):", width=16).grid(row=2, column=0, sticky=W, pady=3)
        self.delay_var = StringVar(value="1000")
        Entry(frm, textvariable=self.delay_var, width=10).grid(row=2, column=1, sticky=W)

        # Musik-Lautstärke
        Label(frm, text="Musik-Lautstärke (dB):", width=16).grid(row=3, column=0, sticky=W, pady=3)
        self.gain_var = StringVar(value="-18")
        Entry(frm, textvariable=self.gain_var, width=10).grid(row=3, column=1, sticky=W)

        # Musik-Datei
        Label(frm, text="Musik-Datei:", width=16).grid(row=4, column=0, sticky=W, pady=3)
        self.music_var = StringVar(value=str(Path("musik.mp3").resolve()))
        Entry(frm, textvariable=self.music_var, width=40).grid(row=4, column=1, sticky=W)
        Button(frm, text="Durchsuchen…", command=self.browse_music).grid(row=4, column=2, padx=6)

        # Tempo / Pitch
        Label(frm, text="Tempo-Faktor:", width=16).grid(row=5, column=0, sticky=W, pady=3)
        self.speed_var = StringVar(value="1.0")
        Entry(frm, textvariable=self.speed_var, width=10).grid(row=5, column=1, sticky=W)

        Label(frm, text="Pitch (Halbtöne):", width=16).grid(row=6, column=0, sticky=W, pady=3)
        self.pitch_var = StringVar(value="0")
        Entry(frm, textvariable=self.pitch_var, width=10).grid(row=6, column=1, sticky=W)

        # Buttons
        btn_frame = Frame(self)
        btn_frame.pack(pady=10)
        self.gen_btn = Button(btn_frame, text="🎙️  Ansage erzeugen", command=self.on_generate, bg="#4CAF50", fg="black", font=("Arial", 12, "bold"))
        self.gen_btn.grid(row=0, column=0, padx=8)
        

        # Status
        self.status_var = StringVar(value="Bereit.")
        Label(self, textvariable=self.status_var, anchor=W).pack(fill=X, padx=12, pady=(6,12))

    def browse_music(self):
        path = filedialog.askopenfilename(title="Musikdatei wählen",
                                          filetypes=[("Audio", "*.mp3 *.wav *.m4a *.flac *.ogg"), ("Alle Dateien", "*.*")])
        if path:
            self.music_var.set(path)

    def set_busy(self, busy: bool):
        self.gen_btn.config(state=DISABLED if busy else NORMAL)
        self.status_var.set("Bitte warten …" if busy else "Bereit.")

    def on_generate(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            messagebox.showerror("Fehlender API Key", "Bitte setze OPENAI_API_KEY als Umgebungsvariable.")
            return

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

        def worker():
            try:
                self.set_busy(True)
                self.status_var.set("Erzeuge Sprachdatei …")
                synthesize_tts_to_wav(tts_text, voice, TMP_VOICE, api_key)

                self.status_var.set("Mische Musik …")
                make_mix(TMP_VOICE, music_path, delay, gain, OUTPUT_WAV, OUTPUT_MP3,
                         speed=speed, pitch_semitones=pitch)

                self.status_var.set("Fertig. Dateien gespeichert.")
                messagebox.showinfo("Fertig ✅",
                    f"Gespeichert:\n{OUTPUT_WAV.resolve()}\n{OUTPUT_MP3.resolve()}")
            except Exception as e:
                messagebox.showerror("Fehler", str(e))
                self.status_var.set("Fehler.")
            finally:
                self.set_busy(False)

        threading.Thread(target=worker, daemon=True).start()



if __name__ == "__main__":
    app = App()
    app.mainloop()

