#!/usr/bin/env python3

'''
USAGE
    merge_cluster_ids.py [OPTION]

DESCRIPTION
    Script 1/4: Merge OCR transcripts with cluster IDs based on common ID column.
    This script can either merge two separate CSV files or reformat a single file 
    that already contains both transcript and cluster data. Column names are 
    automatically detected and mapped to standard names.

OPTIONS
    -t, --transcripts=FILE
        Path to CSV file containing transcript data.
        
    -c, --clusters=FILE
        Path to CSV file containing ID and Cluster_ID columns.
        (Optional if using single file mode)
        
    -i, --input=FILE
        Path to single CSV file containing both transcripts and cluster IDs.
        (Alternative to using separate -t and -c files)
        
    -o, --output=FILE
        Path for output CSV file with merged data.
        
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
                                       "t:c:i:o:s:", 
                                       ["transcripts=", "clusters=", "input=", "output=", "separator=", "help"])
        except getopt.GetoptError as err:
            sys.stderr.write(f"Error: {err}\n")
            sys.exit(1)
        
        for opt, arg in opts:
            if opt in ("-t", "--transcripts"):
                self["transcripts"] = arg
            elif opt in ("-c", "--clusters"):
                self["clusters"] = arg
            elif opt in ("-i", "--input"):
                self["input"] = arg
            elif opt in ("-o", "--output"):
                self["output"] = arg
            elif opt in ("-s", "--separator"):
                self["separator"] = arg
            elif opt == "--help":
                sys.stderr.write(__doc__)
                sys.exit(0)
        
        # check required arguments
        if self["input"]:
            # Single file mode
            if self["transcripts"] or self["clusters"]:
                sys.stderr.write("Error: Cannot use -i/--input with -t/--transcripts or -c/--clusters\n")
                sys.exit(1)
        else:
            # Two file mode
            if not self["transcripts"]:
                sys.stderr.write("Error: Transcripts file required (-t/--transcripts) or use single file mode (-i/--input)\n")
                sys.exit(1)
            if not self["clusters"]:
                sys.stderr.write("Error: Clusters file required (-c/--clusters) or use single file mode (-i/--input)\n")
                sys.exit(1)
        
        if not self["output"]:
            sys.stderr.write("Error: Output file required (-o/--output)\n")
            sys.exit(1)
        
        # store remaining arguments
        self["files"] = args

    def set_default(self):
        self["transcripts"] = None
        self["clusters"] = None
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

def load_csv_data(file_path: str, delimiter: str) -> dict:
    '''
    Load CSV file and return data as dictionary of lists.
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

def detect_column_mapping(columns: list) -> dict:
    '''
    Detect and map column names to standard names used by the script.
    Returns a mapping of standard_name -> actual_column_name
    '''
    mapping = {}
    
    # Patterns for ID column
    id_patterns = ['id', 'label.id', 'label_id', 'labelid', 'identifier']
    
    # Patterns for Cluster_ID column  
    cluster_patterns = ['cluster_id', 'group.id', 'group_id', 'groupid', 'cluster', 'group']
    
    # Patterns for transcript columns
    transcript_patterns = ['transcript', 'label.v', 'label_v', 'text', 'content', 'transcriptocr', 'transcriptmanual']
    
    # Convert columns to lowercase for comparison
    lower_columns = [col.lower() for col in columns]
    
    # Find ID column
    for pattern in id_patterns:
        for i, col in enumerate(lower_columns):
            if pattern in col or col in pattern:
                mapping['ID'] = columns[i]
                break
        if 'ID' in mapping:
            break
    
    # Find Cluster_ID column
    for pattern in cluster_patterns:
        for i, col in enumerate(lower_columns):
            if pattern in col or col in pattern:
                mapping['Cluster_ID'] = columns[i]
                break
        if 'Cluster_ID' in mapping:
            break
    
    # Find transcript columns
    transcript_cols = []
    for pattern in transcript_patterns:
        for i, col in enumerate(lower_columns):
            if pattern in col or col in pattern:
                transcript_cols.append(columns[i])
                break
    
    # Assign transcript columns
    if transcript_cols:
        mapping['TranscriptOCR'] = transcript_cols[0]
        mapping['TranscriptManual'] = transcript_cols[0] if len(transcript_cols) == 1 else transcript_cols[1]
    
    return mapping

