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
            score = line[j]
            try:
                matched_ce[label_ID].append((ce_ID, score))
            except KeyError:
                matched_ce[label_ID] = (ce_ID, score)
    return matched_ce

def get_best_matched_ce(matched_ce):
    return dict( sorted(matched_ce[label_ID], lambda x: x[1])[-1]
                  for label_ID in matched_ce )

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
    read_matched_ce = read_matched_ce(matched_ce_fname)
    
    # compute probability of label group to represent a given collecting event
    # - each collecting event is given a score related to its proportion in the 
    #   group
    ## best match
    ## ..
    
    # 
    
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

