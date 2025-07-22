from tinydb import TinyDB, Query

class DatabaseHandler:
    def __init__(self, db_path='crafting_tree.json'):
        self.db = TinyDB(db_path)
        self.crafting_tree = self.db.table('craftingTree')
        self.alternatives = self.db.table('alternatives')
        self.games = self.db.table('games')

    def get_crafting_tree(self):
        return self.crafting_tree.all()

    def get_alternatives(self):
        return self.alternatives.all()

    def get_games(self):
        """Return all games from the games table as a list of dicts."""
        return self.games.all()

    def get_game_names(self):
        """Return all game names as a list (for dropdowns, etc)."""
        return [game['name'] for game in self.games.all()]

    def add_item(self, itemId, quantity, ingredients=None, game="Unknown", description=""):
        if ingredients is None:
            ingredients = []

        Item = Query()
        if self.crafting_tree.contains(Item.id == itemId):
            return "Item already exists in crafting tree. Use add_alternative to add an alternative recipe."

        for ingredient in ingredients:
            if not self.crafting_tree.contains(Item.id == ingredient['id']):
                self.add_item(ingredient['id'], 1, [], game)

        ratio = [quantity] + [ingredient.get('amount', 1) for ingredient in ingredients]

        self.crafting_tree.insert({
            "id": itemId,
            "name": itemId,
            "game": game,
            "description": description,
            "alternatives": 0,
            "tags": ["raw_material"] if not ingredients else ["product"],
            "quantity": quantity,
            "ingredients": ingredients,
            "ratio": ratio
        })

        for ingredient in ingredients:
            self.__update_tags(ingredient['id'], game=game, table="craftingTree")

        return "Item added successfully."

    def __update_tags(self, itemId, game="Unknown", table="craftingTree"):
        Item = Query()
        db_table = self.crafting_tree if table == "craftingTree" else self.alternatives
        result = db_table.get((Item.id == itemId) & (Item.game == game))
        if not result:
            return

        tags = []
        if result.get('ingredients'):
            tags.append("product")
        if any(itemId == ing.get('id') for item in db_table.search(Item.game == game) for ing in item.get('ingredients', [])):
            tags.append("ingredient")
        if not result.get('ingredients'):
            tags.append("raw_material")
        db_table.update({'tags': tags, 'game': game}, (Item.id == itemId) & (Item.game == game))

    def add_alternative(self, name, quantity, ingredients, game="Unknown", description=""):
        Item = Query()
        item = self.crafting_tree.get(Item.id == name)
        if not item:
            return "Item does not exist in crafting tree. Use add_item to add a new item."

        alt_count = item.get('alternatives', 0) + 1
        alt_id = f"{name} A{alt_count}"

        self.crafting_tree.update({'alternatives': alt_count}, Item.id == name)

        ratio = [quantity] + [ingredient.get('amount', 1) for ingredient in ingredients]

        self.alternatives.insert({
            "id": alt_id,
            "name": name,
            "game": game,
            "description": description,
            "tags": ["product"],
            "quantity": quantity,
            "ingredients": ingredients,
            "ratio": ratio
        })
        return "Alternative recipe added successfully."

    def edit_item(self, itemId, updates, game="Unknown", table="craftingTree"):
        Item = Query()
        db_table = self.crafting_tree if table == "craftingTree" else self.alternatives
        if not db_table.contains((Item.id == itemId) & (Item.game == game)):
            return "Item not found."
        
        if "ingredients" in updates:
            for ing in updates["ingredients"]:
                if not self.crafting_tree.contains(Item.id == ing['id']):
                    self.add_item(ing['id'], 1, [], game)
        
        if "ingredients" in updates and "ratio" not in updates:
            quantity = updates.get("quantity", 1)
            ingredients = updates.get("ingredients", [])
            updates["ratio"] = [quantity] + [ing.get('amount', 1) for ing in ingredients]
        
        db_table.update(updates, (Item.id == itemId) & (Item.game == game))
        self.__update_tags(itemId, game=game, table=table)
        if "ingredients" in updates:
            for ing in updates["ingredients"]:
                self.__update_tags(ing['id'], game=game, table=table)
        return "Item updated successfully."

    def delete_item(self, itemId, game="Unknown", table="craftingTree"):
        Item = Query()
        db_table = self.crafting_tree if table == "craftingTree" else self.alternatives
        if not db_table.contains((Item.id == itemId) & (Item.game == game)):
            return "Item not found."
        item = db_table.get((Item.id == itemId) & (Item.game == game))
        ingredients = item.get("ingredients", []) if item else []
        db_table.remove((Item.id == itemId) & (Item.game == game))
        for ing in ingredients:
            self.__update_tags(ing['id'], game=game, table=table)
        referencing_items = [
            entry for entry in db_table.search(Item.game == game)
            if any(itemId == ing.get('id') for ing in entry.get('ingredients', []))
        ]
        for entry in referencing_items:
            self.__update_tags(entry['id'], game=game, table=table)
        return "Item deleted successfully."

    def add_game(self, game_name, description=""):
        Game = Query()
        if self.games.contains(Game.name == game_name):
            return "Game already exists."
        self.games.insert({
            "name": game_name,
            "description": description
        })
        return "Game added successfully."

    def delete_game(self, game_name):
        Game = Query()
        self.games.remove(Game.name == game_name)
        Item = Query()
        updated = self.crafting_tree.update({"game": "Unknown"}, Item.game == game_name)
        return f"Moved {len(updated)} items to 'Unknown' and deleted game '{game_name}'."

    def edit_game(self, old_name, new_name, description=""):
        Game = Query()
        self.games.update({"name": new_name, "description": description}, Game.name == old_name)
        Item = Query()
        updated = self.crafting_tree.update({"game": new_name}, Item.game == old_name)
        return f"Renamed game '{old_name}' to '{new_name}' for {len(updated)} items."