def validate_required_columns(data: dict, required_cols: list, file_name: str) -> dict:
    '''
    Validate that required columns exist in the data and return column mapping.
    '''
    available_cols = list(data.keys())
    mapping = detect_column_mapping(available_cols)
    
    missing_mappings = []
    for req_col in required_cols:
        if req_col not in mapping:
            missing_mappings.append(req_col)
    
    if missing_mappings:
        sys.stderr.write(f"Error: Could not find columns for {missing_mappings} in {file_name}\n")
        sys.stderr.write(f"Available columns: {available_cols}\n")
        sys.stderr.write(f"Detected mappings: {mapping}\n")
        return None
    
    sys.stderr.write(f"Column mapping for {file_name}: {mapping}\n")
    return mapping

def merge_data(transcripts_data: dict, clusters_data: dict, transcripts_mapping: dict, clusters_mapping: dict) -> dict:
    '''
    Merge transcripts data with cluster IDs based on ID column using column mappings.
    '''
    # Create mapping from ID to Cluster_ID using actual column names
    id_col = clusters_mapping['ID']
    cluster_col = clusters_mapping['Cluster_ID']
    
    id_to_cluster = {}
    for i, id_val in enumerate(clusters_data[id_col]):
        if id_val:  # Skip empty IDs
            id_to_cluster[id_val] = clusters_data[cluster_col][i]
    
    # Create merged data structure with standardized column names
    merged_data = {}
    
    # Start with ID column (using standardized name)
    transcripts_id_col = transcripts_mapping['ID']
    merged_data['ID'] = transcripts_data[transcripts_id_col][:]
    
    # Add Cluster_ID column
    merged_data['Cluster_ID'] = []
    missing_clusters = 0
    
    for id_val in transcripts_data[transcripts_id_col]:
        cluster_id = id_to_cluster.get(id_val, '')
        merged_data['Cluster_ID'].append(cluster_id)
        if not cluster_id:
            missing_clusters += 1
    
    # Add transcript columns with standardized names
    if 'TranscriptOCR' in transcripts_mapping:
        ocr_col = transcripts_mapping['TranscriptOCR']
        merged_data['TranscriptOCR'] = transcripts_data[ocr_col][:]
    
    if 'TranscriptManual' in transcripts_mapping:
        manual_col = transcripts_mapping['TranscriptManual']
        merged_data['TranscriptManual'] = transcripts_data[manual_col][:]
    
    # Add any remaining columns from transcripts (excluding already processed ones)
    processed_cols = set([transcripts_mapping.get(key) for key in transcripts_mapping.values() if key])
    for col in transcripts_data:
        if col not in processed_cols and col not in merged_data:
            merged_data[col] = transcripts_data[col][:]
    
    if missing_clusters > 0:
        sys.stderr.write(f"Warning: {missing_clusters} rows have missing Cluster_ID values\n")
    
    sys.stderr.write(f"Merge completed. {len(merged_data['ID'])} rows in final dataset\n")
    return merged_data

def write_csv_data(data: dict, output_path: str, delimiter: str) -> bool:
    '''
    Write merged data to CSV file.
    '''
    try:
        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Get column order: ID, Cluster_ID, then others
        columns = ['ID', 'Cluster_ID']
        for col in data.keys():
            if col not in columns:
                columns.append(col)
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=columns, delimiter=delimiter)
            writer.writeheader()
            
            # Write rows
            num_rows = len(data['ID'])
            for i in range(num_rows):
                row = {}
                for col in columns:
                    row[col] = data[col][i] if i < len(data[col]) else ''
                writer.writerow(row)
        
        sys.stderr.write(f"Merged data saved to: {output_path}\n")
        return True
        
    except Exception as e:
        sys.stderr.write(f"Error writing output file: {e}\n")
        return False

