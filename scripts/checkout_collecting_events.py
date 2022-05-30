#!/usr/bin/env python3

'''
USAGE
    checkout_collecting_events.py [OPTION] SORTED MATCHES

DESCRIPTION
    Identify inconsistensies between the outputs of sort_labels.py 
    (SORTED) and match_collecting_events.py (MATCHES) in order to 
    validate collecting event attributions.

OPTIONS
    --help
        Display this message

'''

import getopt, sys, fileinput
from statistics import mean

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:], "", ['help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)

        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)

        self.args = args
    
    def set_default(self):
    
        # default parameter value
        pass

def read_sorted_labels(fname):
    sorted_labels = dict()
    with open(fname) as f:
        header = f.readline().strip().split("\t")
        i, j = header.index("label.ID"), header.index("group.ID")
        for line in f:
            line = line.strip().split("\t")
            label_ID, group_ID = line[i], line[j]
            sorted_labels[label_ID] = group_ID
    return sorted_labels

def read_matched_ce(fname):
    matched_ce = dict()
    with open(fname) as f:
        header = f.readline().strip().split("\t")
        i, j = header.index("label.ID"), header.index("CE.ID")
        k = header.index("score")
        for line in f:
            line = line.strip().split("\t")
            label_ID, ce_ID = line[i], line[j]
            score = float(line[k])
            try:
                matched_ce[label_ID].append((ce_ID, score))
            except KeyError:
                matched_ce[label_ID] = [(ce_ID, score)]
    return matched_ce

def get_best_matched_ce(matched_ce):
    return dict( (label_ID, sorted(matched_ce[label_ID], 
                                   key=lambda x: x[1])[-1])
                  for label_ID in matched_ce )

def list_ce_by_groups(sorted_labels, best_matches):
    ce_by_group = dict()
    
    # list best matched collecting event IDs found in each group
    for label_ID in sorted_labels:
        group_ID = sorted_labels[label_ID]
        try:
            best_match, score = best_matches[label_ID]
        except KeyError:
            #sys.stderr.write(f"the label {repr(label_ID)} do not match any"
            #                  " collecting event.\n")
            continue
        try:
            ce_by_group[group_ID].append((best_match, score))
        except KeyError:
            ce_by_group[group_ID] = [(best_match, score)]
    return ce_by_group
    
def get_tables(grouped_ce):
    ce_IDs, scores = zip(*grouped_ce)
    
    # mean scores
    score_table = dict()
    for ce_ID, score in grouped_ce:
        try: 
            score_table[ce_ID].append(score)
        except KeyError:
            score_table[ce_ID] = [score]
    mean_scores = dict( (ce_ID, mean(score_table[ce_ID]))
                        for ce_ID in score_table )
                        
    # frequencies
    freqs = dict( (x, ce_IDs.count(x)/len(ce_IDs)) for x in set(ce_IDs) )
    
    # table
    return [ (ce_ID, mean_scores[ce_ID], freqs[ce_ID]) 
              for ce_ID in mean_scores ]
        
def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    sys.argv[1:] = options.args
    sorted_labels_fname = options.args[0]
    matched_ce_fname = options.args[1]
    
    # read the sorted label table (output from sort_labels.py)
    sorted_labels = read_sorted_labels(sorted_labels_fname)
    
    # read the matched collecting event table (output 
    # from match_collecting_events.py)
    matched_ce = read_matched_ce(matched_ce_fname)
    
    # get best matches
    best_matches = get_best_matched_ce(matched_ce)
    
    # compute probability of label group to represent a given collecting event
    # - each collecting event is given a score related to its proportion in the 
    #   group
    sys.stdout.write("group.ID\tce.ID\tmean.score\tfreq\n")
    ce_by_group = list_ce_by_groups(sorted_labels, best_matches)
    for group_ID in ce_by_group:
        for ce_ID, mean_score, freq in get_tables(ce_by_group[group_ID]):
            sys.stdout.write(f"{group_ID}\t{ce_ID}\t{mean_score:.03f}\t{freq:.03f}\n")
    
    # - each group is given a score related to the proportions of matching 
    #   collecting events
    ## best match
    ## ..
    
    # 
    
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

