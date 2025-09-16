Diagnosis scripts
========================================================================
*Scripts for label clustering quality control*

.. contents ::

Overview
--------

This directory contains diagnostic scripts designed to analyze and evaluate the quality of label clustering results. These tools help identify potential issues in clustering algorithms and provide insights into cluster characteristics.

The scripts are organized into two main categories:

- **Data Processing Pipeline**: Scripts 1/4 through 4/4 for complete clustering analysis workflow
- **Quality Analysis Tools**: Additional scripts for evaluating clustering performance and identifying issues

Scripts
-------

Data Processing Pipeline (Scripts 1/4 - 4/4)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

merge_cluster_ids.py
~~~~~~~~~~~~~~~~~~~~

**Purpose**: Script 1/4 - Merge OCR transcripts with cluster IDs based on common ID column or reformat single files with automatic column detection.

**Description**: 
This script can either merge two separate CSV files or reformat a single file that already contains both transcript and cluster data. It features automatic column detection and mapping to handle various input formats flexibly. This is typically the first step in a data processing pipeline for clustering analysis.

Key features:

- **Dual-mode operation**: Two-file merge OR single-file reformatting
- **Automatic column detection**: Detects and maps various column name patterns (label.ID, group.ID, label.v, etc.)
- **Flexible input formats**: Handles different CSV structures and naming conventions
- Maintains column order (ID, Cluster_ID, then other columns)
- Handles missing cluster IDs with warnings
- Supports flexible CSV delimiter detection

**Usage**::

    # Two-file merge mode
    ./merge_cluster_ids.py -t transcripts.csv -c clusters.csv -o merged_output.csv
    
    # Single-file reformat mode
    ./merge_cluster_ids.py -i clustered_results.csv -o reformatted_output.csv

**Options**:

- ``-t, --transcripts=FILE``: Path to CSV file containing transcript data (two-file mode)
- ``-c, --clusters=FILE``: Path to CSV file containing ID and Cluster_ID columns (two-file mode)
- ``-i, --input=FILE``: Path to single CSV file containing both transcripts and cluster IDs (single-file mode)
- ``-o, --output=FILE``: Path for output CSV file with merged data
- ``-s, --separator=STR``: CSV separator character (default: auto-detect)
- ``--help``: Display help message

**Input format**:

**Two-file mode**:

- **Transcripts file** must contain at minimum an ID column and transcript data
- **Clusters file** must contain ID and Cluster_ID columns

**Single-file mode**:

- **Input file** must contain both ID/cluster data and transcript data
- **Automatic column detection** supports various naming patterns:

  - ID columns: ``ID``, ``label.ID``, ``label_ID``
  - Cluster columns: ``Cluster_ID``, ``group.ID``, ``group_ID``  
  - Transcript columns: ``TranscriptOCR``, ``TranscriptManual``, ``label.v``

**Output format**:

The output CSV contains standardized columns:

- ``ID``: Unique identifier for each label
- ``Cluster_ID``: Cluster identifier (positioned as second column)
- ``TranscriptOCR``: OCR-generated transcript text
- ``TranscriptManual``: Manually corrected transcript text (if available)
- Additional columns from input files are preserved

**Example**::

    # Two-file merge operation
    ./merge_cluster_ids.py -t ocr_transcripts.csv -c clustering_results.csv -o merged_data.csv
    
    # Single-file reformat operation (with automatic column detection)
    ./merge_cluster_ids.py -i clustered_results.csv -o reformatted_data.csv
    
    # Specify delimiter explicitly
    ./merge_cluster_ids.py -t data.csv -c clusters.csv -o output.csv -s ";"
    
    # Real-world example with flexible column names
    ./merge_cluster_ids.py -i /path/to/clustered_results.txt -o standardized_output.csv

**Dependencies**: 

- Built-in Python modules only (csv, sys, os, getopt)


format_comparison_table.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Script 2/4 - Format clustered data into comparison table for side-by-side analysis.

