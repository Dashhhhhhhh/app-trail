import tkinter as tk
import time
import json

class GameUI:
    def __init__(self, root, state):
        self.root = root
        self.state = state
        
        # Create main frame with padding
        main_frame = tk.Frame(root, bg='#2e2e2e', padx=20, pady=20)
        main_frame.pack(expand=True, fill='both')
        
        # Game text area with brighter green text and custom font
        self.text_widget = tk.Text(
            main_frame, 
            wrap=tk.WORD, 
            height=20, 
            width=80, 
            bg='#1c1c1c', 
            fg='#00ff00',  # Bright green
            insertbackground='white',
            font=('Consolas', 11),
            padx=10,
            pady=10
        )
        self.text_widget.pack(pady=(0, 10))
        
        # Command entry with custom font
        self.entry_widget = tk.Entry(
            main_frame, 
            width=80, 
            bg='#2e2e2e', 
            fg='white', 
            insertbackground='white',
            font=('Consolas', 11),
            bd=1,
            relief=tk.SOLID
        )
        self.entry_widget.pack(pady=(0, 20))
        
        # Status frame for health and food
        status_frame = tk.Frame(main_frame, bg='#2e2e2e')
        status_frame.pack(fill='x', pady=(0, 10))
        
        # Health and food labels with custom styling
        self.health_label = tk.Label(
            status_frame, 
            text=f"Health: {self.state.health}", 
            bg='#2e2e2e', 
            fg='#ff5555',  # Red for health
            font=('Consolas', 11, 'bold'),
            width=15
        )
        self.health_label.pack(side='left', padx=10)
        
        self.energy_label = tk.Label(
            status_frame, 
            text=f"Energy: {self.state.energy}",  # Changed from food to energy
            bg='#2e2e2e', 
            fg='#ffaa00',  # Orange for food
            font=('Consolas', 11, 'bold'),
            width=15
        )
        self.energy_label.pack(side='left', padx=10)
        
        # Inventory with scrolled text widget
        inventory_frame = tk.Frame(main_frame, bg='#2e2e2e')
        inventory_frame.pack(fill='x', pady=(0, 10))
        
        inventory_label = tk.Label(
            inventory_frame, 
            text="Inventory:", 
            bg='#2e2e2e', 
            fg='white',
            font=('Consolas', 11, 'bold')
        )
        inventory_label.pack(anchor='w')
        
        self.inventory_text = tk.Text(
            inventory_frame,
            height=3,
            wrap=tk.WORD,
            bg='#1c1c1c',
            fg='#aaaaaa',  # Light gray for inventory
            font=('Consolas', 10),
            padx=5,
            pady=5
        )
        self.inventory_text.pack(fill='x')
        
        # Button frame
        button_frame = tk.Frame(main_frame, bg='#2e2e2e')
        button_frame.pack(pady=(10, 0))
        
        # Styled buttons
        button_style = {
            'bg': '#3e3e3e',
            'fg': 'white',
            'font': ('Consolas', 10),
            'width': 15,
            'bd': 0,
            'padx': 10,
            'pady': 5,
            'relief': tk.FLAT
        }
        
        self.save_button = tk.Button(button_frame, text="Save Game", command=self.state.save_game, **button_style)
        self.save_button.pack(side='left', padx=5)
        
        self.load_button = tk.Button(button_frame, text="Load Game", command=self.state.load_game, **button_style)
        self.load_button.pack(side='left', padx5)
        
        self.settings_button = tk.Button(button_frame, text="Settings", command=self.open_settings, **button_style)
        self.settings_button.pack(side='left', padx=5)
        
        # Configure text tags
        self.text_widget.tag_configure("user_input", foreground="white", font=('Consolas', 11, 'bold'))
        self.text_widget.tag_configure("game_text", foreground="#00ff00", font=('Consolas', 11))  # Bright green

    def start_game(self):
        intro_text = [
            "The morning mist clings to Springer Mountain as you adjust your canvas rucksack.\n",
            "Behind you lies Atlanta and your old life. Ahead stretches the Appalachian Trail - a wild and untamed path north through the mountains.\n",
            "In your pack: basic provisions, a worn map, a brass compass, and hope for a new beginning.\n",
            "The trail ahead is marked by blazes carved into trees by those who walked before.\n",
            "Type '/look' to observe your surroundings, '/inventory' to check your supplies, or start walking with commands like '/go north' or '/follow trail'.\n",
            "Type '/help' for a list of available commands.\n"
        ]
        for text in intro_text:
            self.text_widget.insert(tk.END, text, "game_text")
            self.root.update()
            time.sleep(2)  # Longer pause for dramatic effect
            self.text_widget.see(tk.END)
        self.display_scene_top()

    def show_help(self):
        help_text = (
            "Available commands:\n"
            "/inventory - Check your supplies\n"
            "/pickup [item] - Pick up an item from your surroundings\n"
            "/craft [item] - Craft an item (e.g., /craft snare)\n"
            "/buy [item] - Purchase an item from a vendor\n"
            "/talk - Engage in conversation with a character\n"
            "/help - Show this help message\n\n"
            "While talking to someone, all your messages will be directed to them.\n"
            "Say 'goodbye' to end the conversation.\n"
            "Every action you take will include a description of your surroundings.\n"
        )
        self.text_widget.insert(tk.END, help_text, "game_text")

    def update_inventory_display(self):
        self.inventory_text.delete('1.0', tk.END)
        inventory_text = ", ".join(f"{qty} {item}" if qty > 1 else item 
                                 for item, qty in self.state.inventory.items())
        self.inventory_text.insert(tk.END, inventory_text)

    def open_settings(self):
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.configure(bg='black')
        
        tk.Label(settings_window, text="OpenAI API Key:", bg='black', fg='white').pack(pady=5)
        openai_entry = tk.Entry(settings_window, width=50, bg='black', fg='white', insertbackground='white')
        openai_entry.pack(pady=5)
        openai_entry.insert(0, self.state.api_key)
        
        tk.Label(settings_window, text="DeepSeek API Key:", bg='black', fg='white').pack(pady=5)
        deepseek_entry = tk.Entry(settings_window, width=50, bg='black', fg='white', insertbackground='white')
        deepseek_entry.pack(pady=5)
        deepseek_entry.insert(0, self.state.deepseek_key)
        
        def save_keys():
            self.state.api_key = openai_entry.get()
            self.state.deepseek_key = deepseek_entry.get()
            with open("config.env", "w") as f:
                f.write(f"OPENAI_API_KEY={self.state.api_key}\n")
                f.write(f"DEEPSEEK_API_KEY={self.state.deepseek_key}\n")
            openai.api_key = self.state.api_key
            settings_window.destroy()
        
        save_button = tk.Button(settings_window, text="Save", command=save_keys, bg='gray', fg='white')
        save_button.pack(pady=20)

    def display_scene_top(self):
        with open("game_frame.json", "r") as f:
            data = json.load(f)
        scene_text = data.get("scene_data", "")
        self.text_widget.insert("1.0", scene_text + "\n", "game_text")
