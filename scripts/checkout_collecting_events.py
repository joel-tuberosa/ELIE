#!/usr/bin/env python3

'''
USAGE
    checkout_collecting_events.py [OPTION] SORTED MATCHES[...]

DESCRIPTION
    Identify inconsistensies between the outputs of sort_labels.py 
    (SORTED) and match_collecting_events.py (MATCHES) in order to 
    validate collecting event attributions. Several MATCHES files can
    be provided. 

OPTIONS
    -l, --log=FILE
        Write statistics in the provided FILE instead of stderr.

    --help
        Display this message

'''

import getopt, sys, fileinput
from tokenize import group
import numpy as np
from statistics import mean

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:], "l:", ['log=', 'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)

        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-l', '--log'):
                self["log"] = a

        self.args = args
    
    def set_default(self):
    
        # default parameter value
        self["log"] = None

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

def summarise_counts(d):
    '''
    Extract the mean and standard deviation of values extracted from 
    the input dict object.
    '''

    X = list(d.values())
    return dict(n=len(X),
                mean=np.mean(X), 
                sd=np.std(X))

def summarise_sorted_labels(sorted_labels):
    '''
    Get the mean and standard deviation of the number of labels per 
    cluster. 
    '''

    counts = dict()
    for label_ID in sorted_labels:
        group_ID = sorted_labels[label_ID]
        try:
            counts[group_ID] += 1
        except KeyError:
            counts[group_ID] = 1
    return summarise_counts(counts)

def read_matched_ce(*fnames):
    matched_ce = dict()
    for fname in fnames:
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

def summarise_ce_by_group(ce_by_group):
    '''
    Get the mean and standard deviation of the number of CE per 
    cluster, as well as the number of cluster per CE. 
    '''

    cluster_per_ce = dict()
    ce_per_cluster = dict()
    for group_ID in ce_by_group:
        for ce_ID, score in ce_by_group[group_ID]:
            try:
                cluster_per_ce[ce_ID] += 1
            except KeyError:
                cluster_per_ce[ce_ID] = 1
            try:
                ce_per_cluster[group_ID] += 1
            except KeyError:
                ce_per_cluster[group_ID] = 1
    return dict(cluster_per_ce=summarise_counts(cluster_per_ce),
                ce_per_cluster=summarise_counts(ce_per_cluster))

def statistics_log(sorted_labels, ce_by_group):
    '''
    Compute statistics about sorted labels and matched collecting 
    events and output a log.
    '''

    sorted_stat = summarise_sorted_labels(sorted_labels)
    matches_stat = summarise_ce_by_group(ce_by_group)
    
    return '''
    Sorted labels
    -------------
        number of clusters: {}
        mean (sd) label per cluster: {:.03f} ({:.03f})

    Matched collecting events (CE)
    ------------------------------
        number of matched CE: {}
        mean (sd) CE per cluster: {:.03f} ({:.03f})
        mean (sd) cluster per CE: {:.03f} ({:.03f})
    \n'''.format(sorted_stat["n"], 
                 sorted_stat["mean"], 
                 sorted_stat["sd"],
                 matches_stat["cluster_per_ce"]["n"], 
                 matches_stat["cluster_per_ce"]["mean"],
                 matches_stat["cluster_per_ce"]["sd"],
                 matches_stat["ce_per_cluster"]["mean"],
                 matches_stat["ce_per_cluster"]["sd"])

def get_group_best_ce(ce_by_group):
    best_ce_by_group = dict()
    for group_ID in ce_by_group:
        ce_IDs, scores = zip(*ce_by_group[group_ID])

        # calculate the proportion of each different collecting events
        # associated with the group and find the collecting event with
        # the highest proportion.
        n = len(ce_IDs)
        prop = sorted([ (ce_ID, ce_IDs.count(ce_ID)/n) 
                         for ce_ID in set(ce_IDs) ],
                      key=lambda x: x[1])
        best_ce, best_prop = prop[-1]

        # gather the hit score of all labels matching the best_ce and calculate
        # a mean score.
        mean_score = mean( scores[i] 
                            for i in range(len(ce_IDs))
                            if ce_IDs[i] == best_ce )
        confidence = best_prop*mean_score

        # for each group, save the best CE and the associated confidence score
        best_ce_by_group[group_ID] = (best_ce, confidence)
    return best_ce_by_group

def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    sys.argv[1:] = options.args

    # identify input files
    sorted_labels_fname = options.args[0]
    matched_ce_fnames = options.args[1:]
    
    # read the sorted label table (output from sort_labels.py)
    sorted_labels = read_sorted_labels(sorted_labels_fname)
    
    # read the matched collecting event table (output 
    # from match_collecting_events.py)
    matched_ce = read_matched_ce(*matched_ce_fnames)
    
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
    
    # log the statistics
    stat_log = statistics_log(sorted_labels, ce_by_group)
    if options["log"] is None:
        sys.stderr.write(stat_log)
    else:
        with open(options["log"]) as f:
            f.write(stat_log)

    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

