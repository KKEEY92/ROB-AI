import customtkinter
import tkinter
from tkinter import filedialog, messagebox
from PIL import Image
import analysis_engine as engine
import threading
import time
import os

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
        self.waveform_cache_dir = "waveform_cache"
        if not os.path.exists(self.waveform_cache_dir):
            os.makedirs(self.waveform_cache_dir)

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

        self.playlists_button = customtkinter.CTkButton(self.nav_pane, text="Playlists", state="disabled", corner_radius=5)
        self.playlists_button.pack(pady=5, padx=10, fill="x")

        # --- Content Pane (for the track list) ---
        self.content_pane = customtkinter.CTkFrame(self.main_content_frame, corner_radius=5)
        self.content_pane.grid(row=0, column=1, padx=(0, 10), pady=10, sticky="nsew")
        self.content_pane.grid_rowconfigure(0, weight=1)
        self.content_pane.grid_columnconfigure(0, weight=1)

        # --- Create a scrollable frame for the track list inside the content pane ---
        self.track_list_frame = customtkinter.CTkScrollableFrame(self.content_pane, label_text="Track Collection")
        self.track_list_frame.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        # --- Status Label ---
        self.status_label = customtkinter.CTkLabel(self, text="Load a folder to begin.", anchor="w")
        self.status_label.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 10), sticky="ew")

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
        self.track_list_frame.configure(label_text="Track Collection")
        self.update_track_list_display(self.library_data["collection"])


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
        # Clear existing widgets
        for widget in self.track_list_frame.winfo_children():
            widget.destroy()

        # Create Header
        headers = ["Track Name", "BPM", "Key", "Waveform"]
        column_weights = [2, 1, 1, 4] # Adjust column weights

        for i, header in enumerate(headers):
            self.track_list_frame.grid_columnconfigure(i, weight=column_weights[i])
            header_label = customtkinter.CTkLabel(self.track_list_frame, text=header, font=customtkinter.CTkFont(weight="bold"))
            header_label.grid(row=0, column=i, padx=10, pady=5, sticky="w")

        # Populate with tracks
        for i, track_data in enumerate(tracks_to_display):
            file_path = track_data['path']
            track_name = file_path.stem

            bpm = track_data.get('bpm', '--')
            key = track_data.get('camelot_key', '--')
            waveform_path = track_data.get('waveform_path')

            # --- Create a frame for each track row for selection highlighting ---
            track_frame = customtkinter.CTkFrame(self.track_list_frame, corner_radius=5)
            track_frame.grid(row=i + 1, column=0, columnspan=4, padx=5, pady=2, sticky="ew")
            for j, weight in enumerate(column_weights):
                track_frame.grid_columnconfigure(j, weight=weight)


            # Change background color if selected
            if self.selected_track_path == file_path:
                track_frame.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["hover_color"])

            # --- Create labels/buttons for each track's data ---
            track_button = customtkinter.CTkButton(track_frame, text=track_name, anchor="w", fg_color="transparent", text_color=customtkinter.ThemeManager.theme["CTkLabel"]["text_color"],
                                                   command=lambda p=file_path: self.track_selected(p))
            track_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

            bpm_label = customtkinter.CTkLabel(track_frame, text=bpm, anchor="w")
            bpm_label.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

            key_label = customtkinter.CTkLabel(track_frame, text=key, anchor="w")
            key_label.grid(row=0, column=2, padx=10, pady=5, sticky="ew")

            # --- Display Waveform ---
            if waveform_path and os.path.exists(waveform_path):
                try:
                    img = Image.open(waveform_path)
                    ctk_img = customtkinter.CTkImage(light_image=img, dark_image=img, size=(240, 32))
                    waveform_label = customtkinter.CTkLabel(track_frame, image=ctk_img, text="")
                    waveform_label.grid(row=0, column=3, padx=10, pady=2, sticky="w")
                except Exception:
                    # If image fails to load, show a placeholder
                    placeholder = customtkinter.CTkLabel(track_frame, text="Error", anchor="w")
                    placeholder.grid(row=0, column=3, padx=10, pady=5, sticky="ew")


    def track_selected(self, file_path):
        """Handles the event when a track is selected from the list."""
        self.selected_track_path = file_path
        self.playlist_button.configure(state="normal")
        self.status_label.configure(text=f"Selected: {file_path.stem}")
        self.update_track_list_display(self.library_data["collection"])

    def create_playlist(self):
        """Creates a harmonic playlist starting with the selected track."""
        if not self.selected_track_path:
            return

        self.status_label.configure(text="Creating playlist...")

        # Pass the entire collection to the playlist function
        playlist_file = engine.create_harmonic_playlist(self.library_data["collection"], self.selected_track_path)

        if playlist_file:
            self.status_label.configure(text=f"Playlist created: {playlist_file}")
            messagebox.showinfo("Playlist Created", f"Successfully created playlist:\n{playlist_file}")
        else:
            self.status_label.configure(text="Failed to create playlist.")
            messagebox.showerror("Error", "Could not create the playlist.")


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

            bpm, key = engine.analyze_track(file_path)
            if bpm and key:
                camelot_key = engine.get_camelot_key(key)
                if camelot_key:
                    key_number = ''.join(filter(str.isdigit, camelot_key))
                    color = engine.CAMELOT_COLOR_MAP.get(key_number, "#1f6aa5")
                    waveform_path = os.path.join(self.waveform_cache_dir, f"{file_path.stem}.png")
                    engine.generate_waveform_image(file_path, waveform_path, color=color)

                    track_info = {
                        'path': file_path, 'bpm': round(bpm), 'camelot_key': camelot_key,
                        'waveform_path': waveform_path
                    }
                    # Add new track to the main collection
                    self.library_data["collection"].append(track_info)
                    engine.write_metadata_to_file(file_path, bpm, camelot_key)

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
