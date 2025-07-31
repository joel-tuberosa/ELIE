#!/usr/bin/env python3

'''
USAGE
    validate_clusters_levenshtein.py [OPTION]

DESCRIPTION
    Script 3/4: Cluster validation using Levenshtein distance analysis.
    This script validates clusters by calculating Levenshtein distances between different 
    transcript types and determines if clusters are valid based on manual transcript 
    comparisons. It also generates visualizations showing the validation results.
    The input should be the output from script 2/4 (formatted comparison table).

OPTIONS
    -i, --input=FILE
        Path to formatted CSV file (output from script 2/4).
        
    -o, --output=FILE
        Path for validation results CSV.
        
    -c, --chart=FILE
        Path for pie chart output (PNG format). Default = auto-generated
        
    -t, --title=STR
        Title for the pie chart. Default = "Cluster Validation Results"
        
    -s, --separator=STR
        CSV separator character. Default = auto-detect
        
    --help
        Display this message

'''

import getopt, sys, csv, os, re
import numpy as np
from leven import levenshtein

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "i:o:c:t:s:", 
                                       ["input=", "output=", "chart=", "title=", "separator=", "help"])
        except getopt.GetoptError as err:
            sys.stderr.write(f"Error: {err}\n")
            sys.exit(1)
        
        for opt, arg in opts:
            if opt in ("-i", "--input"):
                self["input"] = arg
            elif opt in ("-o", "--output"):
                self["output"] = arg
            elif opt in ("-c", "--chart"):
                self["chart"] = arg
            elif opt in ("-t", "--title"):
                self["title"] = arg
            elif opt in ("-s", "--separator"):
                self["separator"] = arg
            elif opt == "--help":
                sys.stderr.write(__doc__)
                sys.exit(0)
        
        # check required arguments
        if not self["input"]:
            sys.stderr.write("Error: Input file required (-i/--input)\n")
            sys.exit(1)
        if not self["output"]:
            sys.stderr.write("Error: Output file required (-o/--output)\n")
            sys.exit(1)
        
        # set default chart output if not provided
        if not self["chart"]:
            base_name = os.path.splitext(self["output"])[0]
            self["chart"] = f"{base_name}_pie_chart.png"
        
        # store remaining arguments
        self["files"] = args

    def set_default(self):
        self["input"] = None
        self["output"] = None
        self["chart"] = None
        self["title"] = "Cluster Validation Results"
        self["separator"] = None
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
        sys.stderr.write(f"Warning: Could not determine delimiter for {file_path}, using ';' by default.\n")
        return ';'  # Default to semicolon for this type of data

def load_comparison_data(file_path: str, delimiter: str) -> dict:
    '''
    Load comparison table CSV file and return data as dictionary of lists.
    '''
    if not os.path.exists(file_path):
        sys.stderr.write(f"Error: File {file_path} not found.\n")
        return None
    
    try:
        data = {}
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            
            # Initialize data structure with column names
            for fieldname in reader.fieldnames:
                data[fieldname] = []
            
            # Read all rows
            for row in reader:
                for fieldname in reader.fieldnames:
                    data[fieldname].append(row.get(fieldname, ''))
        
        sys.stderr.write(f"Loaded {len(data[list(data.keys())[0]])} rows from {file_path}\n")
        return data
        
    except Exception as e:
        sys.stderr.write(f"Error loading file {file_path}: {e}\n")
        return None

def validate_required_columns(data: dict, required_cols: list) -> bool:
    '''
    Validate that required columns exist in the data.
    '''
    available_cols = list(data.keys())
    missing_cols = [col for col in required_cols if col not in available_cols]
    
    if missing_cols:
        sys.stderr.write(f"Error: Missing required columns: {missing_cols}\n")
        sys.stderr.write(f"Available columns: {available_cols}\n")
        return False
    
    return True

def normalize_text(text: str) -> str:
    '''
    Normalize text for comparison using simple preprocessing.
    '''
    if not text or text.strip() == '':
        return ''
    
    # Convert to lowercase and remove extra whitespace
    text = text.lower().strip()
    
    # Remove punctuation and special characters, keep only alphanumeric and spaces
    text = re.sub(r'[^\w\s]', '', text)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Split into words, remove common stop words, and sort
    common_stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 
        'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
        'to', 'was', 'were', 'will', 'with', 'the', 'this', 'but', 'they',
        'have', 'had', 'what', 'said', 'each', 'which', 'she', 'do',
        'how', 'their', 'if', 'up', 'out', 'many', 'then', 'them'
    }
    
    words = [word for word in text.split() if word not in common_stop_words and len(word) > 1]
    
    # Sort words for consistent comparison
    return ' '.join(sorted(words)).strip()

