#!/usr/bin/env python3

'''
USAGE
    sort_labels.py [OPTION] [FILE...]

DESCRIPTION
    Cluster label based on text similarity and parse localisation, date
    and collector's names in the raw text. Attribute unique identifier 
    to discovered groups.
    
    Clustering
    ----------
    
    By default, the clustering is performed by the following iterative 
    process:
        1) Pick a random label from the collection of unsorted label
           (seed label).
        2) Find every label for which the similarity value calculated 
           with the seed label is greater than the provided threshold 
           (customizable with option -s).
        3) Store all matched labels in a group and removed them from
           the collection of unsorted labels.
        4) Stop if the unsorted label collection is empty, otherwise
           go back to step 1.
    
    With option -r, the sorted groups are subclustered using the
    K-medoids method based on pairwise Levenshtein distance. To avoid 
    overclustering, it is therefore advised to use a low similarity 
    threshold value when using this protocol.
    
    Parsing
    -------
    
    Options -c, -d and -g activate text parsing to identify expected 
    information within the label, such as collector names, dates or
    geographical localisation.
    
    /!\ still under development /!\ 

OPTIONS
    -c, --collector
        Try to identify the Collector name.
        
    --collector-db=FILE
        Search putative name in the FILE.
        
    -d, --date
        Try to identify a date pattern.
        
    -f, --id-format=FORMAT
        Define the format of the identifiers attributed to each group 
        of labels.
        
        The FORMAT is written <prefix>:<n>
    
            <prefix>    any str
            <n>         a positive integer giving the number of digits      
   
    -g, --geo
        Try to identify a geolocalization.
    
    -m, --min-length=INT
        Minimum word length to be included in the search index. 
        Default = 3.
    
    -r, --refine
        Use the K-medoids method, based on pairwise Levenshtein 
        distances, to find clusters within groups.
    
    -s, --min-score=FLOAT
        Minimum similarity score for two label to be put in the same 
        group.
    
    --help
        Display this message
'''

