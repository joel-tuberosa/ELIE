#!/usr/bin/env python3

'''
USAGE
    sort_labels.py [OPTION] [FILE...]

DESCRIPTION
    Cluster label based on text similarity and parse localisation, date
    and collector's names in the raw text. Attribute unique identifier 
    to discovered groups.

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
    
    -s, --min-score=FLOAT
        Minimum similarity score for two label to be put in the same 
        group.
    
    --help
        Display this message

'''

import getopt, sys, json, fileinput, regex
import mfnb.date, mfnb.labeldata, mfnb.geo, mfnb.name
from mfnb.utils import get_id_formatter, clear_text, tokenize, get_text_segments, get_ngrams
from io import StringIO
from random import randrange

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:], 
                                       "cdf:gm:s:", 
                                       ['collector', 'date', 'id-format=', 
                                        'geo', 'min-length=', 'min-score=', 
                                        'collector-db=', 'help'])
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
                self["id_formatter"] = get_id_formatter(a)
            elif o in ('-g', '--geo'):
                self["geo"] = True
            elif o in ('-m', '--min-length'):
                self["min_word_length"] = int(a)
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
        self["id_formatter"] = get_id_formatter("label:5")
        self["geo"] = False   
        self["min_word_length"] = 3
        self["min_score"] = 0.8
        
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
    i = 1
    
    # write the header
    header = "label.ID\tlabel.v\tgroup.ID"
    for option in ["geo", "date", "collector"]:
        if options[option]: header += f"\t{option}.v\t{option}.i"
    header += "\n"
    sys.stdout.write(header)
    
    # remove newlines from text
    p = regex.compile("\n\r?")
    #remove_newlines = lambda x: p.sub(" // ", x)
    
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
        
        # print the result
        group_id = options["id_formatter"](i)
        for label in matches:
            
            ### labels within group could be classified with a neighbor 
            ### joining algorithm or using the vectorizer
            
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
                if span != -1: text = clear_text(text, span)
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
                if span != -1: text = clear_text(text, span)
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
                for text_segment in get_text_segments(text, sorted(segments)):
                    seg_l = len(text_segment)
                    text_segment = text_segment.strip()
                    if not text_segment: continue
                    verbatim, span, interpreted = parse_name(text_segment, collector_db, 0.75)
                    if span != -1:
                        span = (start+span[0], start+span[1])
                        hits.append((verbatim, span, interpreted, len(interpreted)))
                    start += seg_l
                if hits:
                    hits.sort(key = lambda x: x[3], reverse=True)
                    verbatim, span, interpreted, _ = hits[0]
                else:
                    verbatim, span, interpreted = "", -1, ""
                if span != -1: text = clear_text(text, span)
                collector_cols = f'\t{repr(verbatim)}\t{interpreted}'
                if span == -1:
                    found_info["collector"] = False
                else:
                    found_info["collector"] = True
            else:
                collector_cols = ""
                        
            # write label info
            sys.stdout.write(f'{label_cols}{geo_cols}{date_cols}{collector_cols}\n')
        
        # remove matched IDs from the list of elements to be sorted
        match_ids = { label.ID for label in matches }
        to_be_sorted = [ ID 
                          for ID in to_be_sorted 
                          if ID not in match_ids ]
        i += 1
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
