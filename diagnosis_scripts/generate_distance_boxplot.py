#!/usr/bin/env python3

'''
USAGE
    generate_distance_boxplot.py [OPTION]

DESCRIPTION
    Script 4/4: Generate Levenshtein distance boxplot visualization.
    This script creates boxplot visualizations of Levenshtein distances from cluster 
    validation data. It takes the output from script 3/4 and generates boxplots showing 
    the distribution of distances between different transcript types.

OPTIONS
    -i, --input=FILE
        Path to validation CSV file (output from script 3/4).
        
    -o, --output=FILE
        Path for boxplot image output (PNG format recommended).
        
    -c, --columns=STR
        Comma-separated list of Levenshtein columns to plot.
        Default = "L1 Manual vs L2 Manual Levenshtein"
        
    -t, --title=STR
        Custom title for the boxplot. Default = auto-generated
        
    -s, --separator=STR
        CSV separator character. Default = auto-detect
        
    --figure-size=STR
        Figure size as "width,height". Default = "10,8"
        
    --palette=STR
        Color palette for boxplot. Default = "Set2"
        
    --help
        Display this message

'''

import getopt, sys, csv, os, re
import numpy as np

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "i:o:c:t:s:", 
                                       ["input=", "output=", "columns=", "title=", "separator=", 
                                        "figure-size=", "palette=", "help"])
        except getopt.GetoptError as err:
            sys.stderr.write(f"Error: {err}\n")
            sys.exit(1)
        
        for opt, arg in opts:
            if opt in ("-i", "--input"):
                self["input"] = arg
            elif opt in ("-o", "--output"):
                self["output"] = arg
            elif opt in ("-c", "--columns"):
                self["columns"] = arg
            elif opt in ("-t", "--title"):
                self["title"] = arg
            elif opt in ("-s", "--separator"):
                self["separator"] = arg
            elif opt == "--figure-size":
                self["figure_size"] = arg
            elif opt == "--palette":
                self["palette"] = arg
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
        
        # set default title if not provided
        if not self["title"]:
            base_name = os.path.splitext(os.path.basename(self["input"]))[0]
            self["title"] = f"Levenshtein Distance Distributions - {base_name}"
        
        # store remaining arguments
        self["files"] = args

    def set_default(self):
        self["input"] = None
        self["output"] = None
        self["columns"] = "L1 Manual vs L2 Manual Levenshtein"
        self["title"] = None
        self["separator"] = None
        self["figure_size"] = "10,8"
        self["palette"] = "Set2"
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

