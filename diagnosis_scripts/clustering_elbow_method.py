#!/usr/bin/env python3

'''
USAGE
    clustering_elbow_method.py [OPTION]

DESCRIPTION
    Implement the elbow method to determine the optimal clustering threshold
    based on inertia values calculated from clustering CSV files. This script
    analyzes multiple clustering results with different thresholds and identifies
    the optimal threshold using the elbow point detection method.

OPTIONS
    -i, --input=DIR
        Directory containing clustering CSV files with naming pattern 
        'clustering_*.csv' where * represents the threshold value.
        
    -o, --output=FILE
        Output path for the elbow plot image (PNG format).
        
    -p, --prefix=STR
        Prefix for plot title. Default = "Dataset"
        
    --help
        Display this message

'''

import getopt, sys, csv, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import pairwise_distances
from kneed import KneeLocator

def get_word_tokenize_pattern(min_len=1):
    '''
    Returns a regular expression pattern matching alphanumeric tokens 
    of a minimum length. Same as used in mfnb.utils module.
    '''
    min_char = "".join( "\w" for i in range(min_len-1) )
    return fr'\b{min_char}\w+\b'

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "i:o:p:", 
                                       ["input=", "output=", "prefix=", "help"])
        except getopt.GetoptError as err:
            sys.stderr.write(f"Error: {err}\n")
            sys.exit(1)
        
        for opt, arg in opts:
            if opt in ("-i", "--input"):
                self["input"] = arg
            elif opt in ("-o", "--output"):
                self["output"] = arg
            elif opt in ("-p", "--prefix"):
                self["prefix"] = arg
            elif opt == "--help":
                sys.stderr.write(__doc__)
                sys.exit(0)
        
        # check required arguments
        if not self["input"]:
            sys.stderr.write("Error: Input directory required (-i/--input)\n")
            sys.exit(1)
        if not self["output"]:
            sys.stderr.write("Error: Output file required (-o/--output)\n")
            sys.exit(1)
        
        # store remaining arguments
        self["files"] = args

    def set_default(self):
        self["input"] = None
        self["output"] = None
        self["prefix"] = "Dataset"
        self["files"] = []

# Function to detect the delimiter used in the CSV file
def detect_delimiter(file_path: str) -> str:
    try:
        with open(file_path, 'r') as file:
            sample = file.read(1024)
            if not sample:
                raise ValueError("Empty file")
            sniffer = csv.Sniffer()
            return sniffer.sniff(sample).delimiter
    except Exception:
        sys.stderr.write(f"Warning: Could not determine delimiter for {file_path}, using ',' by default.\n")
        return ','  # Default to comma if detection fails

# Function to calculate inertia
def calculate_inertia(X, labels) -> float:
    """Calculate the inertia (within-cluster sum of squares) for the given data and labels."""
    inertia = 0
    unique_labels = np.unique(labels)

    for label in unique_labels:
        cluster_points = X[labels == label]  # Work with sparse matrix directly
        if cluster_points.shape[0] > 0:
            center = np.mean(cluster_points, axis=0).A[0]  # Get center as a dense array
            inertia += np.sum(pairwise_distances(cluster_points.toarray(), center.reshape(1, -1), metric='euclidean') ** 2)

    return inertia

# Function to load and validate the dataset
def load_and_validate_dataset(file_path: str) -> pd.DataFrame:
    """Load a CSV file and validate its structure."""
    if not os.path.exists(file_path):
        sys.stderr.write(f"Error: File {file_path} not found.\n")
        return None
    
    delimiter = detect_delimiter(file_path)
    
    try:
        df = pd.read_csv(file_path, sep=delimiter)
    except Exception as e:
        sys.stderr.write(f"Error loading file {file_path}: {e}\n")
        return None
    
    # Handle different column naming conventions
    df = df.rename(columns={
        'Transcript': 'Transcript',
        'label.v': 'Transcript',
        'label_v': 'Transcript',
        'Cluster_ID': 'Cluster_ID',
        'group.ID': 'Cluster_ID',
        'group_ID': 'Cluster_ID'
    })
    
    required_columns = ['Transcript', 'Cluster_ID']
    
    if not all(column in df.columns for column in required_columns):
        sys.stderr.write(f"Error: File {file_path} is missing required columns. Found columns: {df.columns.tolist()}\n")
        sys.stderr.write(f"Expected: Transcript/label.v/label_v and Cluster_ID/group.ID/group_ID\n")
        return None
    
    # Fill missing values in 'Transcript' to avoid dropping data
    df['Transcript'] = df['Transcript'].fillna('')

    return df

