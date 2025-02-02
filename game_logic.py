import tkinter as tk
import openai
import os
import time
from dotenv import load_dotenv
from game_state import GameState
from game_ui import GameUI
from game_actions import GameActions

load_dotenv(dotenv_path="config.env")

class AppalachianAdventure:
    def __init__(self, root):
        self.root = root
        self.root.title("Appalachian Trail Adventure")
        self.root.configure(bg='#2e2e2e')  # Change background color to dark grey
        
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.deepseek_key = os.getenv("DEEPSEEK_API_KEY")
        openai.api_key = self.api_key
        
        self.state = GameState()
        self.ui = GameUI(root, self.state)
        self.actions = GameActions(self.state, self.ui)
        
        self.ui.entry_widget.bind("<Return>", self.process_input)
        
        self.ui.start_game()
        self.state.last_action_time = time.time()
        
        # Initialize first act
        self.state.generate_new_act()
    
    def process_input(self, event):
        user_input = self.ui.entry_widget.get().strip()
        if not user_input:
            return
        
        # Clear input box immediately after getting the text
        self.ui.entry_widget.delete(0, tk.END)
        
        self.ui.text_widget.insert(tk.END, f"You: {user_input}\n", "user_input")
        if user_input.startswith('/'):
            command_parts = user_input[1:].split()
            command = command_parts[0].lower()
            args = command_parts[1:]

            if command == "help":
                self.ui.show_help()
            elif command == "inventory":
                self.ui.update_inventory_display()
            elif command == "pickup" and args:
                item_name = " ".join(args)
                self.actions.pickup_item(item_name, collect_all=False)
            elif command == "craft":
                item_to_craft = user_input[7:].strip()
                self.actions.craft_item(item_to_craft)
            elif command == "buy":
                item_name = user_input[5:].strip()
                self.actions.buy_item(item_name)
            elif command == "talk":
                self.actions.talk_to_npc(user_input)
            elif command == "loot":
                self.actions.list_scene_items()
            elif command == "consume" and args:
                item_name = " ".join(args)
                self.actions.consume_item(item_name)
            elif command == "use":
                if args:
                    item_name = args[0]
                    usage_desc = " ".join(args[1:]) if len(args) > 1 else ""
                    self.actions.use_item(item_name, usage_desc)
                return
            else:
                self.ui.text_widget.insert(tk.END, "Unknown command. Type '/help' for a list of available commands.\n", "game_text")
        else:
            if self.actions.can_perform_action(user_input):
                self.actions.get_response(user_input)
            else:
                self.ui.text_widget.insert(tk.END, "Invalid action. Type '/help' for a list of available commands.\n", "game_text")
        
        self.actions.complete_goal_if_applicable(user_input)
        self.ui.text_widget.see(tk.END)

