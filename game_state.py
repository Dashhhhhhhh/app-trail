import json
import openai  # Import the openai module
import random  # Add this import

class GameState:
    def __init__(self):
        self.current_scene = 0
        self.health = 100
        self.energy = 100
        self.inventory = {
            "canvas rucksack": 1,
            "worn map": 1,
            "brass compass": 1,
            "water canteen": 1,
            "first aid supplies": 1,
            "flint and steel": 1
        }
        self.environment_items = {}  # Will store the current scene's available items
        self.scene_history = []      # Track scenes visited
        self.last_action_time = 0
        self.energy_decay_rate = 2  # Energy points lost per hour
        self.moves_since_rest = 0
        self.action_requirements = {
            "hunt": ["flint and steel"],
            "fish": ["fishing line"],
            "climb": ["rope"],
            "cut": ["knife", "axe"],
            "make fire": ["flint and steel"],
            "cook": ["flint and steel"],
            "treat": ["first aid supplies"],
            "navigate": ["compass", "map"],
            "drink": ["water canteen"],
            "fill": ["water canteen"],
            "shoot": ["bow", "arrow"],
            "chop": ["axe"],
            "saw": ["saw"],
            "light": ["flint and steel"],
            "bandage": ["first aid supplies"],
            "stitch": ["first aid supplies", "needle"],
            "repair": ["needle", "thread"],
            "whittle": ["knife"],
            "skin": ["knife"],
            "clean": ["water canteen"],
            "filter": ["cloth"],
        }
        self.crafting_recipes = self.load_crafting_recipes()
        
        # Update item patterns to be more flexible
        self.item_patterns = {
            # Natural materials
            "wood": ["log", "timber", "branch", "stick", "twig"],
            "stone": ["rock", "pebble", "flint"],
            "plant": ["herb", "flower", "grass", "weed"],
            "berry": ["fruit", "berry", "nut", "seed"],
            "mushroom": ["fungus", "toadstool"],
            "vine": ["creeper", "tendril", "rope"],
            "leaf": ["foliage", "frond", "needle"],
            "root": ["tuber", "bulb", "rhizome"],
            "bark": ["shell", "husk", "skin"],
            
            # Common found items
            "tool": ["knife", "axe", "saw", "hammer"],
            "container": ["bucket", "pot", "cup", "bowl"],
            "cloth": ["fabric", "leather", "hide", "rag"],
            "metal": ["coin", "nail", "hook", "pin"],
            "paper": ["note", "map", "page", "letter"]
        }
        self.npcs = self.load_npcs()
        self.current_npc = None
        self.money = 100  # Starting money
        self.current_act = None  # Current act in the game
        self.acts = []  # List of all acts
        try:
            with open("game_state.json", "r") as f:
                data = json.load(f)
                self.acts = data.get("acts", [])
        except:
            self.acts = []

        self.current_act_index = 0

    def generate_crafting_recipe(self, item_name):
        """Generate a new crafting recipe with period-appropriate materials"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """You are an expert in 1897 wilderness survival and crafting.
                Generate a crafting recipe using only materials found in nature or basic tools.
                Consider the technological limitations of 1897.
                Use only materials like: wood, stone, stick, branch, vine, leather, bone, hide,
                fiber, leaf, bark, root, grass, sinew, cord, rope, cloth, fur, feather.
                Format your response like this:
                item_name: 2 stick, 1 rope, 3 leather - Brief description of how to craft it.
                If the item cannot be made with natural materials or is too complex for 1897,
                respond with "impossible"."""},
                {"role": "user", "content": f"Generate a realistic crafting recipe for {item_name} using only basic materials from 1897:"}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        recipe_text = response.choices[0].message['content'].strip()
        if recipe_text.lower() == "impossible":
            return None
            
        if ':' in recipe_text:
            try:
                item, details = recipe_text.split(':', 1)
                if '-' in details:
                    materials, description = details.split('-', 1)
                    materials_dict = {}
                    for material in materials.split(','):
                        material = material.strip()
                        if not material:
                            continue
                        parts = material.split()
                        if len(parts) >= 2:
                            try:
                                amount = int(parts[0])
                                material_name = ' '.join(parts[1:])
                                materials_dict[material_name] = amount
                            except ValueError:
                                continue
                    if materials_dict:  # Only return if we have valid materials
                        return {
                            "materials": materials_dict,
                            "description": description.strip()
                        }
            except Exception as e:
                print(f"Error parsing recipe: {e}")
        return None

    def find_similar_items(self, required_item):
        """Find similar items in inventory that could be substituted"""
        similar_items = {
            "stick": ["branch", "wood", "pole"],
            "rope": ["cord", "string", "fiber", "vine"],
            "cloth": ["fabric", "leather", "hide"],
            "stone": ["rock", "pebble"],
            "leather": ["hide", "skin"],
            "fiber": ["string", "thread", "vine"],
            "branch": ["stick", "wood", "pole"],
            "wood": ["stick", "branch", "pole"],
            "bone": ["antler", "tusk"]
        }
        
        for category, alternatives in similar_items.items():
            if required_item in [category] + alternatives:
                # Check if player has any items from this category
                available_items = [item for item in [category] + alternatives 
                                if item in self.inventory]
                if available_items:
                    return available_items[0]
        return None

    def load_crafting_recipes(self):
        try:
            with open("crafting_recipes.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_crafting_recipes(self):
        with open("crafting_recipes.json", "w") as f:
            json.dump(self.crafting_recipes, f, indent=4)

    def save_game(self):
        game_state = {
            "current_scene": self.current_scene,
            "story": self.text_widget.get(1.0, tk.END),
            "health": self.health,
            "energy": self.energy,
            "inventory": self.inventory,
            "crafting_recipes": self.crafting_recipes,  # Save crafting recipes
            "money": self.money
        }
        with open("game_state.json", "w") as f:
            json.dump(game_state, f, indent=4)
    
    def load_game(self):
        try:
            with open("game_state.json", "r") as f:
                game_state = json.load(f)
                self.current_scene = game_state["current_scene"]
                self.text_widget.delete(1.0, tk.END)
                self.display_text(game_state["story"], "game_text")
                self.health = game_state["health"]
                self.energy = game_state["energy"]
                self.inventory = game_state["inventory"]
                self.crafting_recipes = game_state.get("crafting_recipes", {})  # Load crafting recipes
                self.health_label.config(text=f"Health: {self.health}")
                self.energy_label.config(text=f"Energy: {self.energy}")
                self.inventory_label.config(text=f"Inventory: {', '.join(self.inventory)}")
        except FileNotFoundError:
            self.display_text("No saved game found.\n", "game_text")

    def get_available_items(self):
        """Get a list of available items in the current scene"""
        return {item: qty for item, qty in self.environment_items.items() if qty > 0}

    def load_npcs(self):
        """Load NPCs from game_characters.json"""
        try:
            with open("game_characters.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            # Create the file if it doesn't exist
            with open("game_characters.json", "w") as f:
                json.dump({}, f, indent=4)
            return {}

    def save_npc(self, npc_data):
        """Save a new NPC to game_characters.json"""
        try:
            with open("game_characters.json", "r") as f:
                characters = json.load(f)
        except FileNotFoundError:
            characters = {}
        
        npc_id = str(len(characters) + 1)
        characters[npc_id] = npc_data
        
        with open("game_characters.json", "w") as f:
            json.dump(characters, f, indent=4)
        
        return npc_id

    def get_random_npc(self):
        """Get a random existing NPC or generate a new one"""
        if self.npcs and random.random() < 0.7:  # 70% chance to use existing NPC
            npc_id = random.choice(list(self.npcs.keys()))
            return self.npcs[npc_id]
        else:
            return self.generate_npc()

    def generate_npc(self, npc_type=None):
        """Generate a new NPC using AI, optionally of a specific type"""
        type_prompt = f"of type {npc_type}" if npc_type else "that could be encountered"
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Create a character for the Appalachian Trail in 1897.
                Format: 
                {
                    "name": "character name",
                    "type": "traveler/vendor/hunter/guide",
                    "description": "brief character description",
                    "personality": "key personality traits",
                    "inventory": {"item1": [quantity, price], "item2": [quantity, price]},
                    "dialogue_style": "how they speak"
                }
                For vendors, include 2-4 items with reasonable quantities and prices."""},
                {"role": "user", "content": f"Generate a random character {type_prompt} on the trail:"}
            ]
        )
        
        try:
            npc_data = json.loads(response.choices[0].message['content'])
            if npc_type and npc_data['type'] != npc_type:
                npc_data['type'] = npc_type  # Ensure correct type
            self.save_npc(npc_data)
            return npc_data
        except json.JSONDecodeError:
            return None

    def generate_new_act(self):
        """
        Creates a new act with a goal and relevant scenes.
        Uses AI to generate minimal story context and encounters.
        """
        act_prompt = "Generate a JSON object representing an act with a short goal and up to 3 scene ideas."
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are creating acts for a text-based adventure set in 1897."},
                {"role": "user", "content": act_prompt}
            ],
            max_tokens=100
        )
        # ...existing code...

    def progress_to_next_act(self):
        """
        If the current act goal is accomplished, move on to the next act.
        """
        if self.current_act_index < len(self.acts) - 1:
            self.current_act_index += 1
            # ...existing code...

    def check_if_goal_reached(self, user_input):
        """
        Checks if user_input satisfies an act goal.
        Replace this placeholder with your actual goal logic.
        """
        # Example condition
        return "goal" in user_input

# ...existing code...
