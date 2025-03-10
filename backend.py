from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import datetime
import os

app = Flask(__name__)
CORS(app)


def init_db():
    if not os.path.exists('heartrate.db'):
        conn = sqlite3.connect('heartrate.db')
        c = conn.cursor()
        c.execute('''
            CREATE TABLE heartrates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                heart_rate INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        conn.commit()
        conn.close()
        print("Database created successfully")
    else:
        print("Database already exists")

# Initialize the database
init_db()

@app.route('/api/heartrate', methods=['POST'])
def store_heartrate():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        heart_rate = data.get('heart_rate')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        
        # Validate heart rate
        if not heart_rate or not isinstance(heart_rate, int):
            return jsonify({'error': 'Invalid heart rate value'}), 400
            
        # Store in database
        conn = sqlite3.connect('heartrate.db')
        c = conn.cursor()
        c.execute('INSERT INTO heartrates (device_id, heart_rate, timestamp) VALUES (?, ?, ?)',
                  (device_id, heart_rate, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Heart rate recorded successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/heartrate', methods=['GET'])
def get_heartrates():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('heartrate.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM heartrates'
        params = []
        
        if device_id:
            query += ' WHERE device_id = ?'
            params.append(device_id)
            
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        c.execute(query, params)
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Run the server
if __name__ == '__main__':
    print("Starting Heart Rate Server...")
    app.run(host='192.168.0.162', port=5000, debug=True)
