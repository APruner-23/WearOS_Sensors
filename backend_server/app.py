from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
import datetime
import os
import json

app = Flask(__name__)
CORS(app)

os.makedirs('templates', exist_ok=True)

def init_db():
    if not os.path.exists('health_data.db'):
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        
        # Create heartrates table
        c.execute('''
            CREATE TABLE heartrates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                heart_rate INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Create skin temperature table
        c.execute('''
            CREATE TABLE skin_temperature (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Create GSR table
        c.execute('''
            CREATE TABLE gsr (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')

        # Create Light table
        c.execute('''
            CREATE TABLE light (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')

        # Create PPG table
        c.execute('''
            CREATE TABLE ppg (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                value INTEGER NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')

        # Create Accelerometer table
        c.execute('''
            CREATE TABLE accelerometer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                x_value REAL NOT NULL,
                y_value REAL NOT NULL,
                z_value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')

        # Create Gyroscope table
        c.execute('''
            CREATE TABLE gyroscope (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                x_value REAL NOT NULL,
                y_value REAL NOT NULL,
                z_value REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
        print("Database created successfully")
    else:
        # Check if the new tables exist and create them if not
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='skin_temperature'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE skin_temperature (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            print("Created skin_temperature table")
        
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gsr'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE gsr (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            print("Created gsr table")

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='light'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE light (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            print("Created light table")

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ppg'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE ppg (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    value INTEGER NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            print("Created ppg table")

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accelerometer'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE accelerometer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    x_value REAL NOT NULL,
                    y_value REAL NOT NULL,
                    z_value REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            print("Created accelerometer table")

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gyroscope'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE gyroscope (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    x_value REAL NOT NULL,
                    y_value REAL NOT NULL,
                    z_value REAL NOT NULL,
                    timestamp TEXT NOT NULL
                )
            ''')
            print("Created gyroscope table")
            
        conn.commit()
        conn.close()
        print("Database ready")

# Initialize the database
init_db()

# Helper function to get device IDs
def get_device_ids():
    conn = sqlite3.connect('health_data.db')
    c = conn.cursor()
    c.execute("SELECT DISTINCT device_id FROM heartrates UNION SELECT DISTINCT device_id FROM skin_temperature UNION SELECT DISTINCT device_id FROM gsr UNION SELECT DISTINCT device_id FROM light")
    devices = [row[0] for row in c.fetchall()]
    conn.close()
    return devices

# Web interface routes
@app.route('/')
def home():
    devices = get_device_ids()
    return render_template('index.html', devices=devices)

@app.route('/device/<device_id>')
def device_data(device_id):
    return render_template('device.html', device_id=device_id)

@app.route('/api/devices')
def get_devices():
    devices = get_device_ids()
    return jsonify(devices)

# API routes for health data
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
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO heartrates (device_id, heart_rate, timestamp) VALUES (?, ?, ?)',
                  (device_id, heart_rate, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Heart rate recorded successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/skin_temperature', methods=['POST'])
def store_skin_temperature():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        value = data.get('value')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        
        # Validate data
        if value is None or not isinstance(value, int):
            return jsonify({'error': 'Invalid skin temperature value'}), 400
            
        # Store in database
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO skin_temperature (device_id, value, timestamp) VALUES (?, ?, ?)',
                  (device_id, value, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'Skin temperature recorded successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/gsr', methods=['POST'])
def store_gsr():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        value = data.get('value')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        
        # Validate data
        if value is None or not isinstance(value, int):
            return jsonify({'error': 'Invalid GSR value'}), 400
            
        # Store in database
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO gsr (device_id, value, timestamp) VALUES (?, ?, ?)',
                  (device_id, value, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'GSR recorded successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/light', methods=['POST'])
def store_light():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        value = data.get('value')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        
        # Validate data
        if value is None or not isinstance(value, int):
            return jsonify({'error': 'Invalid light value'}), 400
            
        # Store in database
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO light (device_id, value, timestamp) VALUES (?, ?, ?)',
                  (device_id, value, timestamp))
        conn.commit()
        conn.close()
        
        return jsonify({'message': 'light recorded successfully'}), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@app.route('/api/ppg', methods=['POST'])
def store_ppg():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        value = data.get('value')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())

        # Validate data
        if value is None or not isinstance(value, int):
            return jsonify({'error': 'Invalid PPG value'}), 400

        # Store in database
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO ppg (device_id, value, timestamp) VALUES (?, ?, ?)',
                  (device_id, value, timestamp))
        conn.commit()
        conn.close()

        return jsonify({'message': 'PPG recorded successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/accelerometer', methods=['POST'])
def store_accelerometer():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        x_value = data.get('x_value')
        y_value = data.get('y_value')
        z_value = data.get('z_value')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())

        # Store in database
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO accelerometer (device_id, x_value, y_value, z_value, timestamp) VALUES (?, ?, ?, ?, ?)',
                  (device_id, x_value, y_value, z_value, timestamp))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Accelerometer data recorded successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/gyroscope', methods=['POST'])
def store_gyroscope():
    try:
        # Get data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        x_value = data.get('x_value')
        y_value = data.get('y_value')
        z_value = data.get('z_value')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())

        # Store in database
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        c.execute('INSERT INTO gyroscope (device_id, x_value, y_value, z_value, timestamp) VALUES (?, ?, ?, ?, ?)',
                  (device_id, x_value, y_value, z_value, timestamp))
        conn.commit()
        conn.close()

        return jsonify({'message': 'Gyroscope data recorded successfully'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/heartrate', methods=['GET'])
def get_heartrates():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
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

@app.route('/api/skin_temperature', methods=['GET'])
def get_skin_temperature():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM skin_temperature'
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

@app.route('/api/gsr', methods=['GET'])
def get_gsr():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM gsr'
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
    
@app.route('/api/light', methods=['GET'])
def get_light():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM light'
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
    
@app.route('/api/ppg', methods=['GET'])
def get_ppg():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM ppg'
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
    
@app.route('/api/accelerometer', methods=['GET'])
def get_accelerometer():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM accelerometer'
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
    
@app.route('/api/gyroscope', methods=['GET'])
def get_gyroscope():
    try:
        # Get parameters
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 100)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM gyroscope'
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
    print("Starting Health Data Server...")
    app.run(host='192.168.0.98', port=5000, debug=True)