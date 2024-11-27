from flask import Flask, request, jsonify, make_response
import sqlite3
import os

app = Flask(__name__)
DATABASE = 'cells.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS cells
                 (id TEXT PRIMARY KEY, formula TEXT)''')
    conn.commit()
    conn.close()

# Modify create_cell function to distinguish between creating and updating cells
@app.route('/cells/<cell_id>', methods=['PUT'])
def create_cell(cell_id):
    data = request.json
    if not data or 'id' not in data or 'formula' not in data:
        return make_response(jsonify({"error": "Missing id or formula"}), 400)
    
    # Check if cell exists to determine the correct status code
    conn = get_db_connection()
    existing_cell = conn.execute('SELECT * FROM cells WHERE id = ?', (cell_id,)).fetchone()
    status_code = 204 if existing_cell else 201
    
    # Perform REPLACE operation as before
    conn.execute('REPLACE INTO cells (id, formula) VALUES (?, ?)', (data['id'], data['formula']))
    conn.commit()
    conn.close()
    
    return make_response("", status_code)


# Simplified arithmetic evaluator
def simple_evaluate(expression):
    # Tokenize the expression by spaces for simplicity. This requires that the input formula is well-formatted.
    tokens = expression.split()
    result = 0
    current_operator = "+"
    for token in tokens:
        if token in {'+', '-', '*', '/'}:
            current_operator = token
        else:
            if current_operator == '+':
                result += float(token)
            elif current_operator == '-':
                result -= float(token)
            elif current_operator == '*':
                result *= float(token)
            elif current_operator == '/':
                result /= float(token)
    return result

# Adjusting the read_cell function to use simple_evaluate for formula evaluation
@app.route('/cells/<cell_id>', methods=['GET'])
def read_cell(cell_id):
    conn = get_db_connection()
    cell = conn.execute('SELECT * FROM cells WHERE id = ?', (cell_id,)).fetchone()
    conn.close()
    if cell:
        formula = cell['formula']
        try:
            # Use the simple_evaluate function to calculate the result of the formula
            result = simple_evaluate(formula)
            return jsonify({"id": cell['id'], "formula": str(result)})
        except Exception as e:
            return make_response(jsonify({"error": "Invalid formula"}), 400)
    else:
        return make_response(jsonify({"error": "Cell not found"}), 404)


@app.route('/cells/<cell_id>', methods=['DELETE'])
def delete_cell(cell_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM cells WHERE id = ?', (cell_id,))
    conn.commit()
    conn.close()
    return make_response("", 204)

@app.route('/cells', methods=['GET'])
def list_cells():
    conn = get_db_connection()
    cells = conn.execute('SELECT id FROM cells').fetchall()
    conn.close()
    return jsonify([cell['id'] for cell in cells])

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    app.run(port=3000)
