#!/usr/bin/env python3

'''
USAGE
    format_comparison_table.py [OPTION]

DESCRIPTION
    Script 2/4: Format clustered data into comparison table for side-by-side analysis.
    This script takes a CSV file with clustered data and reformats it into a comparison 
    table where each row represents one cluster with up to 2 labels side by side for 
    easy comparison. The input should be the output from script 1/4 (merged transcripts 
    with cluster IDs).

OPTIONS
    -i, --input=FILE
        Path to CSV file with cluster data (output from script 1/4).
        
    -o, --output=FILE
        Path for formatted comparison table CSV.
        
    -s, --separator=STR
        CSV separator character. Default = auto-detect
        
    --help
        Display this message

'''

import getopt, sys, csv, os

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "i:o:s:", 
                                       ["input=", "output=", "separator=", "help"])
        except getopt.GetoptError as err:
            sys.stderr.write(f"Error: {err}\n")
            sys.exit(1)
        
        for opt, arg in opts:
            if opt in ("-i", "--input"):
                self["input"] = arg
            elif opt in ("-o", "--output"):
                self["output"] = arg
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
        
        # store remaining arguments
        self["files"] = args

    def set_default(self):
        self["input"] = None
        self["output"] = None
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

def load_clustered_data(file_path: str, delimiter: str) -> dict:
    '''
    Load clustered CSV file and return data as dictionary of lists.
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

def group_data_by_cluster(data: dict) -> dict:
    '''
    Group data by Cluster_ID and return dictionary of cluster groups.
    '''
    clusters = {}
    
    # Group rows by Cluster_ID
    for i, cluster_id in enumerate(data['Cluster_ID']):
        if cluster_id not in clusters:
            clusters[cluster_id] = []
        
        # Create row dictionary for this item
        row = {}
        for col in data.keys():
            row[col] = data[col][i] if i < len(data[col]) else ''
        
        clusters[cluster_id].append(row)
    
    sys.stderr.write(f"Found {len(clusters)} unique clusters\n")
    return clusters

def format_comparison_table(clusters: dict) -> list:
    '''
    Format clustered data into comparison table format.
    '''
    formatted_data = []
    clusters_with_more_than_2 = 0
    
    for cluster_id, group in clusters.items():
        if len(group) > 2:
            clusters_with_more_than_2 += 1
        
        # Create comparison row with up to 2 labels side by side
        row = {
            "Cluster ID": cluster_id,
            "Label 1 ID": group[0]["ID"] if len(group) > 0 else "",
            "Label 1 OCR Transcript": group[0].get("TranscriptOCR", "") if len(group) > 0 else "",
            "Label 1 Manual Transcript": group[0].get("TranscriptManual", "") if len(group) > 0 else "",
            "Label 2 ID": group[1]["ID"] if len(group) > 1 else "",
            "Label 2 OCR Transcript": group[1].get("TranscriptOCR", "") if len(group) > 1 else "",
            "Label 2 Manual Transcript": group[1].get("TranscriptManual", "") if len(group) > 1 else "",
        }
        formatted_data.append(row)
    
    if clusters_with_more_than_2 > 0:
        sys.stderr.write(f"Warning: {clusters_with_more_than_2} clusters had more than 2 items (only first 2 used)\n")
    
    sys.stderr.write(f"Created {len(formatted_data)} cluster comparison rows\n")
    return formatted_data

def write_comparison_table(formatted_data: list, output_path: str, delimiter: str) -> bool:
    '''
    Write formatted comparison table to CSV file.
    '''
    try:
        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Define column order for comparison table
        columns = [
            "Cluster ID",
            "Label 1 ID", "Label 1 OCR Transcript", "Label 1 Manual Transcript",
            "Label 2 ID", "Label 2 OCR Transcript", "Label 2 Manual Transcript"
        ]
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns, delimiter=delimiter)
            writer.writeheader()
            
            # Write all formatted rows
            for row in formatted_data:
                writer.writerow(row)
        
        sys.stderr.write(f"Formatted comparison table saved to: {output_path}\n")
        return True
        
    except Exception as e:
        sys.stderr.write(f"Error writing output file: {e}\n")
        return False

def main():
    '''
    Main function to format clustered data into comparison table.
    '''
    
    # parse command line options
    options = Options(sys.argv)
    
    input_file = options["input"]
    output_file = options["output"]
    separator = options["separator"]
    
    sys.stderr.write("Script 2/4: Format clustered data into comparison table\n")
    sys.stderr.write(f"Processing input file: {input_file}\n")
    sys.stderr.write(f"Output will be saved to: {output_file}\n")
    
    # Detect or use specified delimiter
    if separator:
        delimiter = separator
    else:
        delimiter = detect_delimiter(input_file)
        sys.stderr.write(f"Using delimiter '{delimiter}'\n")
    
    # Load clustered data
    sys.stderr.write("Loading cluster data...\n")
    data = load_clustered_data(input_file, delimiter)
    if data is None:
        return 1
    
    # Validate required columns
    required_columns = ['Cluster_ID', 'ID', 'TranscriptOCR', 'TranscriptManual']
    if not validate_required_columns(data, required_columns):
        return 1
    
    # Group data by clusters
    sys.stderr.write("Grouping data by Cluster_ID...\n")
    clusters = group_data_by_cluster(data)
    
    # Format into comparison table
    sys.stderr.write("Creating formatted comparison table...\n")
    formatted_data = format_comparison_table(clusters)
    
    # Write output
    if not write_comparison_table(formatted_data, output_file, delimiter):
        return 1
    
    sys.stderr.write("Script 2/4 completed successfully!\n")
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
