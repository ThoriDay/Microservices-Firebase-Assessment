from flask import Flask, request, jsonify
import os
import sqlite3
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

# SQLite Database Configuration
DATABASE_FILE = 'cells.db'

# Firebase Configuration
FBASE_NAME = os.getenv('FBASE')  # Read Firebase database name from environment variable
cred = credentials.Certificate('path/to/serviceAccountKey.json')  # Replace with path to service account key JSON file
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://ecmca-414de-default-rtdb.europe-west1.firebasedatabase.app/'
})

# Create SQLite database if not exists
def create_sqlite_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cells (
            id TEXT PRIMARY KEY,
            formula TEXT
        )
    ''')
    conn.commit()
    conn.close()

# SQLite: Create cell
def create_sqlite_cell(cell_id, formula):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO cells (id, formula) VALUES (?, ?)', (cell_id, formula))
    conn.commit()
    conn.close()

# SQLite: Get cell
def get_sqlite_cell(cell_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT formula FROM cells WHERE id = ?', (cell_id,))
    cell = cursor.fetchone()
    conn.close()
    return cell[0] if cell else None

# SQLite: Delete cell
def delete_sqlite_cell(cell_id):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM cells WHERE id = ?', (cell_id,))
    conn.commit()
    conn.close()

# Firebase: Create cell
def create_firebase_cell(cell_id, formula):
    db.reference('cells/' + cell_id).set({'formula': formula})

# Firebase: Get cell
def get_firebase_cell(cell_id):
    return db.reference('cells/' + cell_id).get()

# Firebase: Delete cell
def delete_firebase_cell(cell_id):
    db.reference('cells/' + cell_id).delete()

# Create cell route
@app.route('/cells/<cell_id>', methods=['PUT'])
def create_cell(cell_id):
    data = request.get_json()
    formula = data.get('formula')
    if formula:
        if storage_option == 'sqlite':
            create_sqlite_cell(cell_id, formula)
        elif storage_option == 'firebase':
            create_firebase_cell(cell_id, formula)
        return jsonify({'message': f'Cell {cell_id} created successfully'}), 201
    else:
        return jsonify({'error': 'Formula is required'}), 400

# Get cell route
@app.route('/cells/<cell_id>', methods=['GET'])
def get_cell(cell_id):
    if storage_option == 'sqlite':
        formula = get_sqlite_cell(cell_id)
    elif storage_option == 'firebase':
        formula = get_firebase_cell(cell_id).get('formula')
    if formula:
        return jsonify({'id': cell_id, 'formula': formula}), 200
    else:
        return jsonify({'error': f'Cell {cell_id} not found'}), 404

# Delete cell route
@app.route('/cells/<cell_id>', methods=['DELETE'])
def delete_cell(cell_id):
    if storage_option == 'sqlite':
        delete_sqlite_cell(cell_id)
    elif storage_option == 'firebase':
        delete_firebase_cell(cell_id)
    return '', 204

# List cells route
@app.route('/cells', methods=['GET'])
def list_cells():
    if storage_option == 'sqlite':
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM cells')
        cells = cursor.fetchall()
        conn.close()
        cell_ids = [cell[0] for cell in cells]
    elif storage_option == 'firebase':
        cell_ids = list(db.reference('cells').get().keys())
    return jsonify(cell_ids), 200

if __name__ == '__main__':
    # Check storage option
    storage_option = os.getenv('STORAGE_OPTION', 'sqlite')
    if storage_option not in ['sqlite', 'firebase']:
        raise ValueError('Invalid storage option. Use either "sqlite" or "firebase".')

    if storage_option == 'sqlite':
        create_sqlite_db()

    app.run(host='0.0.0.0', port=3000)
