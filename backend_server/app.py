# app.py - Health Data Server with Batch Processing and Web Interface

# Library imports
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

        # Create batch_logs table to track batch processing
        c.execute('''
            CREATE TABLE batch_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT NOT NULL,
                batch_timestamp TEXT NOT NULL,
                heart_rate_count INTEGER DEFAULT 0,
                health_data_count INTEGER DEFAULT 0,
                motion_data_count INTEGER DEFAULT 0,
                total_records INTEGER DEFAULT 0,
                processing_time_ms INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
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

        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='batch_logs'")
        if not c.fetchone():
            c.execute('''
                CREATE TABLE batch_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    batch_timestamp TEXT NOT NULL,
                    heart_rate_count INTEGER DEFAULT 0,
                    health_data_count INTEGER DEFAULT 0,
                    motion_data_count INTEGER DEFAULT 0,
                    total_records INTEGER DEFAULT 0,
                    processing_time_ms INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            ''')
            print("Created batch_logs table")
            
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

# Batch processing endpoint
@app.route('/api/batch', methods=['POST'])
def store_batch_data():
    try:
        import time
        start_time = time.time()
        
        # Get batch data from request
        data = request.json
        device_id = data.get('device_id', 'unknown')
        batch_timestamp = data.get('batch_timestamp', datetime.datetime.now().isoformat())
        
        # Initialize counters
        heart_rate_count = 0
        health_data_count = 0
        motion_data_count = 0
        
        conn = sqlite3.connect('health_data.db')
        c = conn.cursor()
        
        # Begin transaction for atomic batch processing
        c.execute('BEGIN TRANSACTION')
        
        try:
            # Process heart rate data
            if 'heart_rate_data' in data and data['heart_rate_data']:
                heart_rate_batch = []
                for hr_reading in data['heart_rate_data']:
                    heart_rate_batch.append((
                        device_id,
                        hr_reading.get('heart_rate'),
                        hr_reading.get('timestamp')
                    ))
                
                c.executemany(
                    'INSERT INTO heartrates (device_id, heart_rate, timestamp) VALUES (?, ?, ?)',
                    heart_rate_batch
                )
                heart_rate_count = len(heart_rate_batch)
                print(f"Inserted {heart_rate_count} heart rate readings")

            # Process health data (skin temp, GSR, light, PPG)
            if 'health_data' in data and data['health_data']:
                # Group health data by type for batch insertion
                skin_temp_batch = []
                gsr_batch = []
                light_batch = []
                ppg_batch = []
                
                for health_reading in data['health_data']:
                    data_type = health_reading.get('data_type')
                    value = health_reading.get('value')
                    timestamp = health_reading.get('timestamp')
                    
                    if data_type == 'skin_temperature':
                        skin_temp_batch.append((device_id, value, timestamp))
                    elif data_type == 'gsr':
                        gsr_batch.append((device_id, value, timestamp))
                    elif data_type == 'light':
                        light_batch.append((device_id, value, timestamp))
                    elif data_type == 'ppg':
                        ppg_batch.append((device_id, value, timestamp))
                
                # Insert batched health data
                if skin_temp_batch:
                    c.executemany(
                        'INSERT INTO skin_temperature (device_id, value, timestamp) VALUES (?, ?, ?)',
                        skin_temp_batch
                    )
                    print(f"Inserted {len(skin_temp_batch)} skin temperature readings")
                
                if gsr_batch:
                    c.executemany(
                        'INSERT INTO gsr (device_id, value, timestamp) VALUES (?, ?, ?)',
                        gsr_batch
                    )
                    print(f"Inserted {len(gsr_batch)} GSR readings")
                
                if light_batch:
                    c.executemany(
                        'INSERT INTO light (device_id, value, timestamp) VALUES (?, ?, ?)',
                        light_batch
                    )
                    print(f"Inserted {len(light_batch)} light readings")
                
                if ppg_batch:
                    c.executemany(
                        'INSERT INTO ppg (device_id, value, timestamp) VALUES (?, ?, ?)',
                        ppg_batch
                    )
                    print(f"Inserted {len(ppg_batch)} PPG readings")
                
                health_data_count = len(skin_temp_batch) + len(gsr_batch) + len(light_batch) + len(ppg_batch)

            # Process motion data (accelerometer, gyroscope)
            if 'motion_data' in data and data['motion_data']:
                # Group motion data by type for batch insertion
                accelerometer_batch = []
                gyroscope_batch = []
                
                for motion_reading in data['motion_data']:
                    data_type = motion_reading.get('data_type')
                    x_value = motion_reading.get('x_value')
                    y_value = motion_reading.get('y_value')
                    z_value = motion_reading.get('z_value')
                    timestamp = motion_reading.get('timestamp')
                    
                    if data_type == 'accelerometer':
                        accelerometer_batch.append((device_id, x_value, y_value, z_value, timestamp))
                    elif data_type == 'gyroscope':
                        gyroscope_batch.append((device_id, x_value, y_value, z_value, timestamp))
                
                # Insert batched motion data
                if accelerometer_batch:
                    c.executemany(
                        'INSERT INTO accelerometer (device_id, x_value, y_value, z_value, timestamp) VALUES (?, ?, ?, ?, ?)',
                        accelerometer_batch
                    )
                    print(f"Inserted {len(accelerometer_batch)} accelerometer readings")
                
                if gyroscope_batch:
                    c.executemany(
                        'INSERT INTO gyroscope (device_id, x_value, y_value, z_value, timestamp) VALUES (?, ?, ?, ?, ?)',
                        gyroscope_batch
                    )
                    print(f"Inserted {len(gyroscope_batch)} gyroscope readings")
                
                motion_data_count = len(accelerometer_batch) + len(gyroscope_batch)

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)
            total_records = heart_rate_count + health_data_count + motion_data_count
            
            # Log batch processing info
            c.execute('''
                INSERT INTO batch_logs 
                (device_id, batch_timestamp, heart_rate_count, health_data_count, motion_data_count, 
                 total_records, processing_time_ms, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                device_id, batch_timestamp, heart_rate_count, health_data_count, 
                motion_data_count, total_records, processing_time_ms, 
                datetime.datetime.now().isoformat()
            ))
            
            # Commit transaction
            conn.commit()
            
            response_data = {
                'message': 'Batch data processed successfully',
                'summary': {
                    'device_id': device_id,
                    'total_records': total_records,
                    'heart_rate_count': heart_rate_count,
                    'health_data_count': health_data_count,
                    'motion_data_count': motion_data_count,
                    'processing_time_ms': processing_time_ms
                }
            }
            
            print(f"Batch processed: {total_records} total records in {processing_time_ms}ms")
            return jsonify(response_data), 201
            
        except Exception as e:
            # Rollback transaction on error
            conn.rollback()
            raise e
            
    except Exception as e:
        print(f"Error processing batch: {str(e)}")
        return jsonify({'error': f'Batch processing failed: {str(e)}'}), 500
    
    finally:
        if 'conn' in locals():
            conn.close()

# Get batch processing statistics
@app.route('/api/batch/stats', methods=['GET'])
def get_batch_stats():
    try:
        device_id = request.args.get('device_id', None)
        limit = request.args.get('limit', 50)
        
        conn = sqlite3.connect('health_data.db')
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        
        query = 'SELECT * FROM batch_logs'
        params = []
        
        if device_id:
            query += ' WHERE device_id = ?'
            params.append(device_id)
            
        query += ' ORDER BY created_at DESC LIMIT ?'
        params.append(limit)
        
        c.execute(query, params)
        results = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Web interface routes (those need to be updated, OLD UI)
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

# EXISTING API routes for health data (kept for backward compatibility)
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
    print("  GET /api/batch/stats - for batch processing statistics")
    app.run(host='192.168.0.98', port=5000, debug=True)