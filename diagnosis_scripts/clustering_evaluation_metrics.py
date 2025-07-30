#!/usr/bin/env python3

'''
USAGE
    clustering_evaluation_metrics.py [OPTION]

DESCRIPTION
    Evaluates clustering metrics from CSV clustering output files and generates
    visualization of the results. This script calculates multiple clustering
    quality metrics (Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index)
    across different threshold values and creates comparative heatmaps for analysis.

OPTIONS
    -i, --input=DIR
        Directory containing clustering CSV files with naming pattern 
        'clustering_*.csv' where * represents the threshold value.
        
    -t, --thresholds=LIST
        Comma-separated list of thresholds to evaluate (e.g., "0.3,0.4,0.5").
        
    -o, --output=FILE
        Output path for the metrics visualization plot (PNG format).
        
    -p, --prefix=STR
        Prefix for plot title. Default = "Dataset"
        
    --help
        Display this message

'''

import getopt, sys, csv, os
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.feature_extraction.text import TfidfVectorizer

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
                                       "i:t:o:p:", 
                                       ["input=", "thresholds=", "output=", "prefix=", "help"])
        except getopt.GetoptError as err:
            sys.stderr.write(f"Error: {err}\n")
            sys.exit(1)
        
        for opt, arg in opts:
            if opt in ("-i", "--input"):
                self["input"] = arg
            elif opt in ("-t", "--thresholds"):
                # Parse comma-separated thresholds
                self["thresholds"] = [t.strip() for t in arg.split(",")]
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
        if not self["thresholds"]:
            sys.stderr.write("Error: Thresholds list required (-t/--thresholds)\n")
            sys.exit(1)
        if not self["output"]:
            sys.stderr.write("Error: Output file required (-o/--output)\n")
            sys.exit(1)
        
        # store remaining arguments
        self["files"] = args

    def set_default(self):
        self["input"] = None
        self["thresholds"] = []
        self["output"] = None
        self["prefix"] = "Dataset"
        self["files"] = []

def detect_delimiter(file_path: str) -> str:
    '''
    Detect the delimiter used in the CSV file. Same function as other scripts.
    '''
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

def load_and_validate_dataset(file_path: str) -> dict:
    '''
    Load a CSV file and validate its structure. Returns dict instead of pandas DataFrame.
    '''
    if not os.path.exists(file_path):
        sys.stderr.write(f"Error: File {file_path} not found.\n")
        return None
    
    delimiter = detect_delimiter(file_path)
    
    try:
        data = {'Transcript': [], 'Cluster_ID': []}
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Handle different column naming conventions
            transcript_col = None
            cluster_col = None
            
            # Check for various transcript column names
            for col in reader.fieldnames:
                if col in ['Transcript', 'label.v', 'label_v']:
                    transcript_col = col
                    break
            
            # Check for various cluster column names  
            for col in reader.fieldnames:
                if col in ['Cluster_ID', 'group.ID', 'group_ID']:
                    cluster_col = col
                    break
            
            # Check if required columns exist
            if transcript_col is None or cluster_col is None:
                sys.stderr.write(f"Error: File {file_path} is missing required columns. Found columns: {reader.fieldnames}\n")
                sys.stderr.write(f"Expected: Transcript/label.v/label_v and Cluster_ID/group.ID/group_ID\n")
                return None
            
            for row in reader:
                # Fill missing values in 'Transcript' to avoid dropping data
                transcript = row.get(transcript_col, '').strip()
                cluster_id = row.get(cluster_col, '').strip()
                
                if transcript and cluster_id:  # Only add rows with both values
                    data['Transcript'].append(transcript)
                    data['Cluster_ID'].append(cluster_id)
        
        if not data['Transcript']:
            sys.stderr.write(f"Warning: No valid data found in {file_path}\n")
            return None
            
        return data
        
    except Exception as e:
        sys.stderr.write(f"Error loading file {file_path}: {e}\n")
        return None

def calculate_clustering_metrics(features, labels):
    '''
    Calculate clustering quality metrics.
    '''
    try:
        # Use the same tokenization approach as other scripts in mfnb.utils module
        token_pattern = get_word_tokenize_pattern(min_len=3)
        vectorizer = TfidfVectorizer(token_pattern=token_pattern, strip_accents="unicode")
        
        X_encoded = vectorizer.fit_transform(features)
        X_dense = X_encoded.toarray()
        
        # Convert labels to numeric array
        unique_labels = list(set(labels))
        label_map = {label: idx for idx, label in enumerate(unique_labels)}
        numeric_labels = np.array([label_map[label] for label in labels])
        
        if X_dense.shape[0] > 1 and len(unique_labels) > 1:
            # Compute clustering metrics
            silhouette = silhouette_score(X_dense, numeric_labels)
            davies_bouldin = davies_bouldin_score(X_dense, numeric_labels)
            calinski_harabasz = calinski_harabasz_score(X_dense, numeric_labels)
            return silhouette, davies_bouldin, calinski_harabasz
        else:
            return None, None, None
            
    except Exception as e:
        sys.stderr.write(f"Error calculating metrics: {e}\n")
        return None, None, None