import getopt, sys, json, fileinput, regex
import mfnb.date, mfnb.labeldata, mfnb.geo, mfnb.name, mfnb.utils
import numpy as np
from io import StringIO
from random import randrange

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:], 
                                       "cdf:gm:rs:", 
                                       ['collector', 'date', 'id-format=', 
                                        'geo', 'min-length=', 'min-score=', 
                                        'collector-db=', 'refine', 'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)

        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-c', '--collector'):
                self["collector"] = True
            elif o == '--collector-db':
                self["collector_db"] = a
            elif o in ('-d', '--date'):
                self["date"] = True
            elif o in ('-f', '--id-format'):
                self["id_formatter"] = mfnb.utils.get_id_formatter(a)
            elif o in ('-g', '--geo'):
                self["geo"] = True
            elif o in ('-m', '--min-length'):
                self["min_word_length"] = int(a)
            elif o in ('-r', '--refine'):
                self["refine"] = True
            elif o in ('-s', '--min-score'):
                self["min_score"] = float(a)
                
        self.args = args
        if self["collector"] and self["collector_db"] is None:
            raise ValueError("Please locate the collector DB with the" 
                             " --collector-db option if you want to parse the"
                             " input text to find collector names.")
    
    def set_default(self):
    
        # default parameter value
        self["collector"] = False
        self["collector_db"] = None
        self['date'] = False
        self["id_formatter"] = mfnb.utils.get_id_formatter("label:5")
        self["geo"] = False   
        self["min_word_length"] = 3
        self["min_score"] = 0.8
        self["refine"] = False
        
def parse_date(text):
    '''
    Tries to identify a date in the input text and returns the matched 
    string, the span of the matched string and the interpreted value.
    '''
    
    date, span = mfnb.date.find_date(text)
    if span is None:
        return ("", -1, "")
    matched_str = text[slice(*span)]
    datestr = date.get_isoformat()
    return (matched_str, span, datestr)

def parse_geo(text):
    '''
    Tries to identify a geolocalization in the input text and returns
    the matched string, the span of the matched string and the 
    interpreted value.
    '''
    
    latlng, span = mfnb.geo.find_lat_lng_str(text)            
    if span is None:
        return ("", -1, "")
    matched_str = text[slice(*span)]
    geostr = str(latlng)
    return (matched_str, span, geostr)

def parse_name(text, db=None, allow_unknown=False, thresh=0):
    '''
    Tries to identify names in the input text and returns the matched
    string, the span of the matched string and the intepreted value.
    '''
    
    names, span = mfnb.name.find_names(text, db=db, thresh=thresh)
    if span is None:
        return ("", -1, "")
    matched_str = text[slice(*span)]
    namestr = " & ".join(names)
    return (matched_str, span, namestr)

def refine(labels, get_median_dist=False):
    '''
    Identify K-medoids within a group of labels. Does not do anything
    if there are less than 4 elements.

    Parameters
    ----------
        labels : list
            A Label DB or a list of Label objects, whose text attribute
            A list of Label object, whose text attribute will be 
            will be compared.

        get_median_dist : bool
            Output each label along with its median distance with 
            other labels in the same cluster.
    '''

    # list input
    labels = [ label for label in labels ]

    # extract text
    lines = [ label.text for label in labels ]
    n = len(lines)

    # calculates the pairwise distance matrix
    dist = mfnb.utils.get_pairwise_leven_dist(lines, simplify=True)

    # does not attempt anything for less than 8 elements
    if n < 8:

        # get median distance for each point
        if get_median_dist:
            margin_medians = mfnb.utils.get_median_dists(dist)
            labels = list(zip(labels, margin_medians))
        return [labels]
        
    # the maximum number of cluster to evaluate is 20, or the number of
    # elements divided by 2.
    elif n < 20:
        max_cluster = n//2
    else:
        max_cluster = 20
    
    # attempt to optimise clustering using the knee selection method on the SSE 
    # values
    kmedoids = mfnb.utils.find_levenKMedoids(dist, max_cluster=max_cluster)
    
    # if the cluster identification failed with this method, do not cluster
    if kmedoids is None:
        
        # get median distance for each point
        if get_median_dist:
            margin_medians = mfnb.utils.get_median_dists(dist)
            labels = list(zip(labels, margin_medians))
        return [labels]
    
    # otherwise returns a list of clusters (which are lists of sorted items)
    clusters = dict()
    index_map = dict()
    for cluster_index, label_index in zip(kmedoids.labels_, range(len(labels))):
        label = labels[label_index]
        try:
            clusters[cluster_index].append(label)
            index_map[cluster_index].append(label_index)
        except KeyError:
            clusters[cluster_index] = [label]
            index_map[cluster_index] = [label_index]
    
    # calculate median distances within each subcluster
    if get_median_dist:
        for cluster_index in index_map:
            indexes = np.array(index_map[cluster_index])
            rows, cols = indexes[:,None], indexes[None,:]
            subdist = dist[rows, cols]
            subdist_median = mfnb.utils.get_median_dists(subdist)
            clusters[cluster_index] = list(zip(clusters[cluster_index], 
                                               subdist_median))

    # return a list of lists containing labels from the same cluster
    return list(clusters.values())

def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    sys.argv[1:] = options.args
    
    # load label data
    f = StringIO("".join( line for line in fileinput.input() ))
    db = mfnb.labeldata.load_labels(f)
    
    # build the index
    min_len = options["min_word_length"]
    db.make_index(method=2, min_len=min_len)
    
    # index the collector DB if required
    if options["collector_db"]:
        with open(options["collector_db"]) as f:
            collector_db = mfnb.labeldata.LabelDB(
                [ mfnb.labeldata.Label(**d) 
                   for d in json.load(f) ])
        collector_db.make_index(method=1, min_len=1)
                                          
    # label to be classified
    to_be_sorted = [ label.ID for label in db ]
    
    # write the header
    header = "label.ID\tlabel.v\tgroup.ID"
    for option in ["geo", "date", "collector"]:
        if options[option]: header += f"\t{option}.v\t{option}.i"
    header += "\n"
    sys.stdout.write(header)
    
    # remove newlines from text
    p = regex.compile("\n\r?")
    #remove_newlines = lambda x: p.sub(" // ", x)
    
    # label group number
    i = 0
    
    # Successively, sample a label, finds matching labels in the database, 
    # attribute these labels to a group and remove these labels from the labels
    # to be sorted
    while to_be_sorted:
        seed_id = to_be_sorted.pop(randrange(len(to_be_sorted)))
        seed_label = db.get(seed_id)
        seed_text = seed_label.text
        filtering = lambda x: x.ID in to_be_sorted
        matches = [ label 
                     for label, score in db.search(seed_text, 
                                                   filtering=filtering) 
                     if score >= options["min_score"] ]
        matches.append(seed_label)
        
        # find K-medoids within the matched labels
        if options["refine"]:
            clusters = refine(matches)
        else:
            clusters = [matches]
        
        # print the result
        for cluster in clusters:
            i += 1
            group_id = options["id_formatter"](i)
            for label in cluster:
                
                # the text is clean up from the matched patterns
                text = label.text
            
                # output table fields containing label info
                label_cols = f'{label.ID}\t{repr(label.text)}\t{group_id}'
                
                # check list of parsed and retrieved information
                found_info = {"geo": False, "date": False, "collector": False} 
                
                # text segment breaks
                segments = []
                
                # parse the text to retrieve geolocalization information,
                # then remove the intepreted text.
                span = None
                if options["geo"]:
                    verbatim, span, interpreted = parse_geo(text)
                    if span != -1: text = mfnb.utils.clear_text(text, span)
                    geo_cols = f'\t{repr(verbatim)}\t{interpreted}'
                    if span == -1:
                        found_info["geo"] = False
                    else:
                        found_info["geo"] = True
                        segments += list(span)
                else:
                    geo_cols = ""
                
                # parse the text to retrieve date information, then remove
                # the intepreted text.
                if options["date"]:
                    verbatim, span, interpreted = parse_date(text)
                    if span != -1: text = mfnb.utils.clear_text(text, span)
                    date_cols = f'\t{repr(verbatim)}\t{interpreted}'
                    if span == -1:
                        found_info["date"] = False
                    else:
                        found_info["date"] = True
                        segments += list(span)
                else:
                    date_cols = ""
                
                # parse the text to retrieve the collector name
                if options["collector"]:
                    hits = []
                    start = 0
                    text_segments = mfnb.utils.get_text_segments(
                        text, sorted(segments))
                    for text_segment in text_segments:
                        seg_l = len(text_segment)
                        text_segment = text_segment.strip()
                        if not text_segment: continue
                        verbatim, span, interpreted = parse_name(
                            text_segment, collector_db, 0.75)
                        if span != -1:
                            span = (start+span[0], start+span[1])
                            hits.append((verbatim, 
                                         span,
                                         interpreted, 
                                         len(interpreted)))
                        start += seg_l
                    if hits:
                        hits.sort(key = lambda x: x[3], reverse=True)
                        verbatim, span, interpreted, _ = hits[0]
                    else:
                        verbatim, span, interpreted = "", -1, ""
                    if span != -1: text = mfnb.utils.clear_text(text, span)
                    collector_cols = f'\t{repr(verbatim)}\t{interpreted}'
                    if span == -1:
                        found_info["collector"] = False
                    else:
                        found_info["collector"] = True
                else:
                    collector_cols = ""
                            
                # write label info
                sys.stdout.write(f'{label_cols}'
                                 f'{geo_cols}'
                                 f'{date_cols}'
                                 f'{collector_cols}\n')
            
        # remove matched IDs from the list of elements to be sorted
        match_ids = { label.ID for label in matches }
        to_be_sorted = [ ID 
                          for ID in to_be_sorted 
                          if ID not in match_ids ]
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