**Description**: 
This script takes a CSV file with clustered data and reformats it into a comparison table where each row represents one cluster with up to 2 labels side by side for easy comparison. The input should be the output from script 1/4 (merged transcripts with cluster IDs). This facilitates manual review and quality assessment of clustering results.

Key features:

- Creates side-by-side comparison layout for easy manual review
- Handles clusters with 1 or 2 labels appropriately
- Warns about clusters with more than 2 labels (uses only first 2)
- Maintains proper column structure for comparison analysis

**Usage**::

    ./format_comparison_table.py -i merged_data.csv -o comparison_table.csv

**Options**:

- ``-i, --input=FILE``: Path to CSV file with cluster data (output from script 1/4)
- ``-o, --output=FILE``: Path for formatted comparison table CSV
- ``-s, --separator=STR``: CSV separator character (default: auto-detect)
- ``--help``: Display help message

**Input format**:

The input CSV file must contain (typically from merge_cluster_ids.py):

- ``ID``: Unique identifier for each label
- ``Cluster_ID``: Cluster identifier grouping related labels
- ``TranscriptOCR``: OCR-generated transcript text
- ``TranscriptManual``: Manually corrected transcript text

**Output format**:

The output CSV contains one row per cluster with the following columns:

- ``Cluster ID``: The cluster identifier
- ``Label 1 ID``: ID of the first label in the cluster
- ``Label 1 OCR Transcript``: OCR transcript of the first label
- ``Label 1 Manual Transcript``: Manual transcript of the first label
- ``Label 2 ID``: ID of the second label in the cluster (empty if only 1 label)
- ``Label 2 OCR Transcript``: OCR transcript of the second label (empty if only 1 label)
- ``Label 2 Manual Transcript``: Manual transcript of the second label (empty if only 1 label)

**Example**::

    # Format clustered data for comparison
    ./format_comparison_table.py -i merged_transcripts.csv -o side_by_side_comparison.csv
    
    # Specify delimiter explicitly
    ./format_comparison_table.py -i data.csv -o table.csv -s ";"

**Dependencies**:

- Built-in Python modules only (csv, sys, os, getopt)


validate_clusters_levenshtein.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Script 3/4 - Validates clusters by calculating Levenshtein distances between different transcript types and determines if clusters are valid based on manual transcript comparisons.

**Description**: 
This script performs cluster validation using Levenshtein distance analysis between OCR and manual transcripts. It:

- Normalizes text data by removing punctuation, standardizing case, and filtering common stop words
- Calculates Levenshtein distances between all combinations of transcript types (OCR vs OCR, Manual vs Manual, OCR vs Manual)
- Validates clusters based on manual transcript similarity (distance = 0 means valid cluster)
- Generates a pie chart visualization showing validation results
- Outputs comprehensive distance metrics and validation status for each cluster

This is the third script in a 4-script pipeline for clustering data analysis. The input should be the output from script 2/4 (formatted comparison table).

**Key Features**:

- Text normalization with stop word removal and word sorting for consistent comparison
- Multiple Levenshtein distance calculations for analysis
- Automatic cluster validation based on manual transcript comparison
- Statistical reporting of validation results
- Visual pie chart generation showing valid vs invalid clusters
- Handles missing data

**Input**:
A CSV file containing formatted comparison data with columns:

- ``Label 1 OCR Transcript``: OCR transcript of the first label
- ``Label 1 Manual Transcript``: Manual transcript of the first label  
- ``Label 2 OCR Transcript``: OCR transcript of the second label
- ``Label 2 Manual Transcript``: Manual transcript of the second label

**Output**:
- A CSV file with original data plus new columns:

  - ``L1 OCR vs L2 OCR Levenshtein``: Distance between OCR transcripts
  - ``L1 Manual vs L2 Manual Levenshtein``: Distance between manual transcripts
  - ``L1 OCR vs L1 Manual Levenshtein``: Distance between OCR and manual for label 1
  - ``L2 OCR vs L2 Manual Levenshtein``: Distance between OCR and manual for label 2
  - ``Cluster Validation``: 'True' if cluster is valid, 'False' if invalid, empty if insufficient data