def load_validation_data(file_path: str, delimiter: str) -> dict:
    '''
    Load validation results CSV file and return data as dictionary of lists.
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

def validate_columns(data: dict, requested_columns: list) -> list:
    '''
    Validate that requested columns exist in the data and return available ones.
    '''
    available_columns = list(data.keys())
    valid_columns = []
    missing_columns = []
    
    for col in requested_columns:
        if col in available_columns:
            valid_columns.append(col)
        else:
            missing_columns.append(col)
    
    if missing_columns:
        sys.stderr.write(f"Warning: Missing columns: {missing_columns}\n")
        sys.stderr.write(f"Available columns: {available_columns}\n")
    
    if not valid_columns:
        sys.stderr.write("Error: No valid columns found for plotting\n")
        return None
    
    return valid_columns

def extract_numeric_data(data: dict, columns: list) -> dict:
    '''
    Extract numeric data from specified columns, filtering out empty/invalid values.
    '''
    numeric_data = {}
    
    for col in columns:
        values = []
        for val in data[col]:
            if val and val.strip():  # Not empty
                try:
                    num_val = float(val)
                    if not np.isnan(num_val):
                        values.append(num_val)
                except (ValueError, TypeError):
                    continue  # Skip invalid values
        
        numeric_data[col] = values
        sys.stderr.write(f"Column '{col}': {len(values)} valid numeric values\n")
    
    return numeric_data

def calculate_boxplot_stats(values: list) -> dict:
    '''
    Calculate boxplot statistics (quartiles, median, outliers) for a list of values.
    '''
    if not values:
        return None
    
    values_array = np.array(sorted(values))
    
    stats = {
        'min': np.min(values_array),
        'q1': np.percentile(values_array, 25),
        'median': np.percentile(values_array, 50),
        'q3': np.percentile(values_array, 75),
        'max': np.max(values_array),
        'mean': np.mean(values_array),
        'std': np.std(values_array),
        'count': len(values_array)
    }
    
    # Calculate Interquartile Range and outliers
    iqr = stats['q3'] - stats['q1']
    lower_fence = stats['q1'] - 1.5 * iqr
    upper_fence = stats['q3'] + 1.5 * iqr
    
    outliers = [v for v in values_array if v < lower_fence or v > upper_fence]
    stats['outliers'] = outliers
    stats['num_outliers'] = len(outliers)
    
    return stats

def get_color_palette(palette_name: str, n_colors: int) -> list:
    '''
    Get a list of colors for the specified palette.
    '''
    palettes = {
        'Set2': ['#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854', '#ffd92f', '#e5c494', '#b3b3b3'],
        'Set1': ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00', '#ffff33', '#a65628', '#f781bf'],
        'Dark2': ['#1b9e77', '#d95f02', '#7570b3', '#e7298a', '#66a61e', '#e6ab02', '#a6761d', '#666666'],
        'Pastel1': ['#fbb4ae', '#b3cde3', '#ccebc5', '#decbe4', '#fed9a6', '#ffffcc', '#e5d8bd', '#fddaec'],
        'viridis': ['#440154', '#482777', '#3f4a8a', '#31678e', '#26838f', '#1f9d8a', '#6cce5a', '#b6de2b'],
        'plasma': ['#0d0887', '#6a00a8', '#b12a90', '#e16462', '#fca636', '#f0f921']
    }
    
    if palette_name in palettes:
        colors = palettes[palette_name]
        # Repeat colors if we need more than available
        return [colors[i % len(colors)] for i in range(n_colors)]
    else:
        # Default to grayscale
        return [f'#{int(255 - i * 255 / max(1, n_colors-1)):02x}' * 3 for i in range(n_colors)]

def create_boxplot_visualization(numeric_data: dict, output_path: str, title: str, 
                                figure_size: tuple, palette: str) -> bool:
    '''
    Create a boxplot visualization using matplotlib.
    '''
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as patches
        
        # Prepare data and colors
        columns = list(numeric_data.keys())
        colors = get_color_palette(palette, len(columns))
        
        # Calculate statistics for each column
        all_stats = {}
        for col in columns:
            stats = calculate_boxplot_stats(numeric_data[col])
            if stats:
                all_stats[col] = stats
        
        if not all_stats:
            sys.stderr.write("Error: No valid data for plotting\n")
            return False
        
        # Create figure and axis
        fig, ax = plt.subplots(figsize=figure_size)
        
        # Plot each boxplot
        positions = range(1, len(all_stats) + 1)
        box_width = 0.6
        
        for i, (col, stats) in enumerate(all_stats.items()):
            pos = positions[i]
            color = colors[i]
            
            # Draw box (IQR)
            box_height = stats['q3'] - stats['q1']
            box = patches.Rectangle(
                (pos - box_width/2, stats['q1']), 
                box_width, box_height,
                facecolor=color, edgecolor='black', alpha=0.7
            )
            ax.add_patch(box)
            
            # Draw median line
            ax.plot([pos - box_width/2, pos + box_width/2], 
                   [stats['median'], stats['median']], 
                   'k-', linewidth=2)
            
            # Draw whiskers
            whisker_bottom = max(stats['min'], stats['q1'] - 1.5 * (stats['q3'] - stats['q1']))
            whisker_top = min(stats['max'], stats['q3'] + 1.5 * (stats['q3'] - stats['q1']))
            
            # Lower whisker
            ax.plot([pos, pos], [stats['q1'], whisker_bottom], 'k-', linewidth=1)
            ax.plot([pos - box_width/4, pos + box_width/4], 
                   [whisker_bottom, whisker_bottom], 'k-', linewidth=1)
            
            # Upper whisker
            ax.plot([pos, pos], [stats['q3'], whisker_top], 'k-', linewidth=1)
            ax.plot([pos - box_width/4, pos + box_width/4], 
                   [whisker_top, whisker_top], 'k-', linewidth=1)
            
            # Plot outliers
            if stats['outliers']:
                outlier_positions = [pos] * len(stats['outliers'])
                ax.scatter(outlier_positions, stats['outliers'], 
                          c=color, marker='o', s=30, alpha=0.6, edgecolors='black')
        
        # Customize plot
        ax.set_title(title, fontsize=16, fontweight='bold', pad=20)
        ax.set_ylabel('Distance', fontsize=14, labelpad=15)
        
        # Set x-axis labels
        column_labels = [col.replace(' Levenshtein', '').replace(' vs ', '\nvs\n') for col in columns]
        ax.set_xticks(positions)
        ax.set_xticklabels(column_labels, fontsize=10, ha='center')
        
        # Add grid
        ax.grid(True, alpha=0.3, axis='y')
        ax.set_axisbelow(True)
        
        # Adjust layout
        plt.tight_layout(pad=4.0)
        if len(columns) > 1:
            plt.subplots_adjust(bottom=0.25)
        else:
            plt.subplots_adjust(bottom=0.15)
        
        # Create output directory if needed
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        # Save plot
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        sys.stderr.write(f"Boxplot saved to: {output_path}\n")
        return True
        
    except ImportError:
        sys.stderr.write("Warning: matplotlib not available, skipping boxplot generation\n")
        return False
    except Exception as e:
        sys.stderr.write(f"Error creating boxplot: {e}\n")
        return False

def print_statistics_summary(numeric_data: dict) -> None:
    '''
    Print a summary of statistics for each column.
    '''
    sys.stderr.write("\nData Statistics Summary:\n")
    sys.stderr.write("=" * 50 + "\n")
    
    for col, values in numeric_data.items():
        if values:
            stats = calculate_boxplot_stats(values)
            sys.stderr.write(f"\n{col}:\n")
            sys.stderr.write(f"  Count: {stats['count']}\n")
            sys.stderr.write(f"  Min: {stats['min']:.2f}\n")
            sys.stderr.write(f"  Q1: {stats['q1']:.2f}\n")
            sys.stderr.write(f"  Median: {stats['median']:.2f}\n")
            sys.stderr.write(f"  Q3: {stats['q3']:.2f}\n")
            sys.stderr.write(f"  Max: {stats['max']:.2f}\n")
            sys.stderr.write(f"  Mean: {stats['mean']:.2f}\n")
            sys.stderr.write(f"  Std Dev: {stats['std']:.2f}\n")
            sys.stderr.write(f"  Outliers: {stats['num_outliers']}\n")
        else:
            sys.stderr.write(f"\n{col}: No valid data\n")

def main():
    '''
    Main function to generate boxplot visualization of Levenshtein distances.
    '''
    
    # parse command line options
    options = Options(sys.argv)
    
    input_file = options["input"]
    output_file = options["output"]
    columns_str = options["columns"]
    title = options["title"]
    separator = options["separator"]
    figure_size_str = options["figure_size"]
    palette = options["palette"]
    
    sys.stderr.write("Script 4/4: Generate Levenshtein distance boxplot visualization\n")
    sys.stderr.write(f"Processing input file: {input_file}\n")
    sys.stderr.write(f"Boxplot will be saved to: {output_file}\n")
    
    # Parse columns to plot
    requested_columns = [col.strip() for col in columns_str.split(',')]
    sys.stderr.write(f"Requested columns: {requested_columns}\n")
    
    # Parse figure size
    try:
        width, height = map(float, figure_size_str.split(','))
        figure_size = (width, height)
    except ValueError:
        sys.stderr.write(f"Error: Invalid figure size format: {figure_size_str}. Use 'width,height'\n")
        return 1
    
    # Detect or use specified delimiter
    if separator:
        delimiter = separator
    else:
        delimiter = detect_delimiter(input_file)
        sys.stderr.write(f"Using delimiter '{delimiter}'\n")
    
    # Load validation data
    sys.stderr.write("Loading validation data...\n")
    data = load_validation_data(input_file, delimiter)
    if data is None:
        return 1
    
    # Validate columns
    valid_columns = validate_columns(data, requested_columns)
    if valid_columns is None:
        return 1
    
    # Extract numeric data
    sys.stderr.write("Extracting numeric data...\n")
    numeric_data = extract_numeric_data(data, valid_columns)
    
    # Check if we have any valid data
    has_data = any(len(values) > 0 for values in numeric_data.values())
    if not has_data:
        sys.stderr.write("Error: No valid numeric data found for plotting\n")
        return 1
    
    # Print statistics summary
    print_statistics_summary(numeric_data)
    
    # Create boxplot visualization
    sys.stderr.write("Generating boxplot...\n")
    if not create_boxplot_visualization(numeric_data, output_file, title, figure_size, palette):
        return 1
    
    # Report completion
    sys.stderr.write("Script 4/4 completed successfully!\n")
    sys.stderr.write(f"Boxplot saved to: {output_file}\n")
    sys.stderr.write(f"Visualized {len([col for col, values in numeric_data.items() if values])} distance metric(s)\n")
    
    # return 0 if everything succeeded
    return 0

if __name__ == "__main__":
    sys.exit(main())
