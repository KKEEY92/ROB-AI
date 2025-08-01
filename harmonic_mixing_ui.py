import customtkinter
import tkinter
from tkinter import filedialog, messagebox
import analysis_engine as engine
import threading

# Set the theme and color scheme for the application
customtkinter.set_appearance_mode("Dark")
customtkinter.set_default_color_theme("blue")

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        # --- Instance variables ---
        self.music_files = []
        self.analyzed_data = []
        self.selected_track_path = None

        # --- Configure the main window ---
        self.title("Harmonic Mixing Studio")
        self.geometry("1200x600")

        # --- Create the main grid layout ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Create a sidebar frame for controls ---
        self.sidebar_frame = customtkinter.CTkFrame(self, width=180, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1)

        # --- Add a title label to the sidebar ---
        self.logo_label = customtkinter.CTkLabel(self.sidebar_frame, text="Controls", font=customtkinter.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        # --- Add control buttons to the sidebar ---
        self.add_folder_button = customtkinter.CTkButton(self.sidebar_frame, text="Load Music Folder", command=self.load_folder)
        self.add_folder_button.grid(row=1, column=0, padx=20, pady=10)

        self.analyze_button = customtkinter.CTkButton(self.sidebar_frame, text="Analyze Tracks", state="disabled", command=self.start_analysis_thread)
        self.analyze_button.grid(row=2, column=0, padx=20, pady=10)

        self.playlist_button = customtkinter.CTkButton(self.sidebar_frame, text="Create Playlist", state="disabled", command=self.create_playlist)
        self.playlist_button.grid(row=3, column=0, padx=20, pady=10)

        # --- Add a progress bar ---
        self.progress_bar = customtkinter.CTkProgressBar(self.sidebar_frame, orientation="horizontal")
        self.progress_bar.set(0)
        self.progress_bar.grid(row=4, column=0, padx=20, pady=(10, 10))


        # --- Create a scrollable frame for the track list ---
        self.track_list_frame = customtkinter.CTkScrollableFrame(self, label_text="Track List")
        self.track_list_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.track_list_frame.grid_columnconfigure(0, weight=3) # Track name
        self.track_list_frame.grid_columnconfigure(1, weight=1) # BPM
        self.track_list_frame.grid_columnconfigure(2, weight=1) # Key

        # --- Status Label (replaces info_label) ---
        self.status_label = customtkinter.CTkLabel(self.sidebar_frame, text="Load a folder to begin.", wraplength=160)
        self.status_label.grid(row=6, column=0, padx=20, pady=(10, 0), sticky="s")


    def load_folder(self):
        """Opens a dialog to select a folder and loads music files."""
        folder_path = filedialog.askdirectory()
        if not folder_path:
            return

        self.music_files = engine.find_music_files(folder_path)
        self.analyzed_data = [] # Clear previous data
        self.playlist_button.configure(state="disabled")

        if self.music_files:
            self.status_label.configure(text=f"{len(self.music_files)} tracks loaded. Ready for analysis.")
            self.analyze_button.configure(state="normal")
            self.update_track_list_display()
        else:
            self.status_label.configure(text="No supported music files found.")
            self.analyze_button.configure(state="disabled")
            self.update_track_list_display() # Clear the list

    def update_track_list_display(self):
        """Clears and redraws the track list in the UI."""
        # Clear existing widgets
        for widget in self.track_list_frame.winfo_children():
            widget.destroy()

        # Create Header
        headers = ["Track Name", "BPM", "Key"]
        for i, header in enumerate(headers):
            header_label = customtkinter.CTkLabel(self.track_list_frame, text=header, font=customtkinter.CTkFont(weight="bold"))
            header_label.grid(row=0, column=i, padx=10, pady=5, sticky="w")

        # Create a dictionary for quick lookups of analyzed data
        analyzed_map = {item['path']: item for item in self.analyzed_data}

        # Populate with tracks
        for i, file_path in enumerate(self.music_files):
            track_name = file_path.stem

            bpm = "--"
            key = "--"
            is_analyzed = file_path in analyzed_map

            if is_analyzed:
                track_data = analyzed_map[file_path]
                bpm = track_data.get('bpm', '--')
                key = track_data.get('camelot_key', '--')

            # --- Create a frame for each track row for selection highlighting ---
            track_frame = customtkinter.CTkFrame(self.track_list_frame, corner_radius=5)
            track_frame.grid(row=i + 1, column=0, columnspan=3, padx=5, pady=2, sticky="ew")
            track_frame.grid_columnconfigure(0, weight=3)
            track_frame.grid_columnconfigure(1, weight=1)
            track_frame.grid_columnconfigure(2, weight=1)

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

    def track_selected(self, file_path):
        """Handles the event when a track is selected from the list."""
        self.selected_track_path = file_path

        # Check if the selected track has been analyzed
        is_analyzed = any(item['path'] == file_path for item in self.analyzed_data)

        if is_analyzed:
            self.playlist_button.configure(state="normal")
            self.status_label.configure(text=f"Selected: {file_path.stem}")
        else:
            self.playlist_button.configure(state="disabled")
            self.status_label.configure(text=f"Selected: {file_path.stem} (Not analyzed)")

        # Redraw the list to show the selection highlight
        self.update_track_list_display()

    def create_playlist(self):
        """Creates a harmonic playlist starting with the selected track."""
        if not self.selected_track_path:
            return

        self.status_label.configure(text="Creating playlist...")

        playlist_file = engine.create_harmonic_playlist(self.analyzed_data, self.selected_track_path)

        if playlist_file:
            self.status_label.configure(text=f"Playlist created: {playlist_file}")
            messagebox.showinfo("Playlist Created", f"Successfully created playlist:\n{playlist_file}")
        else:
            self.status_label.configure(text="Failed to create playlist.")
            messagebox.showerror("Error", "Could not create the playlist. Please ensure the selected track has been analyzed.")


    def start_analysis_thread(self):
        """Starts the track analysis in a separate thread to keep the UI responsive."""
        self.analyze_button.configure(state="disabled")
        self.add_folder_button.configure(state="disabled")
        self.status_label.configure(text="Analysis in progress...")
        self.progress_bar.set(0)

        analysis_thread = threading.Thread(target=self.run_analysis, daemon=True)
        analysis_thread.start()

    def run_analysis(self):
        """The core analysis loop that runs in a background thread."""
        total_files = len(self.music_files)
        self.analyzed_data = []

        for i, file_path in enumerate(self.music_files):
            bpm, key = engine.analyze_track(file_path)
            if bpm and key:
                camelot_key = engine.get_camelot_key(key)
                if camelot_key:
                    track_info = {'path': file_path, 'bpm': round(bpm), 'camelot_key': camelot_key}
                    self.analyzed_data.append(track_info)
                    # We can still write metadata in the background
                    engine.write_metadata_to_file(file_path, bpm, camelot_key)

            progress_value = (i + 1) / total_files
            self.after(0, self.progress_bar.set, progress_value)
            # Update the UI list incrementally
            self.after(0, self.update_track_list_display)

        self.after(0, self.analysis_complete)

    def analysis_complete(self):
        """Called on the main thread when analysis is finished."""
        self.status_label.configure(text=f"Analysis complete. {len(self.analyzed_data)} tracks analyzed.")
        self.progress_bar.set(1)
        self.add_folder_button.configure(state="normal")
        self.update_track_list_display() # Final update


if __name__ == "__main__":
    app = App()
    app.mainloop()
