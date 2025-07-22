from tinydb import TinyDB, Query
import copy
import math

class CraftingCalculator:
    def __init__(self, db_handler):
        self.db_handler = db_handler

    def calculate_chain_from_leaves(self, productId, available, game="Unknown"):
        """
        Calculate crafting tree for a product.
        Always returns what's needed to make 1 unit of the product.
        """
        product = self._get_product(productId, game)
        if not product:
            return None

        ratio = product.get("ratio", [1])
        output_qty = ratio[0] if ratio and len(ratio) > 0 else 1
        ingredients = product.get('ingredients', [])

        if not ingredients:
            return {
                "id": productId,
                "amount": 1,
                "ingredients": [],
                "recipe_output": 1
            }

        ingredient_trees = []
        for i, ingredient in enumerate(ingredients):
            ing_id = ingredient['id']
            ing_amount_needed = ratio[i + 1] if i + 1 < len(ratio) else ingredient.get('amount', 1)
            ingredient_tree = self.calculate_chain_from_leaves(ing_id, available, game)
            if ingredient_tree:
                if "recipe_output" not in ingredient_tree:
                    ingredient_tree["recipe_output"] = ingredient_tree["amount"]
                ingredient_tree['amount'] = ing_amount_needed
                ingredient_trees.append(ingredient_tree)

        tree = {
            "id": productId,
            "amount": 1,
            "recipe_output": output_qty,
            "ingredients": ingredient_trees
        }
        return tree

    def scale_tree_amounts(self, tree, target_amount):
        """
        Scale tree amounts based on target output.
        Uses recipe batch logic but displays needed amount.
        """
        if not tree:
            return None

        scaled_tree = copy.deepcopy(tree)
        is_raw_material = not tree.get('ingredients') or len(tree.get('ingredients', [])) == 0

        if is_raw_material:
            scaled_tree['amount'] = target_amount
            return scaled_tree

        recipe_output = tree.get('recipe_output', 1)
        batches_needed = math.ceil(target_amount / recipe_output)
        actual_output = batches_needed * recipe_output

        scaled_tree['amount'] = target_amount
        scaled_tree['batches'] = batches_needed
        scaled_tree['produces'] = actual_output

        if 'ingredients' in tree and tree['ingredients']:
            for i, ingredient in enumerate(scaled_tree['ingredients']):
                original_amount = tree['ingredients'][i].get('amount', 1)
                total_needed = original_amount * batches_needed
                scaled_ingredient = self.scale_tree_amounts(ingredient, total_needed)
                if scaled_ingredient:
                    scaled_tree['ingredients'][i] = scaled_ingredient

        return scaled_tree

    def _get_product(self, productId, game="Unknown"):
        """Helper to get product from database"""
        table = self.db_handler.crafting_tree
        Item = self.db_handler.db.table(table.name)
        return Item.get((Query().id == productId) & (Query().game == game))

    def max_craftable(self, productId, available, use_alternatives=False, game="Unknown"):
        """Calculate maximum craftable amount with available resources"""
        product = self._get_product(productId, game)
        if not product:
            return 0

        ratio = product.get("ratio", [1])
        output_qty = ratio[0] if ratio else 1
        ingredients = product.get('ingredients', [])

        if not ingredients:
            return available.get(productId, 0)

        min_batches = float('inf')
        for i, ingredient in enumerate(ingredients):
            ing_id = ingredient['id']
            ing_amount_needed = ratio[i + 1] if i + 1 < len(ratio) else ingredient.get('amount', 1)
            available_amount = available.get(ing_id, 0)
            if ing_amount_needed > 0:
                possible_batches = available_amount // ing_amount_needed
                min_batches = min(min_batches, possible_batches)

        if min_batches == float('inf'):
            min_batches = 0

        return min_batches * output_qty

    def ingredient_breakdown(self, productId, available, use_alternatives=False, game="Unknown"):
        """Get ingredient breakdown for a product"""
        product = self._get_product(productId, game)
        if not product:
            return {}

        ratio = product.get("ratio", [1])
        ingredients = product.get('ingredients', [])
        breakdown = {}

        for i, ingredient in enumerate(ingredients):
            ing_id = ingredient['id']
            ing_amount_needed = ratio[i + 1] if i + 1 < len(ratio) else ingredient.get('amount', 1)
            available_amount = available.get(ing_id, 0)
            breakdown[ing_id] = {
                "required_per_craft": ing_amount_needed,
                "available": available_amount
            }

        return breakdown

    def recursive_craftable_breakdown(self, productId, available, use_alternatives=False, game="Unknown"):
        """Get recursive breakdown of what can be crafted"""
        return self.ingredient_breakdown(productId, available, use_alternatives, game)