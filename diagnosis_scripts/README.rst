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
