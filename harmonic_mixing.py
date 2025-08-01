# Harmonic Mixing & Playlist Skript
# ==================================
# Ein Tool zur Analyse von BPM/Tonart, zum Schreiben von Metadaten
# und zum Erstellen von harmonischen Playlists für Traktor.

import os
from pathlib import Path
from typing import Optional, List, Tuple
import librosa
from mutagen.easyid3 import EasyID3

# --- 1. KONFIGURATION ---

# Eine Liste der Dateitypen, die das Skript verarbeiten soll.
SUPPORTED_FILES = ['.mp3', '.wav', '.aiff', '.flac']

# Das Mapping von musikalischen Tonarten zum Camelot-System.
# HINWEIS: Dies ist ein vereinfachtes Mapping, das auf den Ergebnissen
# der librosa-Analyse basiert. Es kann bei Bedarf erweitert werden.
SIMPLE_CAMELOT_MAP = {
    'C': '8B', 'C#': '3B', 'D': '10B', 'D#': '5B', 'E': '12B', 'F': '7B',
    'F#': '2B', 'G': '9B', 'G#': '4B', 'A': '11B', 'A#': '6B', 'B': '1B'
}


# --- 2. FUNKTIONEN ---

def find_music_files(music_folder: str) -> List[Path]:
    """Durchsucht einen Ordner rekursiv nach unterstützten Audiodateien."""
    found_files = []
    print(f"INFO: Durchsuche den Ordner: {music_folder}")
    for root, _, files in os.walk(music_folder):
        for file in files:
            if Path(file).suffix.lower() in SUPPORTED_FILES:
                found_files.append(Path(root) / file)
    print(f"INFO: {len(found_files)} Musikdateien gefunden!")
    return found_files

def analyze_track(file_path: Path) -> Tuple[Optional[float], Optional[str]]:
    """Analysiert eine Audiodatei, um BPM und Tonart zu ermitteln."""
    try:
        y, sr = librosa.load(str(file_path), duration=120)  # Lade die ersten 2 Minuten für schnellere Analyse

        # BPM ermitteln
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        bpm = round(tempo)

        # Tonart ermitteln (vereinfachte Methode)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key_strengths = chroma.sum(axis=1)
        strongest_pitch_index = key_strengths.argmax()

        major_keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        key = major_keys[strongest_pitch_index]

        return bpm, key
    except Exception as e:
        print(f"WARNUNG: Fehler bei der Analyse von '{file_path.name}': {e}")
        return None, None

def get_camelot_key(key: str) -> Optional[str]:
    """Übersetzt eine Tonart in einen Camelot-Code."""
    return SIMPLE_CAMELOT_MAP.get(key)

def get_compatible_keys(camelot_key: str) -> List[str]:
    """Ermittelt harmonisch kompatible Tonarten basierend auf dem Camelot-Rad."""
    if not camelot_key:
        return []

    try:
        # Extrahiere Nummer und Buchstabe aus dem Key (z.B. "8B" -> 8, "B")
        number = int(camelot_key[:-1])
        letter = camelot_key[-1]
    except (ValueError, IndexError):
        # Fange ungültige Formate ab
        print(f"WARNUNG: Ungültiger Camelot-Code '{camelot_key}' erhalten.")
        return []

    compatible_keys = [camelot_key]

    # 1. Füge den relativen Dur/Moll-Schlüssel hinzu (z.B. 8A <-> 8B)
    relative_letter = 'A' if letter == 'B' else 'B'
    compatible_keys.append(f"{number}{relative_letter}")

    # 2. Füge den nächsten Schlüssel im Uhrzeigersinn hinzu (z.B. 8B -> 9B)
    #    Das Rad wickelt sich von 12 auf 1 um.
    next_number = number + 1 if number < 12 else 1
    compatible_keys.append(f"{next_number}{letter}")

    # 3. Füge den vorherigen Schlüssel gegen den Uhrzeigersinn hinzu (z.B. 8B -> 7B)
    #    Das Rad wickelt sich von 1 auf 12 um.
    prev_number = number - 1 if number > 1 else 12
    compatible_keys.append(f"{prev_number}{letter}")

    return list(set(compatible_keys)) # Entferne Duplikate, falls vorhanden