# Function to find the elbow point using kneed package (same as mfnb.utils)
def find_elbow_kneed(thresholds, inertias):
    """Find the elbow point using the kneed package, same approach as mfnb.utils."""
    # Convert thresholds to indices for kneed
    x_values = list(range(len(thresholds)))
    
    # Use KneeLocator assuming decreasing inertia values forming a convex curve
    kl = KneeLocator(x_values, inertias, curve="convex", direction="decreasing")
    
    if kl.elbow is None:
        # Fallback to manual method if kneed fails
        return find_elbow_manual(thresholds, inertias)
    
    return thresholds[kl.elbow]

# Function to find the elbow point manually (fallback method)
def find_elbow_manual(thresholds, inertias):
    """Fallback elbow detection using maximum distance from line method."""
    # Convert thresholds to float for calculation
    x = np.array([float(t) for t in thresholds])
    y = np.array(inertias)
    # Line from first to last point
    line_vec = np.array([x[-1] - x[0], y[-1] - y[0]])
    line_vec_norm = line_vec / np.sqrt(np.sum(line_vec**2))
    distances = []
    for i in range(len(x)):
        point_vec = np.array([x[i] - x[0], y[i] - y[0]])
        proj_len = np.dot(point_vec, line_vec_norm)
        proj_point = np.array([x[0], y[0]]) + proj_len * line_vec_norm
        dist = np.linalg.norm(point_vec - (proj_point - np.array([x[0], y[0]])))
        distances.append(dist)
    elbow_idx = np.argmax(distances)
    return thresholds[elbow_idx]

def main():
    """Main function to execute the elbow method for clustering threshold selection."""
    
    # parse command line options
    options = Options(sys.argv)
    
    input_dir = options["input"]
    output_path = options["output"]
    prefix = options["prefix"]
    
    # Find all clustering CSVs in the input directory
    file_paths = {}
    try:
        for fname in os.listdir(input_dir):
            if fname.startswith("clustering_") and fname.endswith(".csv"):
                key = fname.split("_")[-1].replace(".csv", "")
                file_paths[key] = os.path.join(input_dir, fname)
    except Exception as e:
        sys.stderr.write(f"Error reading directory {input_dir}: {e}\n")
        return 1
        
    if not file_paths:
        sys.stderr.write("No clustering CSV files found in the input directory.\n")
        return 1

    # Load datasets sequentially
    datasets = {}
    for key, file_path in file_paths.items():
        df = load_and_validate_dataset(file_path)
        if df is not None:
            datasets[key] = df

    if not datasets:
        sys.stderr.write("No valid datasets loaded.\n")
        return 1

    # Get the token pattern for minimum 3 character words (common default)
    token_pattern = get_word_tokenize_pattern(min_len=3)
    vectorizer = TfidfVectorizer(token_pattern=token_pattern, strip_accents="unicode")
    
    sample_size = None  # Use all data for maximum accuracy with large datasets
    inertia_values = {}

    for key, df in sorted(datasets.items(), key=lambda x: float(x[0])):
        sys.stderr.write(f"Processing dataset for threshold {key}...\n")
        X = vectorizer.fit_transform(df['Transcript'].astype(str))
        
        # Only sample if dataset is very large and sample_size is set
        if sample_size and X.shape[0] > sample_size:
            sample_indices = np.random.choice(X.shape[0], sample_size, replace=False)
            X_sampled = X[sample_indices]
            labels_sampled = df['Cluster_ID'].values[sample_indices]
            sys.stderr.write(f"Sampled {sample_size} from {X.shape[0]} labels\n")
        else:
            X_sampled = X
            labels_sampled = df['Cluster_ID'].values
            sys.stderr.write(f"Using all {X.shape[0]} labels\n")
            
        inertia = calculate_inertia(X_sampled, labels_sampled)
        inertia_values[key] = inertia

    thresholds = list(sorted(inertia_values.keys(), key=float))
    inertias = [inertia_values[t] for t in thresholds]

    # Find elbow using kneed package (same approach as mfnb.utils)
    elbow_threshold = find_elbow_kneed(thresholds, inertias)
    sys.stderr.write(f"Automatically detected elbow threshold: {elbow_threshold}\n")

    # Plot the elbow graph
    try:
        plt.figure(figsize=(8, 6))
        plt.plot(thresholds, inertias, marker='o', linestyle='-', color='b', label='Inertia')
        plt.scatter(elbow_threshold, inertia_values[elbow_threshold], color='r', s=100, zorder=5, label=f'Elbow point: {elbow_threshold}')
        plt.title(f'Elbow Method for Optimal Clusters in {prefix}', fontsize=14)
        plt.xlabel('Similarity Thresholds', fontsize=12)
        plt.ylabel('Inertia (Within-Cluster Sum of Squares)', fontsize=12)
        plt.grid(True)
        plt.legend()
        plt.savefig(output_path, dpi=300)
        plt.show()
        sys.stderr.write(f"Elbow plot saved to: {output_path}\n")
        sys.stderr.write(f"The optimal threshold based on the elbow method is: {elbow_threshold}\n")
    except Exception as e:
        sys.stderr.write(f"Error creating plot: {e}\n")
        return 1
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
