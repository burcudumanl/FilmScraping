import requests
import json
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import threading
import webbrowser
import os
from PIL import Image, ImageTk

from DialogueGenerator import (
    generate_dialogue as ai_generate_dialogue,
    get_movie_storyline,
    generate_image as ai_generate_image
)

URL_TOP_250 = "https://www.imdb.com/chart/top/"
HEADERS = {
    "Accept-Language": "en-US,en;q=0.5",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/112.0.0.0 Safari/537.36"
    )
}

def get_top_10_films():
    resp = requests.get(URL_TOP_250, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    script = soup.find("script", id="__NEXT_DATA__", type="application/json")
    data = json.loads(script.string)
    edges = data["props"]["pageProps"]["pageData"]["chartTitles"]["edges"]
    return [(edge["node"]["titleText"]["text"], f"https://www.imdb.com/title/{edge['node']['id']}/") for edge in edges[:10]]

def get_film_description(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    desc_elem = soup.find('span', {'data-testid': 'plot-l'}) or soup.find('span', {'data-testid': 'plot-xl'})
    return desc_elem.get_text(strip=True) if desc_elem else 'N/A'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("IMDb Top 10 Movies")
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        win_width = int(screen_width * 0.8)
        win_height = int(screen_height * 0.8)
        self.geometry(f"{win_width}x{win_height}")

        self.current_title = None
        self.current_link = None
        self.current_desc = None
        self.current_storyline = None

        paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left panel
        left_frame = ttk.Frame(paned)
        ttk.Label(left_frame, text="Top 10 IMDb Movies", font=("Arial", 16, "bold")).pack(pady=5)
        self.listbox = tk.Listbox(left_frame, font=("Arial", 12), width=40)
        self.listbox.pack(fill=tk.BOTH, expand=True, side=tk.LEFT, padx=(5,0), pady=5)
        scrollbar = ttk.Scrollbar(left_frame, command=self.listbox.yview)
        scrollbar.pack(fill=tk.Y, side=tk.RIGHT, padx=(0,5), pady=5)
        self.listbox.config(yscrollcommand=scrollbar.set)
        self.listbox.bind('<<ListboxSelect>>', self.on_select)
        paned.add(left_frame, weight=2)

        # Right panel
        right_frame = ttk.Frame(paned)
        input_frame = ttk.Frame(right_frame)
        input_frame.pack(fill=tk.X, pady=10, padx=10)

        # Inputs
        ttk.Label(input_frame, text="Char Count:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.char_count_entry = ttk.Entry(input_frame, width=8)
        self.char_count_entry.grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Location:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.location_entry = ttk.Entry(input_frame, width=12)
        self.location_entry.grid(row=0, column=3, padx=5)

        ttk.Label(input_frame, text="Max Length (words):").grid(row=0, column=4, sticky=tk.W, padx=5)
        self.max_length_entry = ttk.Entry(input_frame, width=8)
        self.max_length_entry.grid(row=0, column=5, padx=5)

        # Style Combobox
        ttk.Label(input_frame, text="Style:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=(10,0))
        self.style_combo = ttk.Combobox(input_frame, values=["marvel", "futuristic", "cartoon", "realistic"], state="readonly", width=15)
        self.style_combo.grid(row=1, column=1, padx=5, pady=(10,0))
        self.style_combo.current(0)

        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=1, column=2, columnspan=4, sticky=tk.E, padx=5, pady=(10,0))

        ttk.Button(btn_frame, text="Generate Dialogue", command=self.on_generate_dialogue).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Generate Image", command=self.on_generate_image).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Export Dialouge", command=self.on_save_and_tag).pack(side=tk.LEFT, padx=5)

        # Tabs
        notebook = ttk.Notebook(right_frame)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        tab1 = ttk.Frame(notebook)
        self.detail_text = tk.Text(tab1, wrap='word', font=("Arial", 11))
        self.detail_text.pack(fill=tk.BOTH, expand=True)
        notebook.add(tab1, text="Film Details")

        tab2 = ttk.Frame(notebook)
        self.dialogue_text = tk.Text(tab2, wrap='word', font=("Arial", 11))
        self.dialogue_text.pack(fill=tk.BOTH, expand=True)
        notebook.add(tab2, text="Generated Dialogue")

        tab3 = ttk.Frame(notebook)
        self.image_frame = ttk.Frame(tab3)
        self.image_frame.pack(fill=tk.BOTH, expand=True)
        notebook.add(tab3, text="Generated Image")

        paned.add(right_frame, weight=3)
        self.films = []
        self.load_films()

    def load_films(self):
        self.listbox.delete(0, tk.END)
        try:
            self.films = get_top_10_films()
            for i, (title, _) in enumerate(self.films, start=1):
                self.listbox.insert(tk.END, f"{i}. {title}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load films: {e}")

    def on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.detail_text.delete('1.0', tk.END)
        self.detail_text.insert(tk.END, "Loading details...\n")
        self.dialogue_text.delete('1.0', tk.END)
        threading.Thread(target=self._fetch_and_display, args=(idx,), daemon=True).start()

    def _fetch_and_display(self, idx):
        title, link = self.films[idx]
        desc = get_film_description(link)
        storyline = get_movie_storyline(title)
        self.after(0, lambda: self._display_details(idx, title, link, desc, storyline))

    def _display_details(self, idx, title, link, desc, storyline):
        self.detail_text.delete('1.0', tk.END)
        self.detail_text.insert(tk.END, f"{idx+1}. {title}\n{link}\n\nDescription: {desc}\n\nStoryline: {storyline}\n")
        self.current_title = title
        self.current_link = link
        self.current_desc = desc
        self.current_storyline = storyline

    def on_generate_dialogue(self):
        if not self.current_title:
            messagebox.showwarning("Warning", "Please select a film first.")
            return
        try:
            count = int(self.char_count_entry.get())
            max_words = int(self.max_length_entry.get())
        except ValueError:
            messagebox.showwarning("Warning", "Character count and max length must be numbers.")
            return
        try:
            dialogue = ai_generate_dialogue(self.current_title, self.current_desc, self.current_storyline, count, max_words)
            self.dialogue_text.delete('1.0', tk.END)
            self.dialogue_text.insert('1.0', dialogue)
        except Exception as e:
            messagebox.showerror("Error", f"Error generating dialogue: {e}")

    def on_save_and_tag(self):
        dialogue = self.dialogue_text.get('1.0', tk.END).strip()
        if not dialogue:
            messagebox.showwarning("Warning", "Please generate the dialogue first.")
            return
        tag = simpledialog.askstring("Input", "Enter a name for the dialogue file:")
        if tag:
            filename = f"{tag}.txt"
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(dialogue)
                messagebox.showinfo("Success", f"Dialogue saved as '{filename}'.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save dialogue: {e}")

    def on_generate_image(self):
        if not self.current_title:
            messagebox.showwarning("Warning", "Please select a film first.")
            return

        dialogue = self.dialogue_text.get('1.0', tk.END).strip()
        if not dialogue:
            messagebox.showwarning("Warning", "Please generate the dialogue first.")
            return

        location = self.location_entry.get().strip()
        style = self.style_combo.get().strip()

        try:
            image_path = ai_generate_image(self.current_title, self.current_desc, self.current_storyline, dialogue, location, style)
        except Exception as e:
            messagebox.showerror("Error", f"Image generation failed: {e}")
            return

        if not os.path.isfile(image_path):
            messagebox.showerror("Error", image_path)
            return

        for widget in self.image_frame.winfo_children():
            widget.destroy()

        img = Image.open(image_path)
        img.thumbnail((self.image_frame.winfo_width(), self.image_frame.winfo_height()))
        photo = ImageTk.PhotoImage(img)

        label = ttk.Label(self.image_frame, image=photo)
        label.image = photo
        label.pack(fill=tk.BOTH, expand=True)

if __name__ == '__main__':
    app = App()
    app.mainloop()

