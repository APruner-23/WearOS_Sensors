import numpy as np
import pandas as pd
from datetime import datetime, time
import os

def load_existing_dataset(dataset_dir="harnet_dataset"):
    """Load the previously created dataset and timestamps."""
    
    windows_path = os.path.join(dataset_dir, "accelerometer_windows.npy")
    timestamps_path = os.path.join(dataset_dir, "window_timestamps.npy")
    period_info_path = os.path.join(dataset_dir, "window_period_info.npy")
    
    if not os.path.exists(windows_path) or not os.path.exists(timestamps_path):
        raise FileNotFoundError(f"Dataset files not found in {dataset_dir}")
    
    windows = np.load(windows_path)
    timestamps = np.load(timestamps_path, allow_pickle=True)
    
    # Load period info if available
    period_info = None
    if os.path.exists(period_info_path):
        period_info = np.load(period_info_path)
    
    # Convert timestamps to datetime objects if they're not already
    if isinstance(timestamps[0], str):
        timestamps = pd.to_datetime(timestamps)
    elif not isinstance(timestamps[0], (pd.Timestamp, datetime)):
        timestamps = pd.to_datetime(timestamps)
    
    print(f"Loaded dataset with {len(windows)} windows")
    print(f"Window shape: {windows.shape}")
    print(f"Time range: {timestamps[0]} to {timestamps[-1]}")
    
    if period_info is not None:
        unique_periods = np.unique(period_info)
        print(f"Windows from {len(unique_periods)} continuous periods")
        for period in unique_periods:
            count = np.sum(period_info == period)
            period_timestamps = timestamps[period_info == period]
            print(f"  Period {period}: {count} windows ({period_timestamps[0]} to {period_timestamps[-1]})")
    
    return windows, timestamps, period_info

def create_labeling_rules():
    """Define the labeling rules based on dates and times."""
    
    # Class mapping
    idx2class = {0: 'light', 1: 'moderate-vigorous', 2: 'sedentary', 3: 'sleep'}
    class2idx = {v: k for k, v in idx2class.items()}
    
    # Define labeling rules: (date, start_time, end_time, label)
    labeling_rules = [
        # Day 25/07/2025
        ('2025-07-25', '14:55:00', '16:15:00', 'sedentary'),
        
        # Day 01/08/2025
        ('2025-08-01', '16:16:00', '16:57:00', 'light'),
        
        # Day 04/08/2025
        ('2025-08-04', '16:35:00', '17:29:59', 'sedentary'),
        ('2025-08-04', '17:30:00', '18:15:00', 'sleep'),
        ('2025-08-04', '18:20:00', '18:31:00', 'moderate-vigorous'),
        ('2025-08-04', '20:58:00', '22:06:00', 'sedentary'),
    ]
    
    # Convert to datetime ranges
    datetime_rules = []
    for date_str, start_time, end_time, label in labeling_rules:
        start_dt = pd.to_datetime(f"{date_str} {start_time}")
        end_dt = pd.to_datetime(f"{date_str} {end_time}")
        datetime_rules.append((start_dt, end_dt, label, class2idx[label]))
    
    return datetime_rules, idx2class, class2idx

def assign_labels(timestamps, datetime_rules, period_info=None):
    """Assign labels to windows based on their timestamps."""
    
    labels = []
    labeled_count = 0
    
    print("\nLabeling windows...")
    print("=" * 60)
    
    # Show labeling rules
    print("Labeling rules applied:")
    for start_dt, end_dt, label_name, label_idx in datetime_rules:
        print(f"  {start_dt} to {end_dt}: {label_name} (idx: {label_idx})")
    print()
    
    for i, ts in enumerate(timestamps):
        label = None
        label_idx = None
        
        # Check each rule to see if this timestamp falls within a labeled period
        for start_dt, end_dt, label_name, label_index in datetime_rules:
            if start_dt <= ts <= end_dt:
                label = label_name
                label_idx = label_index
                labeled_count += 1
                break
        
        labels.append(label_idx)  # None for unlabeled windows
        
        # Print some examples for each label type
        if label is not None and labeled_count <= 10:
            period_str = f" (Period {period_info[i]})" if period_info is not None else ""
            print(f"Window {i}: {ts}{period_str} -> {label} (idx: {label_idx})")
    
    print(f"\nLabeled {labeled_count} out of {len(timestamps)} windows ({labeled_count/len(timestamps)*100:.1f}%)")
    print(f"Unlabeled windows: {len(timestamps) - labeled_count}")
    
    return np.array(labels)

