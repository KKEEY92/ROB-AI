import os
from pathlib import Path
from typing import Optional, List, Tuple
import librosa
from mutagen.easyid3 import EasyID3
import matplotlib.pyplot as plt
import numpy as np

# --- 1. KONFIGURATION ---

SUPPORTED_FILES = ['.mp3', '.wav', '.aiff', '.flac']
SIMPLE_CAMELOT_MAP = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B'
}

CAMELOT_COLOR_MAP = {
    "1": "#ff6b6b",  # 1A/1B
    "2": "#ff8e3c",  # 2A/2B
    "3": "#ffc13b",  # 3A/3B
    "4": "#eaff5b",  # 4A/4B
    "5": "#86ff4b",  # 5A/5B
    "6": "#4bffa7",  # 6A/6B
    "7": "#4bffff",  # 7A/7B
    "8": "#4b86ff",  # 8A/8B
    "9": "#8e4bff",  # 9A/9B
    "10": "#c13bff", # 10A/10B
    "11": "#ff3bde", # 11A/11B
    "12": "#ff3b8e"  # 12A/12B
}

# --- 2. FUNKTIONEN ---

def find_music_files(music_folder: str) -> List[Path]:
    """Durchsucht einen Ordner rekursiv nach unterstützten Audiodateien."""
    found_files = []
    for root, _, files in os.walk(music_folder):
        for file in files:
            if Path(file).suffix.lower() in SUPPORTED_FILES:
                found_files.append(Path(root) / file)
    return found_files

def analyze_track(file_path: Path) -> Tuple[Optional[float], Optional[str]]:
    """Analysiert eine Audiodatei, um BPM und Tonart zu ermitteln."""
    try:
        y, sr = librosa.load(str(file_path), duration=120)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = round(float(tempo))
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_strengths = chroma.sum(axis=1)
        strongest_pitch_index = key_strengths.argmax()
        major_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key = major_keys[strongest_pitch_index]
        return bpm, key
    except Exception:
        return None, None

def get_camelot_key(key: str) -> Optional[str]:
    """Übersetzt eine Tonart in einen Camelot-Code."""
    return SIMPLE_CAMELOT_MAP.get(key)

def get_compatible_keys(camelot_key: str) -> List[str]:
    """Ermittelt harmonisch kompatible Tonarten basierend auf dem Camelot-Rad."""
    if not camelot_key:
        return []
    try:
        number = int(camelot_key[:-1])
        letter = camelot_key[-1]
    except (ValueError, IndexError):
        return []

    compatible_keys = [camelot_key]
    relative_letter = 'A' if letter == 'B' else 'B'
    compatible_keys.append(f"{number}{relative_letter}")
    next_number = number + 1 if number < 12 else 1
    compatible_keys.append(f"{next_number}{letter}")
    prev_number = number - 1 if number > 1 else 12
    compatible_keys.append(f"{prev_number}{letter}")
    return list(set(compatible_keys))

def write_metadata_to_file(file_path: Path, bpm: float, camelot_key: str) -> bool:
    """Schreibt BPM und Camelot-Key in die Metadaten einer MP3-Datei."""
    if file_path.suffix.lower() != '.mp3':
        return False
    try:
        audio = EasyID3(str(file_path))
        audio['tbpm'] = str(round(bpm))
        audio['tkey'] = camelot_key
        audio.save()
        return True
    except Exception:
        return False

def create_harmonic_playlist(all_tracks: List[dict], start_track_path: Path, max_bpm_diff: int = 5) -> Optional[str]:
    """Erstellt eine harmonische Playlist und gibt den Dateipfad zurück."""
    start_track = next((t for t in all_tracks if t['path'] == start_track_path), None)
    if not start_track or not start_track.get('camelot_key'):
        return None

    playlist = [start_track]
    remaining_tracks = [t for t in all_tracks if t != start_track and t.get('camelot_key')]
    current_track = start_track

    while remaining_tracks:
        compatible_keys = get_compatible_keys(current_track['camelot_key'])
        current_bpm = current_track['bpm']
        candidates = [
            t for t in remaining_tracks
            if t['camelot_key'] in compatible_keys and abs(t['bpm'] - current_bpm) <= max_bpm_diff
        ]
        if not candidates:
            break

        candidates.sort(key=lambda t: abs(t['bpm'] - current_bpm))
        next_track = candidates[0]
        playlist.append(next_track)
        remaining_tracks.remove(next_track)
        current_track = next_track

    playlist_filename = f"Harmonic Mix (starting with {start_track['path'].stem}).m3u"
    try:
        with open(playlist_filename, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for track in playlist:
                title = track['path'].stem
                f.write(f"#EXTINF:-1,{title}\n")
                f.write(str(track['path'].resolve()) + '\n')
        return playlist_filename
    except Exception:
        return None

def generate_waveform_image(file_path: Path, image_path: Path, color: str = "#1f6aa5"):
    """Generates a simple waveform image from an audio file."""
    try:
        # Load audio file with a low sample rate for performance
        y, sr = librosa.load(str(file_path), sr=11025, duration=180)

        # Create a plot with a specific size and transparent background
        fig, ax = plt.subplots(figsize=(6, 0.8), dpi=100)
        fig.patch.set_alpha(0)
        ax.patch.set_alpha(0)

        # Plot the waveform
        ax.plot(y, color=color, linewidth=0.5)

        # Fill under the plot
        ax.fill_between(range(len(y)), y, color=color, alpha=0.5)

        # Remove all axes, labels, and ticks for a clean look
        ax.axis('off')
        ax.margins(0)

        # Ensure tight layout
        plt.tight_layout(pad=0)

        # Save the figure
        plt.savefig(image_path, format='png', bbox_inches='tight', pad_inches=0, transparent=True)

        # Close the plot to free memory
        plt.close(fig)

        return True
    except Exception:
        return False