def calculate_levenshtein_distance(text1: str, text2: str) -> int:
    '''
    Calculate Levenshtein distance between two normalized texts.
    '''
    if not text1 or not text2:
        return -1  # Use -1 to indicate missing data
    
    norm_text1 = normalize_text(text1)
    norm_text2 = normalize_text(text2)
    
    if not norm_text1 or not norm_text2:
        return -1  # Use -1 to indicate missing data after normalization
    
    return levenshtein(norm_text1, norm_text2)

def validate_cluster_row(manual1: str, manual2: str) -> str:
    '''
    Validate a cluster based on manual transcript comparison.
    '''
    distance = calculate_levenshtein_distance(manual1, manual2)
    
    if distance == -1:
        return ''  # No validation possible
    
    return 'True' if distance == 0 else 'False'

def calculate_distances_and_validation(data: dict) -> dict:
    '''
    Calculate all Levenshtein distances and perform cluster validation.
    '''
    # Add new columns for distances and validation
    data['L1 OCR vs L2 OCR Levenshtein'] = []
    data['L1 Manual vs L2 Manual Levenshtein'] = []
    data['L1 OCR vs L1 Manual Levenshtein'] = []
    data['L2 OCR vs L2 Manual Levenshtein'] = []
    data['Cluster Validation'] = []
    
    num_rows = len(data['Label 1 OCR Transcript'])
    
    sys.stderr.write("Calculating Levenshtein distances...\n")
    
    for i in range(num_rows):
        l1_ocr = data['Label 1 OCR Transcript'][i]
        l1_manual = data['Label 1 Manual Transcript'][i]
        l2_ocr = data['Label 2 OCR Transcript'][i]
        l2_manual = data['Label 2 Manual Transcript'][i]
        
        # Calculate distances
        d1 = calculate_levenshtein_distance(l1_ocr, l2_ocr)
        d2 = calculate_levenshtein_distance(l1_manual, l2_manual)
        d3 = calculate_levenshtein_distance(l1_ocr, l1_manual)
        d4 = calculate_levenshtein_distance(l2_ocr, l2_manual)
        
        # Store distances (use empty string for -1 values)
        data['L1 OCR vs L2 OCR Levenshtein'].append(str(d1) if d1 != -1 else '')
        data['L1 Manual vs L2 Manual Levenshtein'].append(str(d2) if d2 != -1 else '')
        data['L1 OCR vs L1 Manual Levenshtein'].append(str(d3) if d3 != -1 else '')
        data['L2 OCR vs L2 Manual Levenshtein'].append(str(d4) if d4 != -1 else '')
        
        # Validate cluster based on manual transcript comparison
        validation = validate_cluster_row(l1_manual, l2_manual)
        data['Cluster Validation'].append(validation)
    
    return data

def generate_validation_statistics(data: dict) -> dict:
    '''
    Generate statistics about cluster validation results.
    '''
    validation_values = data['Cluster Validation']
    
    stats = {
        'total': len(validation_values),
        'valid': validation_values.count('True'),
        'invalid': validation_values.count('False'),
        'no_data': validation_values.count('')
    }
    
    return stats