def analyze_labels(labels, timestamps, idx2class, period_info=None):
    """Analyze the distribution of labels."""
    
    print("\n" + "=" * 60)
    print("LABEL ANALYSIS")
    print("=" * 60)
    
    # Count each label
    labeled_mask = labels != None
    if np.any(labeled_mask):
        unique_labels, counts = np.unique(labels[labeled_mask], return_counts=True)
        
        print("Label distribution:")
        total_labeled = np.sum(labeled_mask)
        for label_idx, count in zip(unique_labels, counts):
            if label_idx is not None:
                percentage = count / total_labeled * 100
                print(f"  {idx2class[label_idx]} (idx {label_idx}): {count} windows ({percentage:.1f}%)")
    
    unlabeled_count = np.sum(labels == None)
    unlabeled_percentage = unlabeled_count / len(labels) * 100
    print(f"  Unlabeled: {unlabeled_count} windows ({unlabeled_percentage:.1f}%)")
    
    # Show time distribution
    if np.any(labeled_mask):
        print("\nTemporal distribution of labeled data:")
        labeled_timestamps = timestamps[labeled_mask]
        labeled_labels = labels[labeled_mask]
        
        print(f"  Labeled data spans: {labeled_timestamps[0]} to {labeled_timestamps[-1]}")
        
        # Group by date
        labeled_df = pd.DataFrame({
            'timestamp': labeled_timestamps,
            'label': labeled_labels
        })
        labeled_df['date'] = labeled_df['timestamp'].dt.date
        
        print("\nWindows per date:")
        for date in sorted(labeled_df['date'].unique()):
            date_data = labeled_df[labeled_df['date'] == date]
            print(f"  {date}: {len(date_data)} windows")
            for label_idx in sorted(date_data['label'].unique()):
                if label_idx is not None:
                    count = np.sum(date_data['label'] == label_idx)
                    print(f"    - {idx2class[label_idx]}: {count} windows")
    
    # Analyze by period if available
    if period_info is not None:
        print("\nLabeled windows by period:")
        unique_periods = np.unique(period_info)
        for period in unique_periods:
            period_mask = period_info == period
            period_labels = labels[period_mask]
            period_timestamps = timestamps[period_mask]
            
            labeled_in_period = np.sum(period_labels != None)
            total_in_period = len(period_labels)
            
            print(f"  Period {period}: {labeled_in_period}/{total_in_period} windows labeled")
            print(f"    Time range: {period_timestamps[0]} to {period_timestamps[-1]}")
            
            if labeled_in_period > 0:
                period_labeled_mask = period_labels != None
                unique_period_labels, period_counts = np.unique(period_labels[period_labeled_mask], return_counts=True)
                for label_idx, count in zip(unique_period_labels, period_counts):
                    if label_idx is not None:
                        print(f"      - {idx2class[label_idx]}: {count} windows")

def check_data_quality(windows, labels, timestamps):
    """Check quality and distribution of the final dataset."""
    
    print("\n" + "=" * 60)
    print("DATA QUALITY CHECK")
    print("=" * 60)
    
    labeled_mask = labels != None
    labeled_windows = windows[labeled_mask]
    labeled_labels = labels[labeled_mask]
    
    if len(labeled_windows) == 0:
        print("WARNING: No labeled data found!")
        return
    
    print(f"Final dataset size: {len(labeled_windows)} windows")
    print(f"Window shape: {labeled_windows.shape}")
    
    # Check for NaN or infinite values
    nan_count = np.sum(np.isnan(labeled_windows))
    inf_count = np.sum(np.isinf(labeled_windows))
    
    if nan_count > 0:
        print(f"WARNING: Found {nan_count} NaN values in the data")
    if inf_count > 0:
        print(f"WARNING: Found {inf_count} infinite values in the data")
    
    if nan_count == 0 and inf_count == 0:
        print("✓ No NaN or infinite values found")
    
    # Check data ranges
    print(f"\nData value ranges:")
    for axis, name in enumerate(['X', 'Y', 'Z']):
        axis_data = labeled_windows[:, :, axis]
        print(f"  {name}-axis: {axis_data.min():.3f} to {axis_data.max():.3f}")
    
    # Check class balance
    print(f"\nClass balance check:")
    unique_labels, counts = np.unique(labeled_labels, return_counts=True)
    min_count = np.min(counts)
    max_count = np.max(counts)
    balance_ratio = min_count / max_count
    
    print(f"  Most common class: {max_count} samples")
    print(f"  Least common class: {min_count} samples")
    print(f"  Balance ratio: {balance_ratio:.2f} (1.0 = perfectly balanced)")
    
    if balance_ratio < 0.1:
        print("  ⚠️  WARNING: Highly imbalanced dataset")
    elif balance_ratio < 0.3:
        print("  ⚠️  Moderately imbalanced dataset")
    else:
        print("  ✓ Reasonably balanced dataset")

