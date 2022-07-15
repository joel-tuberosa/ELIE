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
    
OPTIONS
    -c, --collector=FILE
        Attempt to identifiy collector names from the provided FILE, in 
        the labels.
        
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
    
    -p, --parse-and-sort
        Instead of performing text search to aggregate similar labels 
        together, parse information first, then aggregate labels with
        the same parsed information.

    -q, --consensus-quorum=INT
        Apply the consensus method only if the number of label in the 
        analyzed cluster is greater than the provided value. Default=2.

    -r, --refine
        Use the K-medoids method, based on pairwise Levenshtein 
        distances, to find clusters within groups.
    
    -s, --min-score=FLOAT
        Minimum similarity score for two label to be put in the same 
        group.
    
    -v, --consensus=METHOD
        Instead of parsing each label, build a consensus from the label
        cluster and parse it to retrieve information that will apply to
        all labels of the cluster. Verbatim information is lost with
        this option but the processing is faster.

        Possible METHOD values:
            
            "alignment" Perform an alignment with MAFFT, then build a 
                        consensus string from the most frequent 
                        character at each position. Requires MAFFT to
                        be installed.

            "pick"      Pick the text that has the lowest median 
                        pairwise distance with other texts of the 
                        cluster.

        Default is "pick".

    --help
        Display this message
'''

import getopt, sys, json, fileinput, regex
import mfnb.date, mfnb.labeldata, mfnb.geo, mfnb.name, mfnb.utils
import numpy as np
from io import StringIO
from random import randrange
from functools import partial

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:], 
                                       "c:df:gm:rs:v:qp", 
                                       ['collector=', 'date', 'id-format=', 
                                        'geo', 'min-length=', 'min-score=', 
                                        'refine', 'consensus=', 'parse-and-sort=',
                                        'consensus-quorum=', 'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)

        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-c', '--collector'):
                self["collector"] = a
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
            elif o in ('-v', '--consensus'):
                self["consensus"] = read_consensus(a)
            elif o in ('-q', '--consensus-quorum'):
                self["quorum"] = int(a)
            elif o in ('-p', '--parse-and-sort'):
                self["sort_by"] = "parsed_info"

        self.args = args

    def set_default(self):
    
        # default parameter value
        self["collector"] = None
        self['date'] = False
        self["id_formatter"] = mfnb.utils.get_id_formatter("label:5")
        self["geo"] = False   
        self["min_word_length"] = 3
        self["min_score"] = 0.8
        self["refine"] = False
        self["consensus"] = None
        self["quorum"] = 2
        self["sort_by"] = "text_similarity"

def read_consensus(a):
    a = mfnb.utils.simplify_str(a)
    if mfnb.name.fullname_match(a, "alignment"):
        return "alignment"
    elif mfnb.name.fullname_match(a, "pick"):
        return "pick"
    else:
        raise ValueError(f"unrecognized consensus method: {repr(a)}")

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

def parse_geo(text, username=mfnb.geo.GEONAMES_USERNAME):
    '''
    Tries to identify a geolocalization in the input text and returns
    the matched string, the span of the matched string and the 
    interpreted value.
    '''
    
    latlng, address, span = mfnb.geo.parse_geo(text, username)
    if span is None:
        return ("", -1, "")
    matched_str = text[slice(*span)]
    geostr = f"{address} ({latlng})"
    return (matched_str, span, geostr)

def parse_names(text, collectors):
    '''
    Tries to identify names in the input text and returns the matched
    string, the span of the matched string and the intepreted value.
    '''
    
    names, spans, scores = zip(*mfnb.name.find_collectors(text, collectors))
    if not names:
        return [("", -1, "")]
    results = []
    for name, span, score in zip(names, spans, scores):
        matched_str = text[slice(*span)]
        namestr = name.format("{q} {N}")
        results.append((matched_str, span, namestr))
    return results

def refine(labels, dist=None, get_median_dist=False):
    '''
    Identify K-medoids within a group of labels. Does not do anything
    if there are less than 4 elements.

    Parameters
    ----------
        labels : list
            A Label DB or a list of Label objects, whose text attribute
            A list of Label object, whose text attribute will be 
            will be compared.

        dist : NDarray
            A symetrical pairwise distance matrix that will be used for
            the clustering instead of calculating one from the provided
            labels.

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
    if dist is None:
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

def parse_info(text, geo=False, date=False, collectors=[]):
    '''
    Parse information from the provided text.
    '''

    # parsed and interpreted information
    found_info = {
        "geo": {
            "verbatim": "",
            "interpreted": ""
            },
        "date": {
            "verbatim": "",
            "interpreted": ""
            }, 
        "collectors": {
            "verbatim": "",
            "interpreted": ""
            }
        } 
    
    # text segment breaks
    segments = []
    
    # parse the text to retrieve date information, then remove
    # the intepreted text.
    if date:
        verbatim, span, interpreted = parse_date(text)
        if span != -1: text = mfnb.utils.clear_text(text, span)
        found_info["date"]["verbatim"] = verbatim
        found_info["date"]["interpreted"] = interpreted
        if span != -1:
            segments += list(span)
    
    # parse the text to retrieve the collector name
    if collectors:
        interpreted = []
        verbatim = []
        hits = mfnb.name.find_collectors(text, collectors)
        for collector, span, score in hits:
            interpreted.append(collector.text)
            verbatim.append(text[slice(*span)])
            text = mfnb.utils.clear_text(text, span)
        interpreted = ", ".join(interpreted)
        verbatim = "|".join(verbatim)
        found_info["collectors"]["verbatim"] = verbatim
        found_info["collectors"]["interpreted"] = interpreted
        
    # parse the text to retrieve geolocalization information,
    # then remove the intepreted text.
    if geo:
        verbatim, span, interpreted = parse_geo(text)
        if span != -1: text = mfnb.utils.clear_text(text, span)
        found_info["geo"]["verbatim"] = verbatim
        found_info["geo"]["interpreted"] = interpreted
        if span != -1:
            segments += list(span)
    
    return found_info

