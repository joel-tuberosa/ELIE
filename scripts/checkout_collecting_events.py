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
            best_match, score = ("unassigned", 0)
        try:
            ce_by_group[group_ID].append((best_match, score))
        except KeyError:
            ce_by_group[group_ID] = [(best_match, score)]
    return ce_by_group

def get_group_best_ce(ce_by_group):
    best_ce_by_group = dict()
    for group_ID in ce_by_group:
        ce_IDs, scores = zip(*ce_by_group[group_ID])
        n = len(ce_IDs)
        prop = [ ce_IDs.count(ce_ID)/n for ce_ID in ce_IDs ]
        best_prop = max(prop)
        best_i = prop.index(best_prop)
        best_ce, best_score = ce_by_group[group_ID][best_i]
        confidence = best_prop*best_score
        best_ce_by_group[group_ID] = (best_ce, confidence)
    return best_ce_by_group
        
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
    
    # for each group, find the most frequent CE and calculate a confidence
    # level
    ce_by_group = list_ce_by_groups(sorted_labels, best_matches)
    best_ce_by_group = get_group_best_ce(ce_by_group)

    # output the result
    sys.stdout.write("group.ID\tce.ID\tconfidence\n")
    for group_ID in sorted(best_ce_by_group.keys()):
        ce_ID, confidence = best_ce_by_group[group_ID]
        sys.stdout.write(f"{group_ID}\t{ce_ID}\t{confidence:.03f}\n")
    
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

