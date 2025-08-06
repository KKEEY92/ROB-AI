import os
import json
from pathlib import Path
from typing import Optional, List, Tuple, Dict, Any
import librosa
import soundfile as sf
import pyloudnorm as pyln
from pydub import AudioSegment
import mutagen
from mutagen.easyid3 import EasyID3
import musicbrainzngs
import requests
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

def analyze_track_full(file_path: Path) -> Optional[Dict[str, Any]]:
    """
    Analysiert eine Audiodatei für BPM, Tonart, Lautheit und Helligkeit.
    Gibt ein Dictionary mit allen Analyseergebnissen zurück.
    """
    try:
        # --- Standard-Analyse (BPM, Tonart) ---
        y, sr = librosa.load(str(file_path), sr=44100, duration=180)

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = float(tempo)

        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_strengths = chroma.sum(axis=1)
        strongest_pitch_index = key_strengths.argmax()
        major_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key = major_keys[strongest_pitch_index]

        # --- Erweiterte Analyse ---
        # 1. Lautheit (LUFS)
        # pyloudnorm requires the data to be read by soundfile
        data, rate = sf.read(file_path)
        meter = pyln.Meter(rate)
        loudness = meter.integrated_loudness(data)

        # 2. Helligkeit (Spectral Centroid)
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

        return {
            "bpm": bpm,
            "key": key,
            "loudness": loudness,
            "brightness": spectral_centroid
        }
    except Exception:
        return None

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

# --- 5. ONLINE METADATA ---

musicbrainzngs.set_useragent("HarmonicMixingStudio", "0.1", "https://github.com/yourname/yourrepo")

def fetch_musicbrainz_release_id(file_path: Path) -> Optional[str]:
    """Tries to find a MusicBrainz release ID for a given file."""
    try:
        audio = mutagen.File(file_path, easy=True)
        if not audio:
            return None

        artist = audio.get('artist', [''])[0]
        album = audio.get('album', [''])[0]

        if not artist or not album:
            return None

        result = musicbrainzngs.search_releases(artist=artist, release=album, limit=1)
        if result['release-list']:
            return result['release-list'][0]['id']
        return None
    except Exception:
        return None

def download_cover_art(release_id: str) -> Optional[bytes]:
    """Downloads the front cover art for a given MusicBrainz release ID."""
    try:
        # The Cover Art Archive uses the release ID directly
        url = f"https://coverartarchive.org/release/{release_id}/front"
        response = requests.get(url, allow_redirects=True, timeout=10)
        # The API redirects to the actual image, so we don't need to check for 307
        if response.status_code == 200:
            return response.content
        return None
    except Exception:
        return None

def embed_cover_art(file_path: Path, image_data: bytes) -> bool:
    """Embeds downloaded image data as cover art into an audio file."""
    try:
        audio = mutagen.File(file_path)
        if audio is None:
            return False

        if file_path.suffix.lower() == '.mp3':
            pic = mutagen.id3.APIC(
                encoding=3,  # 3 is for utf-8
                mime='image/jpeg', # or image/png
                type=3,  # 3 is for the cover (front) image
                desc='Cover',
                data=image_data
            )
            audio.tags.add(pic)
        elif file_path.suffix.lower() == '.flac':
            pic = mutagen.flac.Picture()
            pic.type = 3
            pic.mime = 'image/jpeg'
            pic.desc = 'Cover'
            pic.data = image_data
            audio.add_picture(pic)
        else:
            # Other formats might not be supported or require different handling
            return False

        audio.save()
        return True
    except Exception:
        return False

# --- 4. AUDIO CONVERSION ---

def convert_audio(source_path: Path, output_path: Path, format: str, sample_rate: int, bitrate: Optional[str], channels: int) -> bool:
    """
    Converts an audio file to a different format with specified parameters.
    """
    try:
        audio = AudioSegment.from_file(source_path)

        # Set channels
        if channels is not None:
            audio = audio.set_channels(channels)

        # Set sample rate
        if sample_rate is not None:
            audio = audio.set_frame_rate(sample_rate)

        # Prepare export parameters
        export_params = {}
        if format == 'mp3' and bitrate is not None:
            export_params['bitrate'] = bitrate

        # Export the file
        audio.export(output_path, format=format, parameters=export_params)

        return True
    except Exception as e:
        print(f"Error during conversion: {e}") # For debugging
        return False

# --- 3. LIBRARY PERSISTENCE ---

def save_library(library_data: Dict[str, Any], file_path: str):
    """Saves the library data to a JSON file."""
    try:
        # Convert Path objects to strings for JSON serialization
        def convert_paths_to_strings(obj):
            if isinstance(obj, list):
                return [convert_paths_to_strings(item) for item in obj]
            if isinstance(obj, dict):
                return {k: convert_paths_to_strings(v) for k, v in obj.items()}
            if isinstance(obj, Path):
                return str(obj)
            return obj

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(convert_paths_to_strings(library_data), f, indent=4)
        return True
    except Exception:
        return False

def load_library(file_path: str) -> Dict[str, Any]:
    """Loads the library data from a JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            library_data = json.load(f)

        # Convert string paths back to Path objects
        def convert_strings_to_paths(obj):
            if isinstance(obj, list):
                return [convert_strings_to_paths(item) for item in obj]
            if isinstance(obj, dict):
                # Specifically look for a 'path' key to convert
                return {k: Path(v) if k == 'path' else convert_strings_to_paths(v) for k, v in obj.items()}
            return obj

        return convert_strings_to_paths(library_data)
    except (FileNotFoundError, json.JSONDecodeError):
        # If file doesn't exist or is empty/corrupt, return a default structure
        return {"collection": [], "playlists": {}}

def create_harmonic_playlist(all_tracks: List[dict], start_track_path: Path, max_bpm_diff: int = 5) -> Optional[List[Dict]]:
    """Erstellt eine harmonische Playlist und gibt die sortierte Track-Liste zurück."""
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

    return playlist

def export_playlist_to_m3u(playlist_name: str, tracks: List[Dict]) -> bool:
    """Exportiert eine Track-Liste in eine .m3u-Datei."""
    # Sanitize playlist name for use as a filename
    safe_filename = "".join([c for c in playlist_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    if not safe_filename:
        safe_filename = "Untitled Playlist"
    playlist_filename = f"{safe_filename}.m3u"

    try:
        with open(playlist_filename, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            for track in tracks:
                title = track['path'].stem
                f.write(f"#EXTINF:-1,{title}\n")
                f.write(str(track['path'].resolve()) + '\n')
        return True
    except Exception:
        return False

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
