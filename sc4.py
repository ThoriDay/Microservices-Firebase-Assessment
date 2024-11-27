from flask import Flask, request, jsonify, make_response
import sqlite3
import requests
import sys
import os

app = Flask(__name__)
DATABASE = 'cells.db'
FIREBASE_URL = os.environ.get('FIREBASE_DB_URL')

storage_backend = 'sqlite'
if '-r' in sys.argv:
    index = sys.argv.index('-r')
    if index + 1 < len(sys.argv) and sys.argv[index + 1] in ['firebase', 'sqlite']:
        storage_backend = sys.argv[index + 1]

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    if storage_backend == 'sqlite':
        conn = get_db_connection()
        conn.execute('''CREATE TABLE IF NOT EXISTS cells
                        (id TEXT PRIMARY KEY, formula TEXT)''')
        conn.commit()
        conn.close()

def firebase_request(method, cell_id=None, data=None):
    url = f"{FIREBASE_URL}/cells/{cell_id}.json" if cell_id else f"{FIREBASE_URL}/cells.json"
    if method == 'get' or method == 'delete':
        response = requests.request(method, url)
    else:
        response = requests.request(method, url, json=data)
    return response.json()

def fetch_cell_value(cell_id):
    """Fetch the value of a cell by its ID from Firebase or SQLite."""
    if storage_backend == 'firebase':
        result = firebase_request('get', cell_id=cell_id)
        if result and 'formula' in result:
            # Assuming direct value or another reference, not evaluating nested formulas
            return simple_evaluate(result['formula'])
    else:
        conn = get_db_connection()
        cell = conn.execute('SELECT * FROM cells WHERE id = ?', (cell_id,)).fetchone()
        conn.close()
        if cell:
            # Similarly, assuming direct value or another reference
            return simple_evaluate(cell['formula'])
    return 0  # Default if cell not found or other error

def simple_evaluate(expression):
    """Evaluate an expression that may contain cell references."""
    tokens = expression.split()
    result = 0
    current_operator = "+"
    for token in tokens:
        if token in {'+', '-', '*', '/'}:
            current_operator = token
        else:
            try:
                if token.isalpha():  # Assuming a simple way to check if it's a cell reference
                    value = fetch_cell_value(token)
                else:
                    value = float(token)
                
                if current_operator == '+':
                    result += value
                elif current_operator == '-':
                    result -= value
                elif current_operator == '*':
                    result *= value
                elif current_operator == '/':
                    result /= value
            except ValueError:
                # Handling case where conversion to float fails
                return "Error: Invalid formula"
    return result


@app.route('/cells/<cell_id>', methods=['PUT'])
def create_cell(cell_id):
    data = request.json
    if not data or 'id' not in data or 'formula' not in data or data['id'] != cell_id:
        return make_response(jsonify({"error": "Missing id, formula, or id mismatch"}), 400)

    if storage_backend == 'firebase':
        existing = firebase_request('get', cell_id)
        status_code = 204 if existing else 201
        firebase_request('put', cell_id, data)
        return make_response("", status_code)
    else:
        conn = get_db_connection()
        existing_cell = conn.execute('SELECT * FROM cells WHERE id = ?', (cell_id,)).fetchone()
        status_code = 204 if existing_cell else 201
        conn.execute('REPLACE INTO cells (id, formula) VALUES (?, ?)', (cell_id, data['formula']))
        conn.commit()
        conn.close()
        return make_response("", status_code)

@app.route('/cells/<cell_id>', methods=['GET'])
def read_cell(cell_id):
    if storage_backend == 'firebase':
        result = firebase_request('get', cell_id=cell_id)
        if result is None or 'error' in result:
            return make_response(jsonify({"error": "Cell not found"}), 404)
        try:
            evaluated_result = simple_evaluate(result.get('formula', '0'))
            return jsonify({"id": cell_id, "formula": result.get('formula'), "result": evaluated_result})
        except Exception as e:
            return make_response(jsonify({"error": "Invalid formula", "exception": str(e)}), 400)
    else:
        conn = get_db_connection()
        cell = conn.execute('SELECT * FROM cells WHERE id = ?', (cell_id,)).fetchone()
        conn.close()
        if cell:
            try:
                evaluated_result = simple_evaluate(cell['formula'])
                return jsonify({"id": cell['id'], "formula": cell['formula'], "result": evaluated_result})
            except Exception as e:
                return make_response(jsonify({"error": "Invalid formula", "exception": str(e)}), 400)
        else:
            return make_response(jsonify({"error": "Cell not found"}), 404)


@app.route('/cells/<cell_id>', methods=['DELETE'])
def delete_cell(cell_id):
    if storage_backend == 'firebase':
        firebase_request('delete', cell_id=cell_id)
    else:
        conn = get_db_connection()
        conn.execute('DELETE FROM cells WHERE id = ?', (cell_id,))
        conn.commit()
        conn.close()
    return make_response("", 204)

@app.route('/cells', methods=['GET'])
def list_cells():
    if storage_backend == 'firebase':
        result = firebase_request('get')
        if not result:
            return jsonify([])
        return jsonify(list(result.keys()))
    else:
        conn = get_db_connection()
        cells = conn.execute('SELECT id FROM cells').fetchall()
        conn.close()
        return jsonify([cell['id'] for cell in cells])

if __name__ == '__main__':
    if not os.path.exists(DATABASE) and storage_backend == 'sqlite':
        init_db()
    app.run(port=3000)