def reformat_single_file(data: dict, mapping: dict) -> dict:
    '''
    Reformat a single file that already contains both transcript and cluster data.
    '''
    reformatted_data = {}
    
    # Map columns to standard names
    id_col = mapping['ID']
    cluster_col = mapping['Cluster_ID']
    
    reformatted_data['ID'] = data[id_col][:]
    reformatted_data['Cluster_ID'] = data[cluster_col][:]
    
    # Add transcript columns
    if 'TranscriptOCR' in mapping:
        ocr_col = mapping['TranscriptOCR']
        reformatted_data['TranscriptOCR'] = data[ocr_col][:]
    
    if 'TranscriptManual' in mapping:
        manual_col = mapping['TranscriptManual']
        reformatted_data['TranscriptManual'] = data[manual_col][:]
    
    # Add any remaining columns (excluding already processed ones)
    processed_cols = set([mapping.get(key) for key in mapping.keys()])
    for col in data:
        if col not in processed_cols and col not in reformatted_data:
            reformatted_data[col] = data[col][:]
    
    sys.stderr.write(f"Reformatting completed. {len(reformatted_data['ID'])} rows in final dataset\n")
    return reformatted_data

def main():
    '''
    Main function to merge OCR transcripts with cluster IDs or reformat single file.
    '''
    
    # parse command line options
    options = Options(sys.argv)
    
    input_file = options["input"]
    transcripts_file = options["transcripts"]
    clusters_file = options["clusters"]
    output_file = options["output"]
    separator = options["separator"]
    
    sys.stderr.write("Script 1/4: Merge OCR transcripts with cluster IDs\n")
    
    if input_file:
        # Single file mode
        sys.stderr.write(f"Processing single input file: {input_file}\n")
        sys.stderr.write(f"Output will be saved to: {output_file}\n")
        
        # Detect delimiter
        if separator:
            delimiter = separator
        else:
            delimiter = detect_delimiter(input_file)
            sys.stderr.write(f"Using delimiter '{delimiter}'\n")
        
        # Load single file
        sys.stderr.write("Loading input file...\n")
        data = load_csv_data(input_file, delimiter)
        if data is None:
            return 1
        
        # Validate and get mapping for single file (needs both ID and Cluster_ID)
        mapping = validate_required_columns(data, ['ID', 'Cluster_ID'], 'input file')
        if mapping is None:
            return 1
        
        # Reformat data
        sys.stderr.write("Reformatting data...\n")
        final_data = reformat_single_file(data, mapping)
        
    else:
        # Two file mode
        sys.stderr.write(f"Processing transcripts file: {transcripts_file}\n")
        sys.stderr.write(f"Processing clusters file: {clusters_file}\n")
        sys.stderr.write(f"Output will be saved to: {output_file}\n")
        
        # Detect or use specified delimiter for transcripts file
        if separator:
            transcripts_delimiter = separator
        else:
            transcripts_delimiter = detect_delimiter(transcripts_file)
            sys.stderr.write(f"Using delimiter '{transcripts_delimiter}' for transcripts file\n")
        
        # Detect or use specified delimiter for clusters file
        if separator:
            clusters_delimiter = separator
        else:
            clusters_delimiter = detect_delimiter(clusters_file)
            sys.stderr.write(f"Using delimiter '{clusters_delimiter}' for clusters file\n")
        
        # Load CSV files
        sys.stderr.write("Loading CSV files...\n")
        transcripts_data = load_csv_data(transcripts_file, transcripts_delimiter)
        if transcripts_data is None:
            return 1
        
        clusters_data = load_csv_data(clusters_file, clusters_delimiter)
        if clusters_data is None:
            return 1
        
        # Validate required columns and get mappings
        transcripts_mapping = validate_required_columns(transcripts_data, ['ID'], 'transcripts file')
        if transcripts_mapping is None:
            return 1
        
        clusters_mapping = validate_required_columns(clusters_data, ['ID', 'Cluster_ID'], 'clusters file')
        if clusters_mapping is None:
            return 1
        
        # Merge data
        sys.stderr.write("Merging data...\n")
        final_data = merge_data(transcripts_data, clusters_data, transcripts_mapping, clusters_mapping)
        delimiter = transcripts_delimiter
    
    # Write output
    if not write_csv_data(final_data, output_file, delimiter):
        return 1
    
    sys.stderr.write("Script 1/4 completed successfully!\n")
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
