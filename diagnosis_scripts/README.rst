Diagnosis scripts
========================================================================
*Scripts for label clustering quality control*

.. contents ::

Overview
--------

This directory contains diagnostic scripts designed to analyze and evaluate the quality of label clustering results. These tools help identify potential issues in clustering algorithms and provide insights into cluster characteristics.

Scripts
-------

find_distant_pairs.py
~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Identifies the most distant label pairs within each cluster based on Levenshtein edit distance.

**Description**: 
This script analyzes clusters of labels to find the two labels with the maximum edit distance within each cluster. This is useful for quality control of clustering algorithms, as it helps identify:

- Clusters that may be too permissive (containing very different labels)
- Potential outliers within clusters
- The maximum variability within each cluster

**Usage**::

    ./find_distant_pairs.py -i input.csv -o output.csv

**Options**:

- ``-i, --input=FILE``: Path to input CSV file containing clustered labels
- ``-o, --output=FILE``: Path to output CSV file where results will be saved  
- ``-s, --separator=STR``: Field separator for reading the table (default: auto-detect)
- ``--help``: Display help message

**Input format**:
The input CSV file must contain the following columns:

- ``ID`` (or ``label_ID``): Unique identifier for each label
- ``Transcript`` (or ``label_v``): The text content of the label
- ``Cluster_ID`` (or ``group_ID``): Cluster identifier grouping related labels

**Output format**:
The output CSV contains one row per cluster with the following columns:

- ``Cluster ID``: The cluster identifier
- ``Label 1 ID``: ID of the first label in the most distant pair
- ``Label 1 Transcript``: Text content of the first label
- ``Label 2 ID``: ID of the second label in the most distant pair  
- ``Label 2 Transcript``: Text content of the second label
- ``Distance``: Levenshtein edit distance between the two labels

For clusters containing only one label, the second label fields will be empty.

**Example**::

    # Find most distant pairs in clustered labels
    ./find_distant_pairs.py -i clustered_labels.csv -o distant_pairs.csv
    
    # Specify comma separator explicitly
    ./find_distant_pairs.py -i data.csv -o results.csv -s ","

**Dependencies**: 
- ``pandas``: For CSV processing
- ``leven``: For Levenshtein distance calculation (same as used in mfnb.utils)


clustering_elbow_method.py
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Determines the optimal clustering threshold using the elbow method based on inertia values from multiple clustering results.

**Description**: 
This script implements the elbow method to find the optimal similarity threshold for clustering algorithms. It analyzes multiple clustering CSV files (each representing results with different thresholds) and identifies the threshold that provides the best balance between cluster cohesion and number of clusters.

Key features:
- Uses TF-IDF vectorization with mfnb package tokenization patterns
- Calculates within-cluster sum of squares (inertia) for each threshold
- Employs the kneed package for elbow point detection
- Provides automatic fallback to manual elbow detection if needed
- Generates elbow plots

**Usage**::

    ./clustering_elbow_method.py -i clustering_results_dir -o elbow_plot.png

**Options**:

- ``-i, --input=DIR``: Directory containing clustering CSV files with naming pattern 'clustering_*.csv'
- ``-o, --output=FILE``: Output path for the elbow plot image (PNG format)
- ``-p, --prefix=STR``: Prefix for plot title (default: "Dataset")
- ``--help``: Display help message

**Input format**:
The input directory must contain CSV files with naming pattern ``clustering_<threshold>.csv`` where ``<threshold>`` represents the similarity threshold used for clustering. Each CSV file must contain:

- ``Transcript``: The text content of labels
- ``Cluster_ID``: Cluster identifier for each label

**Output**:
- A PNG plot showing the elbow curve with the detected optimal threshold highlighted
- Console output indicating the recommended threshold value

**Example**::

    # Analyze clustering results in a directory
    ./clustering_elbow_method.py -i /path/to/clustering_results -o elbow_analysis.png
    
    # With custom plot title
    ./clustering_elbow_method.py -i results/ -o plot.png -p "Label Clustering Analysis"

**Dependencies**: 
- ``pandas``: For CSV processing and data handling
- ``numpy``: For numerical computations and array operations
- ``matplotlib``: For plot generation and visualization
- ``scikit-learn``: For TF-IDF vectorization (TfidfVectorizer) and distance calculations (pairwise_distances)
- ``kneed``: For elbow point detection (same as used in mfnb.utils)


clustering_evaluation_metrics.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Evaluates clustering quality metrics across multiple threshold values to assess clustering performance and identify optimal thresholds.

**Description**: 
This script calculates clustering quality metrics (Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index) for multiple clustering results with different thresholds. It provides quantitative assessment of clustering quality and helps identify the threshold that produces the best clustering performance.

Key features:
- Uses TF-IDF vectorization
- Calculates three complementary clustering quality metrics
- Processes multiple threshold files sequentially
- Generates heatmap visualizations
- Provides automatic best threshold recommendation based on Silhouette Score
- Compatible with output from other clustering diagnosis scripts

**Usage**::

    ./clustering_evaluation_metrics.py -i clustering_results_dir -t "0.3,0.4,0.5" -o metrics_heatmap.png

**Options**:

- ``-i, --input=DIR``: Directory containing clustering CSV files with naming pattern 'clustering_*.csv'
- ``-t, --thresholds=LIST``: Comma-separated list of thresholds to evaluate (e.g., "0.3,0.4,0.5")
- ``-o, --output=FILE``: Output path for the metrics heatmap visualization (PNG format)
- ``-p, --prefix=STR``: Prefix for plot titles (default: "Dataset")
- ``--help``: Display help message

**Input format**:
The input directory must contain CSV files with naming pattern ``clustering_<threshold>.csv`` where ``<threshold>`` represents the similarity threshold used for clustering. Each CSV file must contain:

- ``Transcript``: The text content of labels
- ``Cluster_ID``: Cluster identifier for each label

**Output**:
A PNG file containing three heatmap visualizations:
- Silhouette Score heatmap (higher values indicate better clustering)
- Davies-Bouldin Index heatmap (lower values indicate better clustering)
- Calinski-Harabasz Index heatmap (higher values indicate better clustering)
- Console output with best threshold recommendation

**Example**::

    # Evaluate clustering quality for multiple thresholds
    ./clustering_evaluation_metrics.py -i /path/to/clustering_results -t "0.2,0.3,0.4,0.5,0.6" -o evaluation_heatmap.png
    
    # With custom dataset prefix
    ./clustering_evaluation_metrics.py -i results/ -t "0.3,0.4,0.5" -o metrics.png -p "Museum Labels"

**Dependencies**: 
- ``numpy``: For numerical computations and array operations
- ``matplotlib``: For plot generation and visualization
- ``seaborn``: For heatmap creation and styling
- ``scikit-learn``: For TF-IDF vectorization and clustering metrics calculation