def create_pie_chart(stats: dict, output_path: str, title: str) -> bool:
    '''
    Create a pie chart showing validation results.
    '''
    try:
        import matplotlib.pyplot as plt
        
        # Prepare data for pie chart (only non-empty values)
        labels = []
        sizes = []
        colors = []
        
        if stats['valid'] > 0:
            labels.append('True')
            sizes.append(stats['valid'])
            colors.append('#66B3FF')  # Blue
        
        if stats['invalid'] > 0:
            labels.append('False')
            sizes.append(stats['invalid'])
            colors.append('#FF9999')  # Red
        
        if not sizes:
            sys.stderr.write("Warning: No valid data for pie chart generation\n")
            return False
        
        # Create pie chart
        plt.figure(figsize=(10, 10))
        plt.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 12},
            wedgeprops={'edgecolor': 'black'}
        )
        plt.title(title, fontsize=16, pad=20)
        plt.legend(title='Validation Status', loc='upper right', fontsize=10)
        
        # Create output directory if needed
        chart_dir = os.path.dirname(output_path)
        if chart_dir and not os.path.exists(chart_dir):
            os.makedirs(chart_dir, exist_ok=True)
        
        # Save chart
        plt.savefig(output_path, format='png', bbox_inches='tight', dpi=300)
        plt.close()
        
        sys.stderr.write(f"Pie chart saved to: {output_path}\n")
        return True
        
    except ImportError:
        sys.stderr.write("Warning: matplotlib not available, skipping pie chart generation\n")
        return False
    except Exception as e:
        sys.stderr.write(f"Error creating pie chart: {e}\n")
        return False

def write_validation_results(data: dict, output_path: str, delimiter: str) -> bool:
    '''
    Write validation results to CSV file.
    '''
    try:
        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Define column order (original columns + new distance/validation columns)
        original_columns = [col for col in data.keys() 
                          if not col.endswith('Levenshtein') and col != 'Cluster Validation']
        
        distance_columns = [
            'L1 OCR vs L2 OCR Levenshtein',
            'L1 Manual vs L2 Manual Levenshtein', 
            'L1 OCR vs L1 Manual Levenshtein',
            'L2 OCR vs L2 Manual Levenshtein'
        ]
        
        columns = original_columns + distance_columns + ['Cluster Validation']
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns, delimiter=delimiter)
            writer.writeheader()
            
            # Write all rows
            num_rows = len(data[list(data.keys())[0]])
            for i in range(num_rows):
                row = {}
                for col in columns:
                    row[col] = data[col][i] if i < len(data[col]) else ''
                writer.writerow(row)
        
        sys.stderr.write(f"Validation results saved to: {output_path}\n")
        return True
        
    except Exception as e:
        sys.stderr.write(f"Error writing output file: {e}\n")
        return False

def main():
    '''
    Main function to validate clusters using Levenshtein distance analysis.
    '''
    
    # parse command line options
    options = Options(sys.argv)
    
    input_file = options["input"]
    output_file = options["output"]
    chart_output = options["chart"]
    chart_title = options["title"]
    separator = options["separator"]
    
    sys.stderr.write("Script 3/4: Cluster validation using Levenshtein distance\n")
    sys.stderr.write(f"Processing input file: {input_file}\n")
    sys.stderr.write(f"Validation results will be saved to: {output_file}\n")
    sys.stderr.write(f"Pie chart will be saved to: {chart_output}\n")
    
    # Detect or use specified delimiter
    if separator:
        delimiter = separator
    else:
        delimiter = detect_delimiter(input_file)
        sys.stderr.write(f"Using delimiter '{delimiter}'\n")
    
    # Load comparison data
    sys.stderr.write("Loading formatted data...\n")
    data = load_comparison_data(input_file, delimiter)
    if data is None:
        return 1
    
    # Validate required columns
    required_columns = [
        'Label 1 OCR Transcript',
        'Label 1 Manual Transcript', 
        'Label 2 OCR Transcript',
        'Label 2 Manual Transcript'
    ]
    if not validate_required_columns(data, required_columns):
        return 1
    
    # Calculate distances and perform validation
    sys.stderr.write("Normalizing text data...\n")
    data = calculate_distances_and_validation(data)
    
    # Generate statistics
    sys.stderr.write("Validating clusters...\n")
    stats = generate_validation_statistics(data)
    
    # Write results
    if not write_validation_results(data, output_file, delimiter):
        return 1
    
    # Create pie chart
    sys.stderr.write("Generating pie chart...\n")
    create_pie_chart(stats, chart_output, chart_title)
    
    # Report statistics
    sys.stderr.write("Cluster validation completed!\n")
    sys.stderr.write(f"Total clusters analyzed: {stats['total']}\n")
    sys.stderr.write(f"Valid clusters: {stats['valid']}\n")
    sys.stderr.write(f"Invalid clusters: {stats['invalid']}\n")
    sys.stderr.write(f"Clusters with insufficient data: {stats['no_data']}\n")
    sys.stderr.write("Script 3/4 completed successfully!\n")
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
