import customtkinter
import tkinter
from tkinter import filedialog, messagebox
from PIL import Image
import analysis_engine as engine
import threading
import time
import os
import pygame

# Set the theme and color scheme for the application
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # --- Instance variables ---
        self.library_file = "library.json"
        self.library_data = {"collection": [], "playlists": {}}
        self.selected_track_path = None
        self.selected_playlist_name = None
        self.is_playing = False
        self.waveform_cache_dir = "waveform_cache"
        if not os.path.exists(self.waveform_cache_dir):
            os.makedirs(self.waveform_cache_dir)

        # --- Initialize Pygame Mixer ---
        pygame.init()
        pygame.mixer.init()

        # --- Configure the main window ---
        self.title("Harmonic Mixing Studio")
        self.geometry("1200x600")

        # --- Create the main grid layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Create a top-level frame for controls ---
        self.control_frame = customtkinter.CTkFrame(self, height=80)
        self.control_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")

        self.add_folder_button = customtkinter.CTkButton(self.control_frame, text="Load Music Folder", command=self.load_folder)
        self.add_folder_button.pack(side="left", padx=10, pady=10)

        self.analyze_button = customtkinter.CTkButton(self.control_frame, text="Analyze Tracks", state="disabled", command=self.start_analysis_thread)
        self.analyze_button.pack(side="left", padx=10, pady=10)

        self.playlist_button = customtkinter.CTkButton(self.control_frame, text="Create Playlist", state="disabled", command=self.create_playlist)
        self.playlist_button.pack(side="left", padx=10, pady=10)

        # --- Progress Bar and Labels ---
        self.progress_bar = customtkinter.CTkProgressBar(self.control_frame, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=10, pady=10)

        self.progress_details_label = customtkinter.CTkLabel(self.control_frame, text="", anchor="e")
        self.progress_details_label.pack(side="right", padx=10)

        self.eta_label = customtkinter.CTkLabel(self.control_frame, text="", anchor="e")
        self.eta_label.pack(side="right", padx=10)


        # --- Create the main content layout (Navigation + Track List) ---
        self.main_content_frame = customtkinter.CTkFrame(self)
        self.main_content_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")
        self.grid_rowconfigure(1, weight=1)
        self.main_content_frame.grid_columnconfigure(1, weight=1)

        # --- Navigation Pane ---
        self.nav_pane = customtkinter.CTkFrame(self.main_content_frame, width=200, corner_radius=5)
        self.nav_pane.grid(row=0, column=0, padx=10, pady=10, sticky="nsw")

        self.nav_label = customtkinter.CTkLabel(self.nav_pane, text="Library", font=customtkinter.CTkFont(size=18, weight="bold"))
        self.nav_label.pack(pady=10, padx=20)

        self.collection_button = customtkinter.CTkButton(self.nav_pane, text="Track Collection", command=self.show_track_collection, corner_radius=5)
        self.collection_button.pack(pady=5, padx=10, fill="x")

        self.playlists_button = customtkinter.CTkButton(self.nav_pane, text="Playlists", command=self.show_playlists_view, corner_radius=5)
        self.playlists_button.pack(pady=5, padx=10, fill="x")

        self.delete_playlist_button = customtkinter.CTkButton(self.nav_pane, text="Delete Playlist", state="disabled", command=self.delete_selected_playlist, fg_color="transparent", border_color="#ff4d4d", border_width=1, hover_color="#ff4d4d")
        self.delete_playlist_button.pack(pady=(10,5), padx=10, fill="x")

        # --- Add a separator and playlist editing controls ---
        self.separator = customtkinter.CTkFrame(self.nav_pane, height=2, fg_color="gray20")
        self.separator.pack(fill="x", padx=10, pady=10)

        self.edit_label = customtkinter.CTkLabel(self.nav_pane, text="Playlist Editing", font=customtkinter.CTkFont(size=16, weight="bold"))
        self.edit_label.pack(pady=5)

        self.move_up_button = customtkinter.CTkButton(self.nav_pane, text="Move Track Up", state="disabled", command=self.move_track_up)
        self.move_up_button.pack(pady=5, padx=10, fill="x")

        self.move_down_button = customtkinter.CTkButton(self.nav_pane, text="Move Track Down", state="disabled", command=self.move_track_down)
        self.move_down_button.pack(pady=5, padx=10, fill="x")

        # --- Content Pane (for the track list) ---
        self.content_pane = customtkinter.CTkFrame(self.main_content_frame, corner_radius=5)
        self.content_pane.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.content_pane.grid_rowconfigure(0, weight=1)
        self.content_pane.grid_columnconfigure(0, weight=1)

        # --- Create a scrollable frame for the track list inside the content pane ---
        self.track_list_frame = customtkinter.CTkScrollableFrame(self.content_pane, label_text="Track Collection")
        self.track_list_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- Create a scrollable frame for the PLAYLIST list ---
        self.playlist_list_frame = customtkinter.CTkScrollableFrame(self.content_pane)
        self.playlist_list_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")
        self.playlist_list_frame.grid_remove() # Hide it by default

        # --- Status Label ---
        self.status_label = customtkinter.CTkLabel(self, text="Load a folder to begin.", anchor="w")
        self.status_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

        # --- Player Frame ---
        self.player_frame = customtkinter.CTkFrame(self, height=60)
        self.player_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="ew")
        self.player_frame.grid_columnconfigure(3, weight=1)

        self.play_pause_button = customtkinter.CTkButton(self.player_frame, text="Play", width=60, command=self.play_pause_track, state="disabled")
        self.play_pause_button.grid(row=0, column=0, padx=(10,5), pady=5)

        self.stop_button = customtkinter.CTkButton(self.player_frame, text="Stop", width=60, command=self.stop_track, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=5, pady=5)

        self.time_label = customtkinter.CTkLabel(self.player_frame, text="00:00 / 00:00")
        self.time_label.grid(row=0, column=2, padx=5, pady=5)

        self.scrub_bar = customtkinter.CTkSlider(self.player_frame, from_=0, to=100, command=None)
        self.scrub_bar.set(0)
        self.scrub_bar.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

        # --- Load initial data and display it ---
        self.load_app_library()
        self.show_track_collection()

    def load_app_library(self):
        """Loads the library from the JSON file on startup."""
        self.library_data = engine.load_library(self.library_file)
        self.status_label.configure(text=f"Loaded {len(self.library_data['collection'])} tracks from library.")

    def save_app_library(self):
        """Saves the current library state to the JSON file."""
        engine.save_library(self.library_data, self.library_file)
        self.status_label.configure(text=f"Library saved. Total tracks: {len(self.library_data['collection'])}")

    def show_track_collection(self):
        """Updates the view to show the main track collection."""
        self.track_list_frame.grid()
        self.playlist_list_frame.grid_remove()
        self.delete_playlist_button.configure(state="disabled")
        self.move_up_button.configure(state="disabled")
        self.move_down_button.configure(state="disabled")
        self.selected_playlist_name = None
        self.update_track_list_display(self.library_data["collection"])

    def show_playlists_view(self):
        """Updates the view to show the list of playlists."""
        self.track_list_frame.grid_remove()
        self.playlist_list_frame.grid()
        self.move_up_button.configure(state="disabled")
        self.move_down_button.configure(state="disabled")
        self.update_playlists_display()
        self.status_label.configure(text="Playlists view. Select a playlist to view its content.")


    def load_folder(self):
        """Opens a dialog to select a folder and adds new music files to the collection."""
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        # --- Reset UI state for analysis ---
        self.progress_bar.set(0)
        self.progress_details_label.configure(text="")
        self.eta_label.configure(text="")
        self.selected_track_path = None

        newly_found_files = engine.find_music_files(folder_path)

        # Filter out files that are already in the library collection
        existing_paths = {track['path'] for track in self.library_data['collection']}
        self.files_to_analyze = [p for p in newly_found_files if p not in existing_paths]

        if self.files_to_analyze:
            self.status_label.configure(text=f"{len(self.files_to_analyze)} new tracks found. Ready to analyze.")
            self.analyze_button.configure(state="normal")
        else:
            self.status_label.configure(text="No new music files found in the selected folder.")
            self.analyze_button.configure(state="disabled")

    def update_track_list_display(self, tracks_to_display):
        """Clears and redraws the track list in the UI with a given list of tracks."""
        for widget in self.track_list_frame.winfo_children():
            widget.destroy()

        headers = ["Track Name", "BPM", "Key", "Loudness", "Brightness", "Waveform"]
        column_weights = [3, 1, 1, 1, 1, 4]

        for i, header in enumerate(headers):
            self.track_list_frame.grid_columnconfigure(i, weight=column_weights[i])
            header_label = customtkinter.CTkLabel(self.track_list_frame, text=header, font=customtkinter.CTkFont(weight="bold"))
            header_label.grid(row=0, column=i, padx=10, pady=5, sticky="w")

        for i, track_data in enumerate(tracks_to_display):
            file_path = track_data['path']
            track_name = file_path.stem

            bpm_val = track_data.get('bpm')
            bpm_text = f"{bpm_val:.2f}" if isinstance(bpm_val, float) else "--"

            key_text = track_data.get('camelot_key', '--')

            loudness_val = track_data.get('loudness')
            loudness_text = f"{loudness_val:.2f} LUFS" if isinstance(loudness_val, float) else "--"

            brightness_val = track_data.get('brightness')
            brightness_text = f"{brightness_val:.0f}" if isinstance(brightness_val, float) else "--"

            waveform_path = track_data.get('waveform_path')

            track_frame = customtkinter.CTkFrame(self.track_list_frame, corner_radius=5)
            track_frame.grid(row=i + 1, column=0, columnspan=len(headers), padx=5, pady=2, sticky="ew")
            for j, weight in enumerate(column_weights):
                track_frame.grid_columnconfigure(j, weight=weight)

            if self.selected_track_path == file_path:
                track_frame.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["hover_color"])

            track_button = customtkinter.CTkButton(track_frame, text=track_name, anchor="w", fg_color="transparent", text_color=customtkinter.ThemeManager.theme["CTkLabel"]["text_color"],
                                                   command=lambda p=file_path: self.track_selected(p))
            track_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

            bpm_label = customtkinter.CTkLabel(track_frame, text=bpm_text, anchor="w")
            bpm_label.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

            key_label = customtkinter.CTkLabel(track_frame, text=key_text, anchor="w")
            key_label.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

            loudness_label = customtkinter.CTkLabel(track_frame, text=loudness_text, anchor="w")
            loudness_label.grid(row=0, column=3, padx=10, pady=5, sticky="ew")

            brightness_label = customtkinter.CTkLabel(track_frame, text=brightness_text, anchor="w")
            brightness_label.grid(row=0, column=4, padx=10, pady=5, sticky="ew")

            if waveform_path and os.path.exists(waveform_path):
                try:
                    img = Image.open(waveform_path)
                    ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(160, 24))
                    waveform_label = customtkinter.CTkLabel(track_frame, image=ctk_img, text="")
                    waveform_label.grid(row=0, column=5, padx=10, pady=2, sticky="w")
                except Exception:
                    placeholder = customtkinter.CTkLabel(track_frame, text="Error", anchor="w")
                    placeholder.grid(row=0, column=5, padx=10, pady=5, sticky="ew")


    def track_selected(self, file_path):
        """Handles the event when a track is selected from the list."""
        self.selected_track_path = file_path
        self.load_track_for_playback(file_path)

        # Enable create playlist button regardless of view
        self.playlist_button.configure(state="normal")
        self.status_label.configure(text=f"Selected: {file_path.stem}")

        # If we are in a playlist view, enable editing buttons
        if self.selected_playlist_name:
            self.move_up_button.configure(state="normal")
            self.move_down_button.configure(state="normal")
            self.update_track_list_display(self.library_data["playlists"][self.selected_playlist_name])
        else:
            self.update_track_list_display(self.library_data["collection"])

    def load_track_for_playback(self, file_path):
        """Loads a track into the pygame mixer."""
        try:
            self.stop_track() # Stop any currently playing track
            pygame.mixer.music.load(file_path)

            # Get track length
            audio = pygame.mixer.Sound(file_path)
            self.track_length = audio.get_length()

            self.scrub_bar.configure(to=self.track_length)
            self.time_label.configure(text=f"00:00 / {time.strftime('%M:%S', time.gmtime(self.track_length))}")
            self.play_pause_button.configure(state="normal")
            self.stop_button.configure(state="normal")
        except Exception as e:
            self.play_pause_button.configure(state="disabled")
            self.stop_button.configure(state="disabled")
            self.time_label.configure(text="00:00 / 00:00")
            self.status_label.configure(text=f"Error loading track: {e}")

    def play_pause_track(self):
        """Toggles play/pause for the loaded track."""
        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
            self.play_pause_button.configure(text="Play")
        else:
            self.is_playing = True
            pygame.mixer.music.unpause() if pygame.mixer.music.get_pos() > 0 else pygame.mixer.music.play()
            self.play_pause_button.configure(text="Pause")
            self.start_playback_progress_thread()

    def stop_track(self):
        """Stops playback and resets the player."""
        self.is_playing = False
        pygame.mixer.music.stop()
        self.play_pause_button.configure(text="Play")
        self.scrub_bar.set(0)
        self.time_label.configure(text=f"00:00 / {time.strftime('%M:%S', time.gmtime(getattr(self, 'track_length', 0)))}")

    def start_playback_progress_thread(self):
        """Starts the thread that updates the playback progress bar and time."""
        progress_thread = threading.Thread(target=self.update_playback_progress, daemon=True)
        progress_thread.start()

    def update_playback_progress(self):
        """Updates the scrub bar and time label while music is playing."""
        while self.is_playing and pygame.mixer.music.get_busy():
            current_pos = pygame.mixer.music.get_pos() / 1000  # get_pos is in milliseconds
            self.scrub_bar.set(current_pos)

            current_time_str = time.strftime('%M:%S', time.gmtime(current_pos))
            total_time_str = time.strftime('%M:%S', time.gmtime(self.track_length))
            self.time_label.configure(text=f"{current_time_str} / {total_time_str}")

            time.sleep(0.1)

        if self.is_playing: # If the song finished naturally
            self.stop_track()

    def create_playlist(self):
        """Prompts for a playlist name and saves the new harmonic playlist."""
        if not self.selected_track_path:
            messagebox.showwarning("Warning", "Please select a starting track first.")
            return

        dialog = customtkinter.CTkInputDialog(text="Enter a name for the new playlist:", title="Create Playlist")
        playlist_name = dialog.get_input()

        if not playlist_name:
            return # User cancelled

        self.status_label.configure(text=f"Creating playlist '{playlist_name}'...")

        # Generate the ordered list of tracks
        new_playlist_tracks = engine.create_harmonic_playlist(self.library_data["collection"], self.selected_track_path)

        if new_playlist_tracks:
            # Save the playlist to the library
            self.library_data["playlists"][playlist_name] = new_playlist_tracks
            self.save_app_library()

            # Export to .m3u file
            engine.export_playlist_to_m3u(playlist_name, new_playlist_tracks)

            self.status_label.configure(text=f"Playlist '{playlist_name}' created and saved.")
            messagebox.showinfo("Success", f"Playlist '{playlist_name}' was created and saved.")
            self.update_playlists_display() # Refresh the playlist view
        else:
            self.status_label.configure(text="Failed to create playlist.")
            messagebox.showerror("Error", "Could not create the harmonic playlist.")

    def update_playlists_display(self):
        """Clears and redraws the list of playlists in the UI."""
        for widget in self.playlist_list_frame.winfo_children():
            widget.destroy()

        header_label = customtkinter.CTkLabel(self.playlist_list_frame, text="Playlists", font=customtkinter.CTkFont(size=16, weight="bold"))
        header_label.pack(anchor="w", padx=10, pady=5)

        for playlist_name in self.library_data["playlists"].keys():
            button = customtkinter.CTkButton(self.playlist_list_frame, text=playlist_name, fg_color="transparent", anchor="w",
                                             command=lambda name=playlist_name: self.show_playlist_content(name))
            button.pack(fill="x", padx=5)

    def show_playlist_content(self, playlist_name: str):
        """Displays the tracks for a selected playlist."""
        self.track_list_frame.configure(label_text=f"Playlist: {playlist_name}")

        self.selected_playlist_name = playlist_name
        self.delete_playlist_button.configure(state="normal")

        playlist_tracks = self.library_data["playlists"].get(playlist_name, [])

        self.update_track_list_display(playlist_tracks)
        self.track_list_frame.grid()
        self.playlist_list_frame.grid_remove()

    def delete_selected_playlist(self):
        """Deletes the currently selected playlist after confirmation."""
        if not self.selected_playlist_name:
            return

        confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the playlist '{self.selected_playlist_name}'?\nThis cannot be undone.")

        if confirm:
            if self.selected_playlist_name in self.library_data["playlists"]:
                del self.library_data["playlists"][self.selected_playlist_name]
                self.save_app_library()
                self.status_label.configure(text=f"Deleted playlist: {self.selected_playlist_name}")
                self.selected_playlist_name = None
                self.delete_playlist_button.configure(state="disabled")
                self.update_playlists_display()
            else:
                messagebox.showerror("Error", "Could not find the selected playlist to delete.")

    def move_track_up(self):
        """Moves the selected track one position up in the current playlist."""
        if not self.selected_track_path or not self.selected_playlist_name:
            return

        playlist = self.library_data["playlists"][self.selected_playlist_name]

        # Find the index of the selected track
        for i, track in enumerate(playlist):
            if track['path'] == self.selected_track_path:
                if i > 0: # Cannot move the first track up
                    # Swap with the previous item
                    playlist[i], playlist[i-1] = playlist[i-1], playlist[i]
                    self.save_app_library()
                    self.show_playlist_content(self.selected_playlist_name)
                break

    def move_track_down(self):
        """Moves the selected track one position down in the current playlist."""
        if not self.selected_track_path or not self.selected_playlist_name:
            return

        playlist = self.library_data["playlists"][self.selected_playlist_name]

        # Find the index of the selected track
        for i, track in enumerate(playlist):
            if track['path'] == self.selected_track_path:
                if i < len(playlist) - 1: # Cannot move the last track down
                    # Swap with the next item
                    playlist[i], playlist[i+1] = playlist[i+1], playlist[i]
                    self.save_app_library()
                    self.show_playlist_content(self.selected_playlist_name)
                break


    def start_analysis_thread(self):
        """Starts the track analysis in a separate thread to keep the UI responsive."""
        self.analyze_button.configure(state="disabled")
        self.add_folder_button.configure(state="disabled")
        self.status_label.configure(text="Preparing analysis...")
        self.progress_bar.set(0)
        self.progress_details_label.configure(text="")
        self.eta_label.configure(text="")

        analysis_thread = threading.Thread(target=self.run_analysis, daemon=True)
        analysis_thread.start()

    def run_analysis(self):
        """The core analysis loop that runs in a background thread."""
        total_files = len(self.files_to_analyze)
        start_time = time.time()

        for i, file_path in enumerate(self.files_to_analyze):
            progress_text = f"Analyzing {i+1}/{total_files}:\n{file_path.name}"
            self.after(0, self.progress_details_label.configure, {"text": progress_text})

            analysis_results = engine.analyze_track_full(file_path)

            if analysis_results:
                camelot_key = engine.get_camelot_key(analysis_results["key"])
                if camelot_key:
                    key_number = ''.join(filter(str.isdigit, camelot_key))
                    color = engine.CAMELOT_COLOR_MAP.get(key_number, "#1f6aa5")
                    waveform_path = os.path.join(self.waveform_cache_dir, f"{file_path.stem}.png")
                    engine.generate_waveform_image(file_path, waveform_path, color=color)

                    track_info = {
                        'path': file_path,
                        'bpm': analysis_results["bpm"],
                        'key': analysis_results["key"],
                        'camelot_key': camelot_key,
                        'loudness': analysis_results["loudness"],
                        'brightness': analysis_results["brightness"],
                        'waveform_path': waveform_path
                    }
                    self.library_data["collection"].append(track_info)
                    engine.write_metadata_to_file(file_path, analysis_results["bpm"], camelot_key)

            elapsed_time = time.time() - start_time
            tracks_processed = i + 1
            avg_time_per_track = elapsed_time / tracks_processed
            remaining_tracks = total_files - tracks_processed
            eta_seconds = remaining_tracks * avg_time_per_track

            if tracks_processed > 1:
                eta_minutes, eta_sec = divmod(int(eta_seconds), 60)
                eta_text = f"ETA: {eta_minutes}m {eta_sec}s"
                self.after(0, self.eta_label.configure, {"text": eta_text})

            progress_value = (i + 1) / total_files
            self.after(0, self.progress_bar.set, progress_value)
            self.after(0, self.show_track_collection)

        self.after(0, self.analysis_complete)

    def analysis_complete(self):
        """Called on the main thread when analysis is finished."""
        self.status_label.configure(text=f"Analysis complete. Library updated.")
        self.progress_details_label.configure(text="")
        self.eta_label.configure(text="")
        self.progress_bar.set(1)
        self.add_folder_button.configure(state="normal")
        self.save_app_library() # Save the updated library
        self.show_track_collection() # Refresh the view


if __name__ == "__main__":
    app = App()
    app.mainloop()