def save_labeled_dataset(windows, timestamps, labels, idx2class, period_info=None, output_dir="harnet_dataset"):
    """Save the labeled dataset."""
    
    # Filter out unlabeled data
    labeled_mask = labels != None
    labeled_windows = windows[labeled_mask]
    labeled_timestamps = timestamps[labeled_mask]
    labeled_labels = labels[labeled_mask]
    labeled_period_info = period_info[labeled_mask] if period_info is not None else None
    
    print(f"\nSaving labeled dataset...")
    print(f"Original dataset: {len(windows)} windows")
    print(f"Labeled dataset: {len(labeled_windows)} windows")
    
    # Save labeled dataset
    labeled_windows_path = os.path.join(output_dir, "labeled_accelerometer_windows.npy")
    np.save(labeled_windows_path, labeled_windows)
    print(f"Saved labeled windows to {labeled_windows_path}")
    
    # Save labels
    labels_path = os.path.join(output_dir, "labels.npy")
    np.save(labels_path, labeled_labels)
    print(f"Saved labels to {labels_path}")
    
    # Save timestamps for labeled data
    labeled_timestamps_path = os.path.join(output_dir, "labeled_timestamps.npy")
    np.save(labeled_timestamps_path, labeled_timestamps)
    print(f"Saved labeled timestamps to {labeled_timestamps_path}")
    
    # Save period info for labeled data if available
    if labeled_period_info is not None:
        labeled_period_info_path = os.path.join(output_dir, "labeled_period_info.npy")
        np.save(labeled_period_info_path, labeled_period_info)
        print(f"Saved labeled period info to {labeled_period_info_path}")
    
    # Save class mapping
    class_mapping_path = os.path.join(output_dir, "class_mapping.npy")
    np.save(class_mapping_path, idx2class)
    print(f"Saved class mapping to {class_mapping_path}")
    
    # Also save full dataset with all labels (including None for unlabeled)
    full_labels_path = os.path.join(output_dir, "all_labels.npy")
    np.save(full_labels_path, labels)
    print(f"Saved all labels (including unlabeled) to {full_labels_path}")
    
    # Create comprehensive summary file
    summary_path = os.path.join(output_dir, "labeled_dataset_summary.txt")
    with open(summary_path, 'w') as f:
        f.write("Labeled Dataset Summary\n")
        f.write("======================\n\n")
        f.write(f"Dataset Creation Date: {datetime.now()}\n\n")
        
        f.write(f"Total windows in original dataset: {len(windows)}\n")
        f.write(f"Labeled windows: {len(labeled_windows)}\n")
        f.write(f"Unlabeled windows: {len(windows) - len(labeled_windows)}\n")
        f.write(f"Labeling percentage: {len(labeled_windows)/len(windows)*100:.1f}%\n\n")
        
        f.write("Class Mapping:\n")
        for idx, class_name in idx2class.items():
            f.write(f"  {idx}: {class_name}\n")
        f.write("\n")
        
        f.write("Label Distribution:\n")
        unique_labels, counts = np.unique(labeled_labels, return_counts=True)
        for label_idx, count in zip(unique_labels, counts):
            percentage = count / len(labeled_labels) * 100
            f.write(f"  {idx2class[label_idx]} (idx {label_idx}): {count} windows ({percentage:.1f}%)\n")
        f.write("\n")
        
        f.write("Files created:\n")
        f.write("  - labeled_accelerometer_windows.npy: (n_labeled_windows, 300, 3) - HARNet input\n")
        f.write("  - labels.npy: (n_labeled_windows,) - integer labels for HARNet\n")
        f.write("  - labeled_timestamps.npy: timestamps for labeled windows\n")
        f.write("  - class_mapping.npy: idx2class dictionary\n")
        f.write("  - all_labels.npy: labels for all windows (None for unlabeled)\n")
        if labeled_period_info is not None:
            f.write("  - labeled_period_info.npy: period information for labeled windows\n")
        f.write("\n")
        
        f.write("Usage:\n")
        f.write("  X = np.load('labeled_accelerometer_windows.npy')\n")
        f.write("  y = np.load('labels.npy')\n")
        f.write("  # X.shape: (n_samples, 300, 3)\n")
        f.write("  # y.shape: (n_samples,)\n")
        
    print(f"Saved comprehensive summary to {summary_path}")

def main():
    dataset_dir = "harnet_dataset"
    
    try:
        # Load existing dataset
        print("Loading existing dataset...")
        windows, timestamps, period_info = load_existing_dataset(dataset_dir)
        
        # Create labeling rules
        print("Creating labeling rules...")
        datetime_rules, idx2class, class2idx = create_labeling_rules()
        
        # Assign labels
        labels = assign_labels(timestamps, datetime_rules, period_info)
        
        # Analyze labels
        analyze_labels(labels, timestamps, idx2class, period_info)
        
        # Check data quality
        check_data_quality(windows, labels, timestamps)
        
        # Save labeled dataset
        save_labeled_dataset(windows, timestamps, labels, idx2class, period_info, dataset_dir)
        
        print("\n" + "=" * 60)
        print("LABELING COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("Your labeled dataset is ready for HARNet training!")
        print("\nKey files for training:")
        print("  📊 labeled_accelerometer_windows.npy: Input data (n_samples, 300, 3)")
        print("  🏷️  labels.npy: Target labels (n_samples,)")
        print("  📋 class_mapping.npy: Label meanings")
        print("  📝 labeled_dataset_summary.txt: Detailed information")
        
        # Final recommendations
        labeled_count = np.sum(labels != None)
        if labeled_count < 100:
            print("\n⚠️  WARNING: Very small dataset. Consider:")
            print("   - Data augmentation techniques")
            print("   - Cross-validation instead of train/test split")
        elif labeled_count < 1000:
            print("\n💡 RECOMMENDATION: Small dataset. Consider:")
            print("   - Using pre-trained models")
            print("   - Data augmentation")
        
    except Exception as e:
        print(f"Error during labeling: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()