def write_metadata_to_file(file_path: Path, bpm: float, camelot_key: str):
    """Schreibt BPM und Camelot-Key in die Metadaten einer MP3-Datei."""
    # EasyID3 ist am besten für MP3-Dateien geeignet.
    if file_path.suffix.lower() != '.mp3':
        print(f"INFO: Das Schreiben von Metadaten wird für '{file_path.name}' übersprungen (nur .mp3 wird unterstützt).")
        return

    try:
        audio = EasyID3(str(file_path))
        # Zuweisung fügt die Tags hinzu, falls sie nicht existieren.
        # Die Keys für EasyID3 sind lowercase Versionen der ID3-Frame-Namen.
        audio['tbpm'] = str(round(bpm))
        audio['tkey'] = camelot_key
        audio.save()
        print(f"INFO: Metadaten für '{file_path.name}' geschrieben: BPM={round(bpm)}, Key={camelot_key}")
    except Exception as e:
        # Fange mögliche Fehler ab, z.B. wenn die Datei beschädigt ist oder keine Schreibrechte bestehen.
        print(f"WARNUNG: Fehler beim Schreiben der Metadaten für '{file_path.name}': {e}")


# --- 3. PLAYLIST-ERSTELLUNG ---

def create_harmonic_playlist(all_tracks: List[dict], start_track_path: Path, max_bpm_diff: int = 5):
    """Erstellt eine harmonische Playlist basierend auf einem Start-Track."""

    start_track = next((t for t in all_tracks if t['path'] == start_track_path), None)
    if not start_track or not start_track.get('camelot_key'):
        print(f"FEHLER: Der Start-Track '{start_track_path.name}' konnte nicht gefunden werden oder hat keine Tonart-Analyse.")
        return

    print(f"\nINFO: Erstelle eine harmonische Playlist, beginnend mit '{start_track['path'].name}'.")
    print(f"INFO: Maximale BPM-Differenz für den Mix: {max_bpm_diff} BPM.")

    playlist = [start_track]
    # Erstelle eine Liste von Tracks, die für die Playlist zur Verfügung stehen.
    # Schließe Tracks ohne Tonart aus.
    remaining_tracks = [t for t in all_tracks if t != start_track and t.get('camelot_key')]

    current_track = start_track

    while remaining_tracks:
        compatible_keys = get_compatible_keys(current_track['camelot_key'])
        current_bpm = current_track['bpm']

        # Finde alle potenziell passenden Tracks basierend auf Tonart und BPM.
        candidates = []
        for track in remaining_tracks:
            if track['camelot_key'] in compatible_keys and abs(track['bpm'] - current_bpm) <= max_bpm_diff:
                candidates.append(track)

        if not candidates:
            print("INFO: Keine weiteren kompatiblen Tracks gefunden. Playlist wird abgeschlossen.")
            break

        # Wähle den besten nächsten Track aus: der mit dem geringsten BPM-Unterschied.
        candidates.sort(key=lambda t: abs(t['bpm'] - current_bpm))
        next_track = candidates[0]

        playlist.append(next_track)
        remaining_tracks.remove(next_track)
        current_track = next_track
        print(f"INFO: Nächster Track im Mix: '{current_track['path'].name}' (Key: {current_track['camelot_key']}, BPM: {current_track['bpm']})")

    # Schreibe die finale Playlist in eine .m3u-Datei.
    playlist_filename = f"Harmonic Mix (starting with {start_track['path'].stem}).m3u"
    try:
        with open(playlist_filename, 'w', encoding='utf-8') as f:
            # M3U-Header
            f.write("#EXTM3U\n")
            for track in playlist:
                # Füge zusätzliche Informationen für erweiterte M3U-Player hinzu
                title = track['path'].stem
                f.write(f"#EXTINF:-1,{title}\n")
                # Schreibe den absoluten Pfad zur Datei
                f.write(str(track['path'].resolve()) + '\n')
        print(f"\nERFOLG: Playlist '{playlist_filename}' mit {len(playlist)} Tracks wurde erstellt!")
    except Exception as e:
        print(f"FEHLER: Die Playlist-Datei konnte nicht geschrieben werden: {e}")


