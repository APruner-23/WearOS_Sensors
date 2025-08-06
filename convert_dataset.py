import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import os

def load_accelerometer_data(db_path):
    """Load accelerometer data from SQLite database."""
    conn = sqlite3.connect(db_path)
    
    # Load accelerometer data, sorted by timestamp
    query = """
    SELECT id, x_value, y_value, z_value, timestamp 
    FROM accelerometer 
    ORDER BY timestamp
    """
    
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    print(f"Loaded {len(df)} accelerometer samples")
    print(f"Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    return df

def detect_continuous_periods(df, max_gap_seconds=5):
    """
    Detect continuous data collection periods by finding gaps larger than threshold.
    
    Args:
        df: DataFrame with accelerometer data
        max_gap_seconds: Maximum gap in seconds to consider data as continuous
    
    Returns:
        List of (start_idx, end_idx) tuples for continuous periods
    """
    
    # Calculate time differences between consecutive samples
    time_diffs = df['timestamp'].diff().dt.total_seconds()
    
    # Find gaps larger than threshold
    gap_indices = np.where(time_diffs > max_gap_seconds)[0]
    
    # Define continuous periods
    periods = []
    start_idx = 0
    
    for gap_idx in gap_indices:
        # Period ends at the sample before the gap
        end_idx = gap_idx - 1
        if end_idx > start_idx:
            periods.append((start_idx, end_idx))
        # Next period starts after the gap
        start_idx = gap_idx
    
    # Add the last period
    if start_idx < len(df) - 1:
        periods.append((start_idx, len(df) - 1))
    
    print(f"\nDetected {len(periods)} continuous periods:")
    for i, (start_idx, end_idx) in enumerate(periods):
        start_time = df.iloc[start_idx]['timestamp']
        end_time = df.iloc[end_idx]['timestamp']
        duration = (end_time - start_time).total_seconds()
        n_samples = end_idx - start_idx + 1
        freq = n_samples / duration if duration > 0 else 0
        print(f"  Period {i+1}: {start_time} to {end_time}")
        print(f"    Duration: {duration:.1f}s, Samples: {n_samples}, Freq: {freq:.1f} Hz")
    
    return periods

def create_windows_from_periods(df, periods, window_duration=10, target_freq=30):
    """
    Create sliding windows from continuous periods only.
    
    Args:
        df: DataFrame with accelerometer data
        periods: List of (start_idx, end_idx) for continuous periods
        window_duration: Duration of each window in seconds (default: 10)
        target_freq: Target frequency in Hz (default: 30)
    
    Returns:
        windows: numpy array of shape (n_windows, samples_per_window, 3)
        timestamps: numpy array of window start timestamps
        period_info: list of which period each window came from
    """
    
    target_samples = window_duration * target_freq  # 300 samples
    windows = []
    timestamps = []
    period_info = []
    
    for period_idx, (start_idx, end_idx) in enumerate(periods):
        period_data = df.iloc[start_idx:end_idx+1].copy()
        period_duration = (period_data['timestamp'].iloc[-1] - period_data['timestamp'].iloc[0]).total_seconds()
        
        if period_duration < window_duration:
            print(f"  Skipping period {period_idx+1}: too short ({period_duration:.1f}s)")
            continue
        
        # Calculate actual frequency for this period
        actual_freq = len(period_data) / period_duration
        print(f"  Processing period {period_idx+1}: {actual_freq:.1f} Hz")
        
        # Create windows within this continuous period
        period_windows, period_timestamps = create_windows_from_continuous_data(
            period_data, window_duration, target_freq
        )
        
        windows.extend(period_windows)
        timestamps.extend(period_timestamps)
        period_info.extend([period_idx] * len(period_windows))
        
        print(f"    Created {len(period_windows)} windows from period {period_idx+1}")
    
    if len(windows) == 0:
        raise ValueError("No valid windows could be created from any continuous period.")
    
    # Convert to numpy arrays
    windows = np.array(windows)  # Shape: (n_windows, target_samples, 3)
    timestamps = np.array(timestamps)
    period_info = np.array(period_info)
    
    print(f"\nTotal: Created {len(windows)} windows of shape {windows.shape}")
    
    return windows, timestamps, period_info

def create_windows_from_continuous_data(period_data, window_duration, target_freq):
    """
    Create windows from a single continuous period of data.
    """
    target_samples = window_duration * target_freq
    window_timedelta = timedelta(seconds=window_duration)
    
    windows = []
    timestamps = []
    
    start_time = period_data['timestamp'].iloc[0]
    end_time = period_data['timestamp'].iloc[-1]
    current_time = start_time
    
    while current_time + window_timedelta <= end_time:
        window_end_time = current_time + window_timedelta
        
        # Get samples within this time window
        window_mask = (period_data['timestamp'] >= current_time) & (period_data['timestamp'] < window_end_time)
        window_data = period_data[window_mask]
        
        if len(window_data) >= target_samples * 0.5:  # At least 50% of expected samples
            # Resample to target frequency
            window_samples = resample_to_target_frequency(window_data, target_samples)
            windows.append(window_samples)
            timestamps.append(current_time)
        
        # Move to next window (non-overlapping)
        current_time = window_end_time
    
    return windows, timestamps

def resample_to_target_frequency(window_data, target_samples):
    """
    Resample window data to target number of samples using interpolation.
    """
    if len(window_data) == target_samples:
        # Already the right size
        return window_data[['x_value', 'y_value', 'z_value']].values
    
    # Create time index for interpolation
    time_seconds = (window_data['timestamp'] - window_data['timestamp'].iloc[0]).dt.total_seconds()
    
    # Target time points (evenly spaced)
    window_duration = time_seconds.iloc[-1]
    target_times = np.linspace(0, window_duration, target_samples)
    
    # Interpolate each axis
    x_interp = np.interp(target_times, time_seconds, window_data['x_value'])
    y_interp = np.interp(target_times, time_seconds, window_data['y_value'])
    z_interp = np.interp(target_times, time_seconds, window_data['z_value'])
    
    # Stack into (target_samples, 3) array
    interpolated = np.column_stack([x_interp, y_interp, z_interp])
    
    return interpolated

def save_dataset(windows, timestamps, period_info, output_dir="dataset"):
    """Save the dataset and metadata to files."""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Save windows as .npy file (suitable for HARNet)
    windows_path = os.path.join(output_dir, "accelerometer_windows.npy")
    np.save(windows_path, windows)
    print(f"Saved accelerometer windows to {windows_path}")
    print(f"Windows shape: {windows.shape}")
    
    # Save timestamps as .npy file
    timestamps_path = os.path.join(output_dir, "window_timestamps.npy")
    np.save(timestamps_path, timestamps)
    print(f"Saved timestamps to {timestamps_path}")
    
    # Save period info
    period_info_path = os.path.join(output_dir, "window_period_info.npy")
    np.save(period_info_path, period_info)
    print(f"Saved period info to {period_info_path}")
    
    # Also save timestamps as readable text file for reference
    timestamps_txt_path = os.path.join(output_dir, "window_timestamps.txt")
    with open(timestamps_txt_path, 'w') as f:
        for i, (ts, period) in enumerate(zip(timestamps, period_info)):
            f.write(f"Window {i}: {ts} (Period {period})\n")
    print(f"Saved readable timestamps to {timestamps_txt_path}")
    
    # Save metadata
    metadata_path = os.path.join(output_dir, "dataset_info.txt")
    with open(metadata_path, 'w') as f:
        f.write(f"Dataset Information\n")
        f.write(f"==================\n")
        f.write(f"Number of windows: {len(windows)}\n")
        f.write(f"Window shape: {windows.shape}\n")
        f.write(f"Window duration: 10 seconds\n")
        f.write(f"Samples per window: 300\n")
        f.write(f"Target frequency: 30 Hz\n")
        f.write(f"Data shape per window: (300, 3) - [x, y, z] accelerometer values\n")
        f.write(f"First window timestamp: {timestamps[0]}\n")
        f.write(f"Last window timestamp: {timestamps[-1]}\n")
        f.write(f"Number of continuous periods used: {len(np.unique(period_info))}\n")
        f.write(f"\nWindows per period:\n")
        unique_periods, counts = np.unique(period_info, return_counts=True)
        for period, count in zip(unique_periods, counts):
            f.write(f"  Period {period}: {count} windows\n")
    print(f"Saved dataset info to {metadata_path}")

def main():
    # Configuration
    db_path = "health_data.db"  # Path to your database file
    output_dir = "harnet_dataset"
    max_gap_seconds = 5  # Maximum gap to consider data as continuous
    
    # Check if database file exists
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found!")
        print("Please make sure the file is in the same directory as this script.")
        return
    
    try:
        # Load data
        print("Loading accelerometer data from database...")
        df = load_accelerometer_data(db_path)
        
        # Detect continuous periods
        print("Detecting continuous data collection periods...")
        periods = detect_continuous_periods(df, max_gap_seconds)
        
        # Create windows from continuous periods only
        print("Creating 10-second windows from continuous periods...")
        windows, timestamps, period_info = create_windows_from_periods(df, periods)
        
        # Save dataset
        print("Saving dataset...")
        save_dataset(windows, timestamps, period_info, output_dir)
        
        print("\nDataset creation completed successfully!")
        print(f"Your HARNet-ready dataset is saved in the '{output_dir}' directory.")
        print(f"Load it in your HARNet model using: np.load('harnet_dataset/accelerometer_windows.npy')")
        
    except Exception as e:
        print(f"Error during processing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()