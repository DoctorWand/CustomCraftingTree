from flask import Flask, jsonify, request
from databaseHandler import DatabaseHandler
from craftingCalculator import CraftingCalculator

app = Flask(__name__)

db = DatabaseHandler()
calculator = CraftingCalculator(db)

@app.route('/api/products')
def get_products():
    game = request.args.get('game', '')
    items = [item for item in db.get_crafting_tree() if "product" in item.get("tags", [])]
    if game == "":
        return jsonify(items[:50])
    else:
        filtered = [item for item in items if item.get("game", "Unknown") == game]
        return jsonify(filtered)

@app.route('/api/raw-materials')
def get_raw_materials():
    game = request.args.get('game', '')
    items = [item for item in db.get_crafting_tree() if "raw_material" in item.get("tags", [])]
    if game == "":
        return jsonify(items[:50])
    else:
        filtered = [item for item in items if item.get("game", "Unknown") == game]
        return jsonify(filtered)

@app.route('/api/games')
def get_games():
    games = db.get_games()
    return jsonify(games)

@app.route('/api/search')
def search_items():
    query = request.args.get('q', '').lower()
    game = request.args.get('game', 'Unknown')
    results = [item for item in db.get_crafting_tree() if query in item.get("name", "").lower() and (item.get("game", "Unknown") == game or game == "")]
    return jsonify(results)

@app.route('/api/item/<item_id>', methods=['PUT'])
def edit_item(item_id):
    data = request.json
    game = request.args.get('game', 'Unknown')
    table = request.args.get('table', 'craftingTree')
    result = db.edit_item(item_id, data, game, table)
    return jsonify({"message": result})

@app.route('/api/item/<item_id>', methods=['DELETE'])
def delete_item(item_id):
    game = request.args.get('game', 'Unknown')
    table = request.args.get('table', 'craftingTree')
    result = db.delete_item(item_id, game, table)
    return jsonify({"message": result})

@app.route('/api/item', methods=['POST'])
def add_item():
    data = request.json
    game = request.args.get('game', 'Unknown')
    itemId = data.get('id')
    quantity = data.get('quantity', 1)
    ingredients = data.get('ingredients', [])
    description = data.get('description', "")
    result = db.add_item(itemId, quantity, ingredients, game, description)
    return jsonify({"message": result})

@app.route('/api/crafting-tree')
def get_crafting_tree():
    game = request.args.get('game', 'Unknown')
    items = [item for item in db.get_crafting_tree() if item.get("game", "Unknown") == game or game == ""]
    return jsonify(items)

@app.route('/api/crafting-tree-full')
def get_crafting_tree_full():
    try:
        item_id = request.args.get('id')
        game = request.args.get('game', 'Unknown')
        target_amount = int(request.args.get('target_amount', 1))
        available = {k: int(v) for k, v in request.args.items() if k not in ['id', 'game', 'target_amount']}
        
        print(f"API: Calculating tree for {item_id} with target amount {target_amount} and available {available}")
        
        tree = calculator.calculate_chain_from_leaves(item_id, available, game)
        
        if tree is None:
            return jsonify({"error": "Item not found"}), 404
        
        if target_amount != tree.get('amount', 1):
            tree = calculator.scale_tree_amounts(tree, target_amount)
            
        return jsonify(tree)
    except Exception as e:
        print(f"❌ API Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/max-craftable')
def get_max_craftable():
    item_id = request.args.get('id')
    game = request.args.get('game', 'Unknown')
    available = {k: int(v) for k, v in request.args.items() if k not in ['id', 'game']}
    max_amount = calculator.max_craftable(item_id, available, False, game)
    breakdown = calculator.ingredient_breakdown(item_id, available, False, game)
    return jsonify({"max_craftable": max_amount, "breakdown": breakdown})

@app.route('/api/craftable-breakdown')
def get_craftable_breakdown():
    item_id = request.args.get('id')
    game = request.args.get('game', 'Unknown')
    available = {k: int(v) for k, v in request.args.items() if k not in ['id', 'game']}
    breakdown = calculator.recursive_craftable_breakdown(item_id, available, False, game)
    return jsonify(breakdown)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)