# --- 4. HAUPTFUNKTION ---

def main():
    """Die Hauptfunktion, die den gesamten Prozess steuert."""
    print("=" * 50)
    print("Harmonic Mixing & Playlist Skript")
    print("=" * 50)

    # 1. Musikordner vom Benutzer abfragen
    music_folder = input("Bitte geben Sie den Pfad zu Ihrem Musikordner ein: ")
    if not Path(music_folder).is_dir():
        print(f"FEHLER: Der Ordner '{music_folder}' wurde nicht gefunden.")
        return

    # 2. Musikdateien finden
    music_files = find_music_files(music_folder)
    if not music_files:
        print("INFO: Keine unterstützten Musikdateien im Ordner gefunden.")
        return

    # 3. Alle Dateien analysieren und Metadaten schreiben
    print("\n--- Starte Analyse der Tracks ---")
    all_analyzed_tracks = []
    for index, file_path in enumerate(music_files):
        print(f"\n({index + 1}/{len(music_files)}) Analysiere: {file_path.name}")
        bpm, key = analyze_track(file_path)

        if bpm and key:
            camelot_key = get_camelot_key(key)
            if camelot_key:
                print(f"-> Ergebnis: {round(bpm)} BPM, Tonart: {key} ({camelot_key})")
                track_info = {'path': file_path, 'bpm': bpm, 'camelot_key': camelot_key}
                all_analyzed_tracks.append(track_info)
                # Metadaten nur für MP3s schreiben
                write_metadata_to_file(file_path, bpm, camelot_key)
            else:
                print(f"-> Ergebnis: {round(bpm)} BPM, Tonart: {key} (Kein Camelot-Mapping gefunden)")
        else:
            print("-> Analyse fehlgeschlagen.")

    print("\n--- Analyse abgeschlossen ---")

    # 4. Playlist-Erstellung anbieten
    if not all_analyzed_tracks:
        print("\nKeine Tracks konnten erfolgreich analysiert werden. Playlist-Erstellung nicht möglich.")
        return

    while True:
        create_playlist_choice = input("\nMöchten Sie eine harmonische Playlist erstellen? (ja/nein): ").lower()
        if create_playlist_choice in ['ja', 'j', 'yes']:
            break
        elif create_playlist_choice in ['nein', 'n', 'no']:
            print("Skript wird beendet. Auf Wiedersehen!")
            return
        else:
            print("Ungültige Eingabe. Bitte antworten Sie mit 'ja' oder 'nein'.")

    # 5. Start-Track für die Playlist auswählen
    print("\nWählen Sie einen Start-Track für die Playlist aus:")
    # Filtere nur Tracks, die auch wirklich analysiert wurden
    selectable_tracks = [t for t in all_analyzed_tracks if t.get('camelot_key')]
    for i, track in enumerate(selectable_tracks):
        print(f"  {i + 1}: {track['path'].name} (Key: {track['camelot_key']}, BPM: {track['bpm']})")

    if not selectable_tracks:
        print("\nKeine Tracks mit gültiger Tonart für Playlist-Erstellung gefunden.")
        return

    while True:
        try:
            start_track_num = int(input(f"\nGeben Sie die Nummer des Start-Tracks ein (1-{len(selectable_tracks)}): "))
            if 1 <= start_track_num <= len(selectable_tracks):
                start_track = selectable_tracks[start_track_num - 1]
                create_harmonic_playlist(all_analyzed_tracks, start_track['path'])
                break
            else:
                print(f"FEHLER: Ungültige Nummer. Bitte zwischen 1 und {len(selectable_tracks)} wählen.")
        except ValueError:
            print("FEHLER: Bitte geben Sie eine gültige Zahl ein.")


if __name__ == "__main__":
    main()