def create_metrics_visualization(metrics_data, output_path, prefix):
    '''
    Create visualization plots for clustering metrics and save as PNG.
    '''
    try:
        # Extract data for plotting
        thresholds = list(metrics_data['thresholds'].keys())
        if not thresholds:
            sys.stderr.write("No valid data to plot\n")
            return False
        
        # Sort thresholds numerically
        thresholds.sort(key=float)
        
        silhouette_scores = [metrics_data['thresholds'][t]['silhouette_score'] for t in thresholds]
        davies_bouldin_scores = [metrics_data['thresholds'][t]['davies_bouldin_index'] for t in thresholds]
        calinski_harabasz_scores = [metrics_data['thresholds'][t]['calinski_harabasz_index'] for t in thresholds]
        
        # Create subplots
        fig, axes = plt.subplots(nrows=3, figsize=(12, 15))
        
        # Create heatmaps for each metric
        # Silhouette Score (higher is better)
        sns.heatmap([[score] for score in silhouette_scores], 
                   annot=True, fmt=".3f", cmap='Blues', 
                   yticklabels=thresholds, xticklabels=['Silhouette Score'],
                   ax=axes[0], cbar_kws={'label': 'Score'})
        axes[0].set_title(f'Silhouette Score Across Thresholds - {prefix}', fontsize=14)
        axes[0].set_ylabel('Threshold Values', fontsize=12)
        
        # Davies-Bouldin Index (lower is better)
        sns.heatmap([[score] for score in davies_bouldin_scores], 
                   annot=True, fmt=".3f", cmap='Greens', 
                   yticklabels=thresholds, xticklabels=['Davies-Bouldin Index'],
                   ax=axes[1], cbar_kws={'label': 'Index'})
        axes[1].set_title(f'Davies-Bouldin Index Across Thresholds - {prefix}', fontsize=14)
        axes[1].set_ylabel('Threshold Values', fontsize=12)
        
        # Calinski-Harabasz Index (higher is better)
        sns.heatmap([[score] for score in calinski_harabasz_scores], 
                   annot=True, fmt=".1f", cmap='Reds', 
                   yticklabels=thresholds, xticklabels=['Calinski-Harabasz Index'],
                   ax=axes[2], cbar_kws={'label': 'Index'})
        axes[2].set_title(f'Calinski-Harabasz Index Across Thresholds - {prefix}', fontsize=14)
        axes[2].set_ylabel('Threshold Values', fontsize=12)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        sys.stderr.write(f"Metrics visualization saved to: {output_path}\n")
        plt.show()
        return True
        
    except Exception as e:
        sys.stderr.write(f"Error creating visualization: {e}\n")
        return False

def main():
    '''
    Main function to evaluate clustering metrics across thresholds.
    '''
    
    # parse command line options
    options = Options(sys.argv)
    
    input_dir = options["input"]
    thresholds = options["thresholds"]
    output_path = options["output"]
    prefix = options["prefix"]
    
    # Prepare metrics storage
    metrics_data = {
        'prefix': prefix,
        'thresholds': {},
        'summary': {
            'total_thresholds': len(thresholds),
            'successful_evaluations': 0,
            'failed_evaluations': 0
        }
    }
    
    # Process each threshold
    for thresh in thresholds:
        file_path = os.path.join(input_dir, f'clustering_{thresh}.csv')
        sys.stderr.write(f"Processing threshold {thresh}...\n")
        
        # Load and validate dataset
        data = load_and_validate_dataset(file_path)
        if data is None:
            metrics_data['summary']['failed_evaluations'] += 1
            continue
        
        features = data['Transcript']
        labels = data['Cluster_ID']
        
        sys.stderr.write(f"Loaded {len(features)} samples with {len(set(labels))} unique clusters\n")
        
        # Calculate metrics
        silhouette, davies_bouldin, calinski_harabasz = calculate_clustering_metrics(features, labels)
        
        if silhouette is not None:
            metrics_data['thresholds'][thresh] = {
                'silhouette_score': silhouette,
                'davies_bouldin_index': davies_bouldin,
                'calinski_harabasz_index': calinski_harabasz,
                'num_samples': len(features),
                'num_clusters': len(set(labels))
            }
            metrics_data['summary']['successful_evaluations'] += 1
            sys.stderr.write(f"Threshold {thresh}: Silhouette={silhouette:.3f}, Davies-Bouldin={davies_bouldin:.3f}, Calinski-Harabasz={calinski_harabasz:.3f}\n")
        else:
            metrics_data['summary']['failed_evaluations'] += 1
            sys.stderr.write(f"Warning: Could not calculate metrics for threshold {thresh}\n")
    
    # Create visualization
    if not create_metrics_visualization(metrics_data, output_path, prefix):
        return 1
    
    # Summary
    sys.stderr.write(f"Evaluation complete: {metrics_data['summary']['successful_evaluations']}/{len(thresholds)} thresholds processed successfully\n")
    
    # Find best threshold based on silhouette score
    valid_thresholds = {k: v for k, v in metrics_data['thresholds'].items() if 'silhouette_score' in v}
    if valid_thresholds:
        best_threshold = max(valid_thresholds.keys(), 
                           key=lambda x: valid_thresholds[x]['silhouette_score'])
        best_score = valid_thresholds[best_threshold]['silhouette_score']
        sys.stderr.write(f"Best threshold based on Silhouette Score: {best_threshold} (score: {best_score:.3f})\n")
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