- A PNG pie chart showing validation results distribution
- Console statistics about validation outcomes

**Example**::

    # Validate clusters with default settings
    ./validate_clusters_levenshtein.py -i comparison_table.csv -o validation_results.csv
    
    # Specify custom chart output and title
    ./validate_clusters_levenshtein.py -i data.csv -o results.csv -c validation_chart.png -t "My Cluster Validation"
    
    # Use specific CSV separator
    ./validate_clusters_levenshtein.py -i data.csv -o results.csv -s ";"

**Dependencies**:

- ``leven``: For fast Levenshtein distance calculations
- ``matplotlib``: For pie chart generation and visualization
- Built-in Python modules (csv, sys, os, getopt, re)


generate_distance_boxplot.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Purpose**: Script 4/4 - Generate Levenshtein distance boxplot visualization from cluster validation data.

**Description**: 
This script creates boxplot visualizations of Levenshtein distances from cluster validation data. It takes the output from script 3/4 and generates boxplots showing the distribution of distances between different transcript types. The script:

- Loads validation results with Levenshtein distance calculations
- Extracts numeric data from specified distance columns
- Calculates comprehensive boxplot statistics (quartiles, outliers, etc.)
- Creates customizable boxplot visualizations using matplotlib
- Provides detailed statistical summaries for each distance metric

This is the fourth and final script in the 4-script pipeline for clustering data analysis, providing visual insights into the distribution and spread of edit distances.

**Key Features**:

- Customizable column selection for flexible analysis
- Multiple built-in color palettes (Set2, Set1, Dark2, Pastel1, viridis, plasma)
- Statistical reporting (quartiles, outliers, mean, std dev)
- Output with configurable figure size and DPI
- Robust handling of missing or invalid data
- Automatic outlier detection and visualization

**Input**:

A CSV file containing validation results with Levenshtein distance columns:

- ``L1 OCR vs L2 OCR Levenshtein``: Distance between OCR transcripts
- ``L1 Manual vs L2 Manual Levenshtein``: Distance between manual transcripts
- ``L1 OCR vs L1 Manual Levenshtein``: Distance between OCR and manual for label 1
- ``L2 OCR vs L2 Manual Levenshtein``: Distance between OCR and manual for label 2
- Any other numeric columns can also be visualized

**Output**:

- A PNG boxplot visualization showing distance distributions
- Console output with detailed statistics for each column (count, quartiles, outliers, etc.)
- Visual representation of data spread, central tendency, and outliers

**Example**::

    # Generate boxplot for manual transcript comparison (default)
    ./generate_distance_boxplot.py -i validation_results.csv -o distance_boxplot.png
    
    # Plot multiple distance metrics
    ./generate_distance_boxplot.py -i results.csv -o boxplot.png -c "L1 Manual vs L2 Manual Levenshtein,L1 OCR vs L2 OCR Levenshtein"
    
    # Customize appearance and size
    ./generate_distance_boxplot.py -i data.csv -o plot.png --figure-size "12,6" --palette "viridis" -t "Distance Analysis"
    
    # Use specific CSV separator
    ./generate_distance_boxplot.py -i data.csv -o plot.png -s ";"

**Dependencies**:

- ``numpy``: For statistical calculations and array operations
- ``matplotlib``: For boxplot generation and visualization
- Built-in Python modules (csv, sys, os, getopt)


Quality Analysis Tools
~~~~~~~~~~~~~~~~~~~~~~

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
The input directory must contain CSV files with a naming pattern ``clustering_<threshold>.csv`` where ``<threshold>`` represents the similarity threshold used for clustering. Each CSV file must contain:

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
This script calculates clustering quality metrics (Silhouette Score, Davies-Bouldin Index, Calinski-Harabasz Index) for multiple clustering results with different thresholds. It provides a quantitative assessment of clustering quality and helps identify the threshold that produces the best clustering performance.

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