def get_interpreted_data(found_info):
    '''
    Returns a tuple containing intepreted parsed data contained in the 
    result of the parse_info function.
    '''

    return tuple( found_info[field]["interpreted"] 
                   for field in ("date", "collectors", "geo") )
        
def format_result_line(label, group_id, found_info, 
                       fields=("geo", "date", "collectors")):

    line = f'{label.ID}\t{repr(label.text)}\t{group_id}'
    for field in fields:
        if found_info[field]["interpreted"]:
            line += (f'\t{found_info[field]["verbatim"]}'
                     f'\t{found_info[field]["interpreted"]}')
    return line + "\n"

def sort_by_text_similarity(db, parse_info, format_result_line, consensus=None,
                            min_score=0.8, refine_clustering=False, 
                            id_formatter=mfnb.utils.get_id_formatter("label:5"),
                            quorum=2):
    '''
    Aggregate labels by text similarity, then parse information within 
    label groups.
    '''
    
    # consensus method to be used
    if consensus == "alignment":
        consensus = True
        get_consensus = mfnb.utils.text_alignment_consensus
    elif consensus == "pick":
        consensus = True
        get_consensus = mfnb.utils.text_pick_consensus
    else:
        consensus = False

    # label to be classified
    to_be_sorted = [ label.ID for label in db ]

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
                     if score >= min_score ]
        matches.append(seed_label)
        
        # find K-medoids within the matched labels
        if refine_clustering:
            clusters = refine(matches)
        else:
            clusters = [matches]
        
        # print the result
        for cluster in clusters:
            i += 1
            group_id = id_formatter(i)

            # if the consensus option is selected and the cluster reaches the 
            # quorum, information is parsed within the consensus text instead
            # of within each individual label
            if consensus and len(cluster) >= quorum:
                text = get_consensus([ label.text for label in cluster ], 
                                     simplify=True)
                found_info = parse_info(text)
            else:
                found_info = None

            for label in cluster:
                
                # parse info from individual label if needed
                if found_info is None:
                    found_info = parse_info(label.text)
                
                # write label info
                result_line = format_result_line(label, group_id, found_info)
                sys.stdout.write(result_line)
            
        # remove matched IDs from the list of elements to be sorted
        match_ids = { label.ID for label in matches }
        to_be_sorted = [ ID 
                          for ID in to_be_sorted 
                          if ID not in match_ids ]

def sort_by_parsed_info(db, parse_info, format_result_line, 
                        id_formatter=mfnb.utils.get_id_formatter("label:5")):

    # store group_ids in a dictionnary, whose keys are parsed information data
    group_ids = dict()
    for label in db:
        found_info = parse_info(label.text)
        interpeted_data = get_interpreted_data(found_info)

        # try to get an existing group_id (identical parsed information was 
        # already identified in another label), otherwise create a new group.
        try:
            group_id = group_ids[interpeted_data]
        except KeyError:
            group_id = id_formatter(len(group_ids))
            group_ids[interpeted_data] = group_id

        # format the result line and print it, this results in an output where
        # label not ordered by group.
        result_line = format_result_line(label, group_id, found_info)
        sys.stdout.write(result_line)

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
    if options["collector"] is not None:
        with open(options["collector"]) as f:
            collectors = mfnb.name.load_collectors(f)
    else:
        collectors = []

    # parser function
    global parse_info
    parse_info = partial(parse_info, 
                         geo=options["geo"], 
                         date=options["date"],
                         collectors=collectors)

    # result line formatter function
    fields = []
    if options["geo"]:
        fields.append("geo")
    if options["date"]:
        fields.append("date")
    if collectors:
        fields.append("collectors")
    global format_result_line
    format_result_line = partial(format_result_line,
                                 fields=fields)

    # write the header
    header = "label.ID\tlabel.v\tgroup.ID"
    for option in ["geo", "date", "collector"]:
        if options[option]: header += f"\t{option}.v\t{option}.i"
    header += "\n"
    sys.stdout.write(header)
    
    # sort by using text similarity, then parse info
    if options["sort_by"] == "text_similarity":
        sort_by_text_similarity(db, parse_info, format_result_line, 
                                consensus=options["consensus"], 
                                min_score=options["min_score"],
                                refine_clustering=options["refine"], 
                                id_formatter=options["id_formatter"],
                                quorum=options["quorum"])

    # parse info within label, then aggregate labels containing the same info
    elif options["sort_by"] == "parsed_info":
        sort_by_parsed_info(db, parse_info, format_result_line, 
                            id_formatter=options["id_formatter"])

    # returns 0 if everything succeeded
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
