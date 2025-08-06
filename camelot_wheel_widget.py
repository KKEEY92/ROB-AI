import customtkinter
import tkinter
import math
from analysis_engine import get_compatible_keys

class CamelotWheel(customtkinter.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)

        self.canvas = tkinter.Canvas(self, width=200, height=200, bg="#2b2b2b", borderwidth=0, highlightthickness=0)
        self.canvas.pack(pady=20, padx=10)

        self.segments = {} # To store canvas item IDs for interactivity
        self.key_to_segment_id = {} # For easier lookup
        self.draw_wheel()

        self.canvas.bind("<Button-1>", self.on_canvas_click)

    def draw_wheel(self, highlighted_keys=None):
        if highlighted_keys is None:
            highlighted_keys = []

        self.canvas.delete("all")
        center_x, center_y = 100, 100
        outer_radius = 90
        inner_radius = 50

        keys_b = [f"{i}B" for i in range(1, 13)] # Outer ring (Major)
        keys_a = [f"{i}A" for i in range(1, 13)] # Inner ring (Minor)

        self.key_to_segment_id = {} # Reset

        # Draw outer ring (B keys)
        for i, key in enumerate(keys_b):
            angle_start = (i - 3.5) * 30
            angle_extent = 30

            fill_color = "#0072B2" if key in highlighted_keys else "#4a4a4a"

            segment_id = self.canvas.create_arc(center_x - outer_radius, center_y - outer_radius,
                                                center_x + outer_radius, center_y + outer_radius,
                                                start=angle_start, extent=angle_extent,
                                                fill=fill_color, outline="gray20", width=2, tags=key)
            self.key_to_segment_id[key] = segment_id

            angle_text = math.radians(-angle_start - (angle_extent / 2))
            text_x = center_x + (outer_radius - 15) * math.cos(angle_text)
            text_y = center_y + (outer_radius - 15) * math.sin(angle_text)
            self.canvas.create_text(text_x, text_y, text=key, fill="white", font=("Arial", 10, "bold"), tags=key)

        # Draw inner ring (A keys)
        for i, key in enumerate(keys_a):
            angle_start = (i - 3.5) * 30
            angle_extent = 30

            fill_color = "#0072B2" if key in highlighted_keys else "#3a3a3a"

            segment_id = self.canvas.create_arc(center_x - inner_radius, center_y - inner_radius,
                                                center_x + inner_radius, center_y + inner_radius,
                                                start=angle_start, extent=angle_extent,
                                                fill=fill_color, outline="gray20", width=2, tags=key)
            self.key_to_segment_id[key] = segment_id

            angle_text = math.radians(-angle_start - (angle_extent / 2))
            text_x = center_x + (inner_radius - 15) * math.cos(angle_text)
            text_y = center_y + (inner_radius - 15) * math.sin(angle_text)
            self.canvas.create_text(text_x, text_y, text=key, fill="white", font=("Arial", 9), tags=key)

    def on_canvas_click(self, event):
        item_id = self.canvas.find_closest(event.x, event.y)[0]
        tags = self.canvas.gettags(item_id)
        if tags:
            clicked_key = tags[0]
            compatible_keys = get_compatible_keys(clicked_key)
            self.draw_wheel(highlighted_keys=compatible_keys)

if __name__ == '__main__':
    # Example of how to use the widget
    app = customtkinter.CTk()
    app.title("Camelot Wheel Test")
    app.geometry("300x300")

    wheel = CamelotWheel(app)
    wheel.pack(expand=True)

    app.mainloop()
