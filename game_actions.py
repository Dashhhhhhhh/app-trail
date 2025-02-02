import openai
import time
import random
import json
import tkinter as tk

class GameActions:
    def __init__(self, state, ui):
        self.state = state
        self.ui = ui
        self.conversation_history = []
        self.system_instructions = """Describe Appalachian Trail scenes in 1-2 brief sentences.
        Always include 3-4 interactable items naturally in every description.
        Keep descriptions short but rich with collectible items."""

    def can_perform_action(self, user_input):
        input_words = user_input.lower().split()
        
        for action in self.state.action_requirements.keys():
            if action in user_input.lower():
                required_items = self.state.action_requirements[action]
                missing_items = [item for item in required_items if item not in self.state.inventory]
                if missing_items:
                    self.ui.text_widget.insert(tk.END, 
                        f"You need {', '.join(missing_items)} to {action}.\n", "game_text")
                    return False

        tool_actions = {
            "bow": ["shoot", "aim", "fire"],
            "knife": ["cut", "slice", "carve"],
            "axe": ["chop", "split", "hack"],
            "rope": ["tie", "bind", "secure"],
            "fishing line": ["fish", "catch"],
        }

        for tool, actions in tool_actions.items():
            if any(action in input_words for action in actions) and tool not in self.state.inventory:
                self.ui.text_widget.insert(tk.END, 
                    f"You need a {tool} to do that.\n", "game_text")
                return False

        impossible_actions = [
            "fly", "teleport", "swim", "dive", "build", "create", "craft"
        ]
        if any(action in input_words for action in impossible_actions):
            self.ui.text_widget.insert(tk.END, 
                "That action is not possible in this environment.\n", "game_text")
            return False

        if any(word in input_words for word in ['go', 'walk', 'follow', 'climb', 'hike']):
            if self.state.health <= 20:
                self.ui.text_widget.insert(tk.END, 
                    "You are too exhausted to travel. You should rest first.\n", "game_text")
                return False
            if self.state.energy <= 10:
                self.ui.text_widget.insert(tk.END, 
                    "You are too hungry to travel. You should eat something.\n", "game_text")
                return False

        if "pick up" in user_input:
            parts = user_input.split("pick up ")[1].split()
            try:
                quantity = int(parts[0])
                item = " ".join(parts[1:])
            except (ValueError, IndexError):
                item = " ".join(parts)
                quantity = 1
                
            if item not in self.state.environment_items:
                self.ui.text_widget.insert(tk.END, f"There is no {item} here to pick up.\n", "game_text")
                return False
            if not self.is_item_pickable(item):
                self.ui.text_widget.insert(tk.END, f"You cannot pick up the {item}.\n", "game_text")
                return False
            if quantity > self.state.environment_items.get(item, 0):
                self.ui.text_widget.insert(tk.END, f"There aren't that many {item}s available.\n", "game_text")
                return False

        return True

    def is_item_pickable(self, item):
        """Enhanced item pickable check"""
        unpickable_items = [
            "tree", "mountain", "path", "trail", "river", "stream", "rock formation",
            "view", "mountain range", "forest", "ground", "sky", "sun", "moon",
            "building", "cabin", "shelter", "boulder", "cliff", "lake", "pond",
            "hill", "mountain", "cloud", "star", "fence", "wall", "house"
        ]
        
        # Check if item is too large or immovable
        if any(unpickable in item.lower() for unpickable in unpickable_items):
            return False
            
        # Don't allow picking up living creatures
        living_things = ["bird", "animal", "snake", "deer", "bear", "fox", "rabbit", "fish"]
        if any(creature in item.lower() for creature in living_things):
            return False
            
        return True

    def clean_response(self, text):
        """Clean up AI response text to remove any 'You' prefixes"""
        text = text.strip()
        # Remove "You" or "you" at the start of the text
        while text.lower().startswith(('you ', 'your ')):
            text = text.split(' ', 1)[1]
        # Capitalize first letter if needed
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text

    def get_response(self, user_input):
        # If in conversation, only handle dialogue
        if self.state.current_npc:
            self.talk_to_npc(user_input)
            return

        frame_data = self.load_frame()
        lower_input = user_input.lower()

        # Enhanced character interaction check
        if "talk to" in lower_input:
            scene_text = frame_data.get("scene_data", "")
            # Extract character being referenced
            target = lower_input.split("talk to")[-1].strip()
            
            # Generate character if mentioned in scene
            if target in scene_text.lower():
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{
                        "role": "system",
                        "content": """Create an NPC based on the mentioned character.
                        Format as JSON: {
                            "name": "descriptive name",
                            "type": "role/occupation",
                            "description": "brief description",
                            "personality": "key traits",
                            "dialogue_style": "speaking style"
                        }"""
                    }, {
                        "role": "user",
                        "content": f"Create character for: {target} mentioned in: {scene_text}"
                    }]
                )
                
                try:
                    npc_data = json.loads(response.choices[0].message['content'])
                    self.state.current_npc = npc_data
                    self.state.save_npc(npc_data)
                    
                    # Start conversation
                    self.talk_to_npc("hello")
                    return
                except:
                    pass

        # Load current context
        frame_data = self.load_frame()
        context = frame_data.get("scene_context", {})
        current_scene = frame_data.get("scene_data", "")
        
        previous_scenes = context.get("previous_scenes", [])
        if current_scene and (not previous_scenes or current_scene != previous_scenes[-1]):
            previous_scenes.append(current_scene)
        context["previous_scenes"] = previous_scenes[-3:]  # keep last 3

        # Update messages to refer to multiple previous scenes
        scene_history_str = " | ".join(previous_scenes)
        messages = [
            {"role": "system", "content": f"""You are describing scenes on the Appalachian Trail in 1897.
Keep each new scene to 1-2 sentences.
Base it on past scenes: {scene_history_str}"""},
            {"role": "user", "content": user_input}
        ]

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=50,  # Reduced for shorter responses
            temperature=0.7
        )
        
        story = self.clean_response(response.choices[0].message['content'])
        
        # Update scene context
        try:
            new_context = {
                "location": context.get("location", "unknown"),
                "previous_locations": context.get("previous_locations", [])[-4:] + [context.get("location")],
                "environment": context.get("environment", {}),
                "scene_data": story,
                "discovered_locations": context.get("discovered_locations", [])
            }
            
            # Update frame data
            frame_data["scene_context"] = new_context
            frame_data["scene_data"] = story
            with open("game_frame.json", "w") as f:
                json.dump(frame_data, f, indent=4)
                
        except Exception as e:
            print(f"Error updating context: {e}")
            
        self.ui.text_widget.insert(tk.END, f"{story}\n", "game_text")

        # Generate scene pools
        try:
            pools_response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system", 
                    "content": """Create scene pools in this exact JSON format:
{
    "item_pool": {
        "common": ["branch", "stone", "leaf"],
        "uncommon": ["herbs", "tools", "rope"],
        "rare": ["coins", "jewelry", "weapons"]
    },
    "npc_pool": {
        "common": ["traveler", "hunter", "farmer"],
        "uncommon": ["vendor", "guide", "craftsman"],
        "rare": ["doctor", "soldier", "mystic"]
    }
}
Only include period-appropriate items and characters for 1897."""
                }, {
                    "role": "user",
                    "content": f"Generate pools for: {story}"
                }],
                max_tokens=200,
                temperature=0.7
            )
            
            # Parse response and validate structure
            pools = json.loads(pools_response.choices[0].message['content'])
            if not all(key in pools for key in ["item_pool", "npc_pool"]):
                raise ValueError("Missing required pool categories")
                
            frame_data["scene_context"]["scene_pools"] = pools
            self.save_frame(json.dumps(frame_data, indent=4))
            
        except json.JSONDecodeError as e:
            print(f"JSON parse error in pools: {str(e)}")
            # Use default pools
            frame_data["scene_context"]["scene_pools"] = {
                "item_pool": {
                    "common": ["stick", "stone", "leaf"],
                    "uncommon": [],
                    "rare": []
                },
                "npc_pool": {
                    "common": ["traveler"],
                    "uncommon": [],
                    "rare": []
                }
            }
        except Exception as e:
            print(f"Error generating scene pools: {str(e)}")

        # Step B: Example check for new location, e.g., user finds a shop
        if "find a shop" in user_input.lower() or "come across a small general store" in user_input.lower():
            new_location_desc = "A small general store nestled amongst the trees."
            self.store_location(new_location_desc)
            self.ui.text_widget.insert(tk.END, f"Location updated: {new_location_desc}\n", "game_text")

        # ...rest of existing code...

    def extract_npcs_from_scene(self, scene_text):
        """Extract NPCs mentioned in scene description"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Extract any characters/NPCs from the scene.
                Return as JSON array of NPCs with format:
                [{
                    "name": "descriptive name",
                    "type": "role/occupation", 
                    "description": "brief description"
                }]
                Only include characters that could be interacted with."""},
                {"role": "user", "content": f"Scene: {scene_text}"}
            ],
            max_tokens=150
        )
        
        try:
            npcs = json.loads(response.choices[0].message['content'])
            # Update scene context with active NPCs
            frame_data = self.load_frame()
            frame_data["scene_context"]["active_npcs"] = npcs
            self.save_frame(json.dumps(frame_data))
            return npcs
        except:
            return []

    def extract_npc_from_scene(self):
        """Extract NPC type from user input or scene"""
        last_index = self.ui.text_widget.index("end-2c linestart")
        last_lines = self.ui.text_widget.get("end-50c linestart", last_index).lower()
        
        # Map specific mentions to NPC types
        npc_mappings = {
            "dog": "animal",
            "merchant": "vendor",
            "trader": "vendor",
            "hunter": "hunter",
            "guide": "guide",
            "traveler": "traveler",
            "blacksmith": "craftsman",
            "doctor": "healer",
            "shepherd": "animal_handler",
            "farmer": "settler"
        }
        
        for mention, npc_type in npc_mappings.items():
            if mention in last_lines:
                return npc_type
        return None

    def generate_npc_encounter(self, npc_type=None):
        """Generate a contextually appropriate NPC"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""Generate an NPC appropriate for the Appalachian Trail in 1897.
                Type requested: {npc_type if npc_type else 'any appropriate type'}
                Format as JSON:
                {{
                    "name": "character name",
                    "type": "{npc_type if npc_type else 'type'}",
                    "description": "brief physical description",
                    "personality": "key traits",
                    "dialogue_style": "how they speak",
                    "inventory": {{"item": [quantity, price]}} # only for vendors
                }}"""},
                {"role": "user", "content": "Generate a historically accurate character"}
            ]
        )
        
        try:
            npc_data = json.loads(response.choices[0].message['content'])
            self.state.current_npc = npc_data
            
            # Save new NPC to game_characters.json
            if npc_data.get("name"):  # Only save if valid NPC generated
                self.state.save_npc(npc_data)
            
            encounter_msg = f"A {npc_data['type']} is encountered. {npc_data['name']}, {npc_data['description']}\n"
            if npc_data['type'] == 'vendor':
                items = [f"{item} ({qty} available, {price} coins)" 
                        for item, (qty, price) in npc_data.get('inventory', {}).items()]
                if items:
                    encounter_msg += f"They have: {', '.join(items)}\n"
            
            self.ui.text_widget.insert(tk.END, encounter_msg + 
                "You can talk naturally with them. Say 'goodbye' to end the conversation.\n", "game_text")
            
        except (json.JSONDecodeError, KeyError):
            self.ui.text_widget.insert(tk.END, "No one responds.\n", "game_text")

    def talk_to_npc(self, user_input):
        """Handle conversation with current NPC"""
        if not self.state.current_npc:
            # Check if trying to talk to someone in scene
            frame_data = self.load_frame()
            scene_npcs = frame_data["scene_context"].get("active_npcs", [])
            
            # Try to find mentioned NPC
            lower_input = user_input.lower()
            for npc in scene_npcs:
                if npc["name"].lower() in lower_input or npc["type"].lower() in lower_input:
                    self.state.current_npc = npc
                    self.ui.text_widget.insert(tk.END, 
                        f"You approach {npc['name']}, {npc['description']}\n", "game_text")
                    self.ui.text_widget.insert(tk.END, 
                        "You can talk naturally. Say 'goodbye' to end conversation.\n", "game_text")
                    return
                    
            self.ui.text_widget.insert(tk.END, "There's no one here to talk to.\n", "game_text")
            return
            
        # Check for conversation exit
        if any(word in user_input.lower() for word in ["goodbye", "bye", "leave", "farewell"]):
            npc_name = self.state.current_npc['name']
            self.state.current_npc = None
            self.ui.text_widget.insert(tk.END, f"{npc_name} bids farewell.\n", "game_text")
            return

        npc = self.state.current_npc
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"""You are {npc['name']}, a {npc['type']} on the Appalachian Trail in 1897.
                Personality: {npc['personality']}
                Speaking style: {npc['dialogue_style']}
                ONLY respond in character with dialogue.
                No scene descriptions or narrative text.
                If the traveler says goodbye, acknowledge it politely."""},
                {"role": "user", "content": user_input}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        reply = response.choices[0].message['content'].strip()
        self.ui.text_widget.insert(tk.END, f"{npc['name']}: {reply}\n", "game_text")

    def buy_item(self, item_name):
        """Handle purchasing items from vendors"""
        if not self.state.current_npc or self.state.current_npc['type'] != 'vendor':
            self.ui.text_widget.insert(tk.END, "There's no vendor here to buy from.\n", "game_text")
            return

        npc = self.state.current_npc
        if item_name not in npc['inventory']:
            self.ui.text_widget.insert(tk.END, f"{npc['name']} doesn't have that item for sale.\n", "game_text")
            return

        quantity, price = npc['inventory'][item_name]
        if quantity <= 0:
            self.ui.text_widget.insert(tk.END, f"{npc['name']} is out of {item_name}.\n", "game_text")
            return

        if self.state.money < price:
            self.ui.text_widget.insert(tk.END, f"You don't have enough money. {item_name} costs {price} coins.\n", "game_text")
            return

        # Complete the purchase
        self.state.money -= price
        npc['inventory'][item_name][0] -= 1
        self.state.inventory[item_name] = self.state.inventory.get(item_name, 0) + 1
        
        self.ui.text_widget.insert(tk.END, 
            f"You bought {item_name} for {price} coins. You have {self.state.money} coins remaining.\n", "game_text")
        self.ui.update_inventory_display()

    def extract_mentioned_items(self, text):
        """Extract items that the user is trying to collect from their message"""
        mentioned_items = set()
        text_words = text.lower().split()
        
        # Look for items after collection verbs
        collection_verbs = ["grab", "take", "collect", "gather", "pick"]
        for i, word in enumerate(text_words):
            if word in collection_verbs and i < len(text_words) - 1:
                # Look at the next few words for potential items
                potential_item = " ".join(text_words[i+1:i+4])
                # Check against known item patterns
                for base_item, variants in self.state.item_patterns.items():
                    if any(variant in potential_item for variant in [base_item] + variants):
                        mentioned_items.add(base_item)
        
        return mentioned_items

    def pickup_item(self, item_name, collect_all=True):  # Changed default to True
        """Handle the pickup command with automatic collection of all items"""
        if not item_name:
            self.ui.text_widget.insert(tk.END, "What would you like to pick up?\n", "game_text")
            return

        # Try to find the exact item or a similar one
        target_item = None
        if item_name in self.state.environment_items:
            target_item = item_name
        else:
            similar_item = self.find_similar_item(item_name, self.state.environment_items)
            if similar_item:
                target_item = similar_item

        if not target_item:
            self.ui.text_widget.insert(tk.END, 
                f"There is no {item_name} or anything similar here to pick up.\n", "game_text")
            return

        if not self.is_item_pickable(target_item):
            self.ui.text_widget.insert(tk.END, f"You cannot pick up the {target_item}.\n", "game_text")
            return

        # Get quantity to collect
        available_quantity = self.state.environment_items[target_item]
        quantity_to_collect = available_quantity if collect_all else 1

        # Add to inventory
        self.state.inventory[target_item] = self.state.inventory.get(target_item, 0) + quantity_to_collect
        
        # Remove from environment
        if collect_all:
            del self.state.environment_items[target_item]
        else:
            self.state.environment_items[target_item] -= 1
            if self.state.environment_items[target_item] <= 0:
                del self.state.environment_items[target_item]
        
        # Display appropriate message
        if quantity_to_collect > 1:
            self.ui.text_widget.insert(tk.END, f"You picked up {quantity_to_collect} {target_item}s.\n", "game_text")
        else:
            self.ui.text_widget.insert(tk.END, f"You picked up a {target_item}.\n", "game_text")
        
        # Add extra detail about item uses when picked up
        if target_item in self.state.environment_items:
            usage_hints = {
                "flint": "could be useful for starting fires",
                "rope": "might help with climbing or crafting",
                "knife": "good for cutting and crafting",
                "berries": "can be eaten to restore food",
                "mushroom": "might be edible if you're sure they're safe",
                "herb": "could have medicinal properties"
            }
            
            for keyword, hint in usage_hints.items():
                if keyword in target_item.lower():
                    self.ui.text_widget.insert(tk.END, f"This {hint}.\n", "game_text")
                    break

        self.ui.update_inventory_display()

    def loot_all_items(self):
        if not self.state.environment_items:
            self.ui.text_widget.insert(tk.END, "There are no items to loot.\n", "game_text")
            return
        
        # Record items and their quantities first
        items_looted = [(item, self.state.environment_items[item]) for item in self.state.environment_items.keys()]

        # Pick up everything
        for item_name in list(self.state.environment_items.keys()):
            self.pickup_item(item_name, collect_all=True)

        # Summarize looted items
        summary = ", ".join(f"{qty} {name}" for name, qty in items_looted)
        self.ui.text_widget.insert(tk.END, f"You looted: {summary}\n", "game_text")
        self.ui.text_widget.insert(tk.END, "All items in the scene have been looted.\n", "game_text")

    def generate_scene_items(self, scene_description):
        """Generate contextual items based on scene description"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Analyze the scene and list items that could be picked up.
                Consider:
                1. Items explicitly mentioned in the scene
                2. Items that would logically be present
                3. Items that are realistic for 1897
                4. Only items that can actually be picked up and carried
                Format as JSON:
                {
                    "natural_items": {"item": quantity},
                    "found_items": {"item": quantity},
                    "valuable_items": {"item": quantity}
                }
                Natural items: plants, sticks, stones, etc.
                Found items: lost/discarded objects, tools, etc.
                Valuable items: rare/useful items worth collecting
                Keep quantities realistic (1-10)."""},
                {"role": "user", "content": f"List collectable items from this scene: {scene_description}"}
            ],
            max_tokens=150,
            temperature=0.7
        )

        try:
            items_data = json.loads(response.choices[0].message['content'])
            # Merge all categories into one dictionary
            all_items = {}
            for category in items_data.values():
                all_items.update(category)
            return all_items
        except json.JSONDecodeError:
            return {"stick": 2, "stone": 3}  # Fallback items

    def display_available_items(self, items):
        """Display available items in an organized way"""
        if not items:
            return

        # Group items by type for better organization
        natural_items = []
        found_items = []
        valuable_items = []

        natural_keywords = ["stick", "stone", "leaf", "berry", "herb", "root", "bark", "grass", "mushroom"]
        valuable_keywords = ["coin", "jewelry", "tool", "weapon", "metal", "leather", "cloth"]

        for item, qty in items.items():
            if any(keyword in item.lower() for keyword in natural_keywords):
                natural_items.append(f"{qty} {item}" if qty > 1 else item)
            elif any(keyword in item.lower() for keyword in valuable_keywords):
                valuable_items.append(f"{qty} {item}" if qty > 1 else item)
            else:
                found_items.append(f"{qty} {item}" if qty > 1 else item)

        self.ui.text_widget.insert(tk.END, "\nIn this area:\n", "game_text")
        
        if natural_items:
            self.ui.text_widget.insert(tk.END, "Natural items: " + ", ".join(natural_items) + "\n", "game_text")
        if found_items:
            self.ui.text_widget.insert(tk.END, "Found items: " + ", ".join(found_items) + "\n", "game_text")
        if valuable_items:
            self.ui.text_widget.insert(tk.END, "Valuable items: " + ", ".join(valuable_items) + "\n", "game_text")

    def show_environment(self):
        # ...existing code...
        
        # After generating description, show available items
        items = self.generate_scene_items()
        if items:
            item_list = ", ".join(f"{qty} {item}" if qty > 1 else item 
                                for item, qty in items.items())
            self.ui.text_widget.insert(tk.END, 
                f"Noticeable items in the area: {item_list}\n", "game_text")
        
        self.state.environment_items = items
        self.ui.text_widget.see(tk.END)

    def extract_items(self, description):
        """Extract items from environment description more effectively"""
        item_patterns = {
            "stick": ["stick", "branch", "twig", "wood"],
            "stone": ["stone", "rock", "pebble", "boulder"],
            "herb": ["herb", "plant", "flower"],
            "berry": ["berry", "berries", "fruit"],
            "mushroom": ["mushroom", "fungi", "fungus"],
            "vine": ["vine", "creeper", "rope"],
            "leaf": ["leaf", "leaves", "foliage"],
            "root": ["root", "roots"],
            "bark": ["bark"]
        }
        
        found_items = {}
        desc_lower = description.lower()
        
        # First check for explicit mentions with quantities
        quantity_words = ['several', 'few', 'many', 'some', 'scattered', 'numerous']
        
        for base_item, variants in item_patterns.items():
            for variant in [base_item] + variants:
                # Check for explicit mentions with quantities
                for qty_word in quantity_words:
                    if f"{qty_word} {variant}" in desc_lower:
                        found_items[base_item] = 3  # Multiple items found
                        break
                
                # Check for single items
                if any(f"a {variant}" in desc_lower or f"the {variant}" in desc_lower):
                    found_items[base_item] = 1
                    
                # Check for plural forms
                if variant + "s" in desc_lower:
                    found_items[base_item] = 2
        
        return found_items

    def find_similar_item(self, target_item, scene_items):
        """Find similar items that could be picked up"""
        similar_items = {
            "stick": ["branch", "twig", "wood"],
            "stone": ["rock", "pebble", "boulder"],
            "herb": ["plant", "flower"],
            "berry": ["berries", "fruit"],
            "mushroom": ["fungi", "fungus"],
            "vine": ["creeper", "rope"],
            "wood": ["log", "timber", "stick"],
            "leaf": ["leaves", "foliage"],
            "root": ["roots", "tuber"],
            "bark": ["tree bark", "bark pieces"]
        }
        
        # Convert target_item to singular form if plural
        if target_item.endswith('s'):
            target_item = target_item[:-1]
        
        # First check if the target item exists as a key in scene_items
        if target_item in scene_items:
            return target_item
            
        # Then check for similar items
        for base_item, variants in similar_items.items():
            if target_item in [base_item] + variants:
                # Check if base item or any variant is in the scene
                available_items = [item for item in [base_item] + variants 
                                if item in scene_items]
                if available_items:
                    return available_items[0]
                    
        return None

    def hunt_animal(self):
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Describe a hunting attempt in the wilderness.
                Write in third person perspective.
                Never start sentences with 'You' or 'Your'.
                Focus on the action and outcome.
                Example: 'The hunt yields a small rabbit.' NOT 'You catch a rabbit.'"""},
                {"role": "user", "content": "Describe the hunting outcome in 1-2 sentences."}
            ],
            max_tokens=50,
            temperature=0.7
        )
        hunting_description = self.clean_response(response.choices[0].message['content'])
        self.ui.text_widget.insert(tk.END, f"{hunting_description}\n", "game_text")
        self.ui.text_widget.see(tk.END)
        if "success" in hunting_description.lower():
            food_gain = 30
            self.state.energy = min(100, self.state.energy + food_gain)
            self.ui.food_label.config(text=f"Energy: {self.state.energy}")

    def craft_item(self, item_name):
        """Handle crafting with smart validation"""
        # Clean item name
        item_name = item_name.lower().strip()
        
        # List of nonsensical or impossible items
        impossible_items = [
            "car", "phone", "computer", "gun", "metal", "steel", "iron",
            "plastic", "glass", "concrete", "brick", "engine", "machine",
            "battery", "electricity", "robot", "airplane", "tank", "bomb"
        ]

        # Check if item is obviously impossible
        if any(word in item_name for word in impossible_items):
            self.ui.text_widget.insert(tk.END, 
                f"'{item_name}' cannot be crafted with 1897 technology and available materials.\n", "game_text")
            return

        # List of basic materials that can be used in crafting
        basic_materials = [
            "wood", "stone", "stick", "branch", "vine", "leather",
            "bone", "hide", "fiber", "leaf", "bark", "root", "grass",
            "sinew", "cord", "rope", "cloth", "fur", "feather"
        ]

        # If it's a completely new item, validate it makes sense for the setting
        if item_name not in self.state.crafting_recipes:
            # Check if it's too short or lacks meaning
            if len(item_name) < 3 or item_name in ["the", "and", "but", "for"]:
                self.ui.text_widget.insert(tk.END, "Please specify a valid item to craft.\n", "game_text")
                return

            self.ui.text_widget.insert(tk.END, 
                f"Attempting to devise a way to craft '{item_name}' using available materials...\n", "game_text")
            recipe = self.state.generate_crafting_recipe(item_name)
            
            # Validate the recipe uses only appropriate materials
            if recipe and all(any(material in mat for mat in basic_materials) 
                            for material in recipe["materials"].keys()):
                self.state.crafting_recipes[item_name] = recipe
                self.state.save_crafting_recipes()
                self.ui.text_widget.insert(tk.END, f"Figured out how to craft {item_name}.\n", "game_text")
            else:
                self.ui.text_widget.insert(tk.END, 
                    f"Unable to figure out how to craft '{item_name}' with available materials.\n", "game_text")
                return

        # Continue with existing crafting logic
        recipe = self.state.crafting_recipes[item_name]
        missing_materials = []
        substitutions = {}

        # Check for required materials or suitable substitutes
        for material, amount in recipe["materials"].items():
            if material in self.state.inventory and self.state.inventory[material] >= amount:
                continue
            
            # Look for similar items that could be used instead
            similar_item = self.state.find_similar_items(material)
            if similar_item and self.state.inventory.get(similar_item, 0) >= amount:
                substitutions[material] = similar_item
                continue
            
            missing_materials.append(f"{amount} {material}")

        if missing_materials:
            self.ui.text_widget.insert(tk.END, f"You need {', '.join(missing_materials)} to craft {item_name}.\n", "game_text")
            return

        # Use materials (including substitutions)
        for material, amount in recipe["materials"].items():
            actual_material = substitutions.get(material, material)
            self.state.inventory[actual_material] -= amount
            if self.state.inventory[actual_material] <= 0:
                del self.state.inventory[actual_material]

        # Add crafted item to inventory
        self.state.inventory[item_name] = self.state.inventory.get(item_name, 0) + 1
        
        # Show substitutions used
        if substitutions:
            subs_text = ", ".join(f"{orig} → {sub}" for orig, sub in substitutions.items())
            self.ui.text_widget.insert(tk.END, f"Crafted using substitutions: {subs_text}\n", "game_text")
        
        self.ui.text_widget.insert(tk.END, f"You successfully crafted a {item_name}.\n", "game_text")
        self.ui.update_inventory_display()

    def update_game_state(self, user_input):
        # Calculate time-based energy decay
        current_time = time.time()
        hours_passed = (current_time - self.state.last_action_time) / 3600
        self.state.energy = max(0, self.state.energy - int(hours_passed * self.state.energy_decay_rate))
        self.state.last_action_time = current_time

        # Update moves counter and affect health/energy based on action
        if any(word in user_input.lower() for word in ['go', 'walk', 'follow', 'climb', 'hike']):
            self.state.moves_since_rest += 1
            self.state.energy = max(0, self.state.energy - 2)
            if self.state.moves_since_rest > 5:
                self.state.health = max(0, self.state.health - 5)
                self.ui.text_widget.insert(tk.END, "You're getting tired. You should rest soon.\n", "game_text")

        if "eat" in user_input:
            if "food" in user_input.lower() or any(food in user_input.lower() for food in ["berries", "meat", "fish"]):
                food_gain = 20
                self.state.energy = min(100, self.state.energy + food_gain)
                self.ui.text_widget.insert(tk.END, f"You feel less hungry.\n", "game_text")
            else:
                self.ui.text_widget.insert(tk.END, "You need to specify what to eat.\n", "game_text")

        if "rest" in user_input:
            self.state.moves_since_rest = 0
            health_gain = 15
            self.state.health = min(100, self.state.health + health_gain)
            self.state.energy = max(0, self.state.energy - 5)
            self.ui.text_widget.insert(tk.END, "You feel refreshed after resting.\n", "game_text")

        # Check critical conditions
        if self.state.energy <= 0:
            self.state.health = max(0, self.state.health - 10)
            self.ui.text_widget.insert(tk.END, "You are starving and losing health!\n", "game_text")
        elif self.state.energy <= 20:
            self.ui.text_widget.insert(tk.END, "You are getting very hungry...\n", "game_text")

        if self.state.health <= 0:
            self.ui.text_widget.insert(tk.END, "You have collapsed from exhaustion and hunger...\n", "game_text")

        # Update display
        self.ui.health_label.config(text=f"Health: {self.state.health}")
        self.ui.energy_label.config(text=f"Energy: {self.state.energy}")

    def extract_items_from_description(self, description):
        """Extract mentioned items from scene description and generate quantities"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Given a scene description, identify items that could be collected.
                Return only a JSON object mapping items to quantities.
                Example: {"fallen branch": 2, "wild mushrooms": 3, "flint stone": 1}
                Only include items that:
                1. Are explicitly or implicitly mentioned in the scene
                2. Could realistically be picked up and carried
                3. Would exist in 1897
                4. Have practical survival value"""},
                {"role": "user", "content": f"List collectable items from: {description}"}
            ],
            max_tokens=150,
            temperature=0.7
        )

        try:
            items = json.loads(response.choices[0].message['content'])
            return items
        except json.JSONDecodeError:
            return {"stick": 1}  # Fallback item

    def extract_scene_items(self, description):
        """Extract all potential items from scene description"""
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": """Create a simple JSON object mapping collectible items to quantities.
                Only include items that:
                1. Are explicitly mentioned in the scene
                2. Could be picked up and carried
                3. Would exist in 1897
                Format: {"item": quantity}
                Example: {"wild berries": 3, "flint stone": 2, "rusted knife": 1}"""},
                {"role": "user", "content": f"List collectible items from: {description}"}
            ],
            max_tokens=50,
            temperature=0.5
        )

        try:
            return json.loads(response.choices[0].message['content'])
        except json.JSONDecodeError:
            return {"stick": 1}  # Fallback item

    def list_scene_items(self):
        if not self.state.environment_items:
            self.ui.text_widget.insert(tk.END, "No items are available here.\n", "game_text")
            return
        items_list = ", ".join(self.state.environment_items.keys())
        self.ui.text_widget.insert(tk.END, f"Pickupable items: {items_list}\n", "game_text")

    def consume_item(self, item_name):
        if item_name not in self.state.inventory or self.state.inventory[item_name] < 1:
            self.ui.text_widget.insert(tk.END, f"You have no {item_name} to consume.\n", "game_text")
            return
        self.state.inventory[item_name] -= 1
        if self.state.inventory[item_name] <= 0:
            del self.state.inventory[item_name]
        self.ui.text_widget.insert(tk.END, f"You consumed a {item_name}.\n", "game_text")
        self.ui.update_inventory_display()

    def use_item(self, item_name, usage_desc=""):
        """Handle item usage with optional AI frame adaptation and transformations."""
        if item_name not in self.state.inventory or self.state.inventory[item_name] <= 0:
            self.ui.text_widget.insert(tk.END, f"You don't have any {item_name} to use.\n", "game_text")
            return

        # Optional usage description -> AI frame adaptation
        if usage_desc:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": """Given the player's usage description, adapt the current game frame to reflect changes caused by item usage. Return only the updated JSON of the game_frame."""},
                    {"role": "user", "content": f"Current frame: {json.dumps(self.load_frame(), indent=4)}\nItem used: {item_name}\nUsage description: {usage_desc}"}
                ],
                max_tokens=200,
                temperature=0.7
            )
            updated_frame = response.choices[0].message['content'].strip()
            self.save_frame(updated_frame)
            self.ui.text_widget.insert(tk.END, f"You used {item_name}: {usage_desc}\n", "game_text")
        else:
            self.ui.text_widget.insert(tk.END, f"You use the {item_name}.\n", "game_text")

        # Handle item interactions
        item_interactions = {
            "water canteen": {
                "near_water": True,
                "transforms_to": "full canteen",
                "message": "You fill the canteen with water."
            },
            "flint": {
                "requires": ["stick", "leaf"],
                "creates": "fire",
                "message": "You start a fire using the flint."
            },
            "berries": {
                "consumable": True,
                "food_value": 10,
                "message": "You eat the berries, restoring some energy."
            },
            "snare": {
                "consumable": True,
                "message": "You set up a snare trap in the underbrush."
            }
        }

        if item_name in item_interactions:
            interaction = item_interactions[item_name]
            # ...existing code to check requirements, transform, consume, restore food, etc...
            self.ui.text_widget.insert(tk.END, interaction["message"] + "\n", "game_text")
            # ...existing code...
        else:
            # Default usage text already inserted above

            # Example: Mark item as used in game_frame (if desired)
            # with open("game_frame.json", "r+") as f:
            #     # ...existing code...

            pass

        # Consume item if it's one-time use
        self.state.inventory[item_name] -= 1
        if self.state.inventory[item_name] <= 0:
            del self.state.inventory[item_name]

        self.ui.update_inventory_display()

    def load_frame(self):
        with open("game_frame.json", "r") as f:
            return json.load(f)

    def save_frame(self, frame_str):
        try:
            data = json.loads(frame_str)
            with open("game_frame.json", "w") as f:
                json.dump(data, f, indent=4)
        except:
            pass

    def store_location(self, location_description):
        """Update the current location in game_frame.json"""
        frame_data = self.load_frame()
        frame_data["scene_context"]["location"] = location_description
        self.save_frame(json.dumps(frame_data))

    def complete_goal_if_applicable(self, user_input):
        goal_reached = self.state.check_if_goal_reached(user_input)
        if goal_reached:
            self.state.progress_to_next_act()

    def npc_gives_item(self, npc_name, item_name):
        """
        NPC gives an item to the player. Update inventory and NPC disposition.
        """
        # ...existing code...
        self.update_npc_disposition(npc_name, 1)
        # ...existing code...

    def npc_requests_item(self, npc_name, item_name):
        """
        NPC requests an item from the player. If player gives it, update memory.
        """
        # ...existing code...
        self.update_npc_disposition(npc_name, 1)
        # ...existing code...

    def npc_feeds_player(self, npc_name):
        """
        NPC feeds the player, increasing player's food and good deeds.
        """
        # ...existing code...
        self.state.energy += 15  # example
        self.update_npc_disposition(npc_name, 2)

    def update_npc_disposition(self, npc_name, change):
        """
        Increment or decrement good/bad deeds in game_characters.json for the NPC.
        """
        # ...existing code...
        # Load NPC data, adjust memory.good_deeds and disposition by 'change'
        # Save updated data back to game_characters.json

    def sleep(self):
        """
        Clear the chat and fully restore the character's energy if they have shelter.
        """
        # Check if player has built/found shelter
        if "shelter" not in self.state.inventory and not self.is_near_shelter():
            self.ui.text_widget.insert(tk.END, 
                "You need a shelter to sleep safely. Try crafting one or finding a safe place.\n", "game_text")
            return
            
        self.ui.text_widget.delete("1.0", tk.END)
        self.state.energy = 100
        self.state.health = min(100, self.state.health + 20)  # Bonus health regeneration while sleeping
        
        # Generate peaceful sleeping scene
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{
                "role": "system",
                "content": "Describe a peaceful night's rest in a shelter on the Appalachian Trail in 1897. Keep it to 1-2 sentences."
            }, {
                "role": "user",
                "content": "Describe the scene"
            }],
            max_tokens=50
        )
        sleep_scene = self.clean_response(response.choices[0].message['content'])
        
        self.ui.text_widget.insert(tk.END, f"{sleep_scene}\n", "game_text")
        self.ui.text_widget.insert(tk.END, "You feel well-rested and refreshed.\n", "game_text")
        
    def is_near_shelter(self):
        """Check if player is near a natural or man-made shelter"""
        frame_data = self.load_frame()
        scene_text = frame_data.get("scene_data", "").lower()
        shelter_keywords = ["cave", "cabin", "shelter", "inn", "house", "camp", "lodge"]
        return any(keyword in scene_text for keyword in shelter_keywords)

    def sleep(self):
        """
        Clear the chat and fully restore the character's energy.
        """
        self.ui.text_widget.delete("1.0", tk.END)
        self.state.energy = 100
        self.ui.text_widget.insert(tk.END, "You feel well-rested.\n", "game_text")
