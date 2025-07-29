#!/usr/bin/env python3

'''
USAGE
    find_distant_pairs.py [OPTION]

DESCRIPTION
    Find the most distant label pairs within clusters in a CSV file
    based on Levenshtein distance. For each cluster, identifies the
    two labels with the maximum edit distance between their transcripts.

OPTIONS
    -i, --input=FILE
        Path to input CSV file containing clustered labels.
        
    -o, --output=FILE
        Path to output CSV file where results will be saved.
        
    -s, --separator=STR
        Set the field separator to read the table. Default = auto-detect
        
    --help
        Display this message

'''

import getopt, sys, csv, os
import pandas as pd
from leven import levenshtein

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

def detect_delimiter(file_path, default=';'):
    """Detects the delimiter of a CSV file by reading a sample of it."""
    with open(file_path, 'r', newline='') as f:
        sample = f.read(1024)
        sniffer = csv.Sniffer()
        try:
            return sniffer.sniff(sample).delimiter
        except csv.Error:
            sys.stderr.write(f"Warning: Could not detect delimiter, using default '{default}'\n")
            return default

def main():
    """Main function to process the input file and find most distant label pairs."""
    
    # parse command line options
    options = Options(sys.argv)
    
    input_file = options["input"]
    output_file = options["output"]
    
    # Check file existence
    if not os.path.exists(input_file):
        sys.stderr.write(f"Error: File {input_file} not found.\n")
        return 1

    # Detect delimiter and read file
    if options["separator"]:
        delimiter = options["separator"]
    else:
        delimiter = detect_delimiter(input_file)
        sys.stderr.write(f"Using delimiter: {delimiter}\n")

    try:
        df = pd.read_csv(input_file, sep=delimiter, engine='python')
    except Exception as e:
        sys.stderr.write(f"Error reading CSV: {e}\n")
        return 1

    # Rename for consistency
    df = df.rename(columns={
        'ID': 'label_ID',
        'Transcript': 'label_v',
        'Cluster_ID': 'group_ID'
    })

    # Check required columns
    required_columns = {'label_ID', 'label_v', 'group_ID'}
    if not required_columns.issubset(df.columns):
        sys.stderr.write(f"Missing columns: {required_columns - set(df.columns)}\n")
        return 1

    # Drop missing values
    df = df.dropna(subset=required_columns)

    # Group by cluster
    grouped = df.groupby('group_ID')
    output_rows = []

    for cluster_id, group in grouped:
        labels = list(zip(group['label_ID'], group['label_v']))

        if len(labels) == 1:
            # Only one label in cluster
            output_rows.append({
                'Cluster ID': cluster_id,
                'Label 1 ID': labels[0][0],
                'Label 1 Transcript': labels[0][1],
                'Label 2 ID': '',
                'Label 2 Transcript': '',
                'Distance': ''
            })
        else:
            # Find the pair with maximum Levenshtein distance
            max_distance = -1
            most_distant_pair = None

            for i in range(len(labels)):
                for j in range(i + 1, len(labels)):
                    dist = levenshtein(labels[i][1], labels[j][1])
                    if dist > max_distance:
                        max_distance = dist
                        most_distant_pair = (
                            labels[i][0], labels[i][1],
                            labels[j][0], labels[j][1]
                        )

            output_rows.append({
                'Cluster ID': cluster_id,
                'Label 1 ID': most_distant_pair[0],
                'Label 1 Transcript': most_distant_pair[1],
                'Label 2 ID': most_distant_pair[2],
                'Label 2 Transcript': most_distant_pair[3],
                'Distance': max_distance
            })

    # Save output
    output_df = pd.DataFrame(output_rows)
    try:
        output_df.to_csv(output_file, index=False)
        sys.stderr.write(f"Output saved to: {output_file}\n")
    except Exception as e:
        sys.stderr.write(f"Error saving output: {e}\n")
        return 1
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
