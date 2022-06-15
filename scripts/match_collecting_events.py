#!/usr/bin/env python3

'''
USAGE
    match_collecting_events.py [OPTION] DB [FILE...]

DESCRIPTION
    Load a collecting event database (a JSON formatted file), match
    label raw data to collecting events. Label data are contained in 
    one or several JSON files provided in input. The program iterates 
    on the content of the JSON file, in which single label data would
    be contained in a dict object with the keys "ID" and "text", 
    allowing to map an identifier value to the text content of each 
    label.
    
OPTIONS
    -d, --date-search
        Prior to the text search, identify a date in the label, then 
        limit the text search to collecting events with overlapping
        dates.

    -f, --text-fields=STR[,...]
        Limit text search in the collecting events to the provided 
        fields.

    -m, --method=METHOD
        Provide with the search method to use.

            (1) (Default) Every exactly matched token adds 1 unit to 
            the scoring The scoring is calculated as the expected 
            amount of units in case of a perfect match, divided by the
            actual amounts of units.

            (2) Similar as method 1, but units are weighted according
            to their relative TF-IDF score.

    -p, --persist
        If limited search was unsuccessful (i.e. limiting to collecting
        events with overlapping dates) search onto the whole database.

    -s, --scoring=METHOD
        Indicate how to calculate the hit scoring.

            (w) (Default) The score is calculated as the product of the
            rates of matching token in the query and in the subject, 
            then weighted accounting for mismatches and TF-IDF scores.

            (l) The score is calculated as the normalized Levenshtein 
            similarity between the query and the target. This 
            Levenshtein similarity is calculated on a simplified 
            version of the text, removing accents, case and treating 
            consecutive white spaces as single space characters.

            (w+l) Calculate the product of both scoring method.

    -u, --unmatched-logs
        Save unmatched items in a log files:
        
            __unmatched_labels.txt  Record of labels that did not match
                                    any collecting event.
                                    
            __unmatched_ce.txt      Record of collecting event that 
                                    were not matched by any label.

    -x, --no-text-search
        Do not perform text search.
    
    --help
        Display this message
'''


import sys, getopt, fileinput, regex, json
import mfnb.date, mfnb.labeldata, mfnb.utils
from math import log

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "di:f:m:pus:x", 
                                       ['date-search',
                                        'method=',
                                        'text-fields=',
                                        'persist',
                                        'scoring=',
                                        'no-text-search',
                                        'unmatched-logs',
                                        'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)
        
        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-d', '--date-search'):
                self['date_search'] = True
            elif o in ('-f', '--text-fields'):
                self["text_fields"] = a.split(",")
                notvalid = [ x 
                             for x in self["text_fields"] 
                             if x not in mfnb.labeldata.CollectingEvent.keys ]
                if notvalid:
                    notvalid = ', '.join( repr(x) for x in notvalid )
                    raise ValueError("The following keys are not valid:"
                                    f" {notvalid}.")
            elif o in ('-m', '--method'):
                self["method"] = int(a)
            elif o in ('-p', '--persist'):
                self["persist"] = True
            elif o in ('-s', '--scoring'):
                self["scoring"] = a
            elif o in ('-u', '--unmatched-logs'):
                self["unmatched_logs"] = True
            elif o in ('-x', '--no-text-search'):
                self["text_search"] = False
            
        if len(args) < 1:
            raise ValueError("Database file not provided.")
        self.args = args
    
    def set_default(self):
    
        # default parameter value
        self['date_search'] = False
        self["method"] = 1
        self["persist"] = False
        self["scoring"] = "w"
        self["text_fields"] = ["text"]
        self["text_search"] = True
        self["unmatched_logs"] = False
    
def write_results(fout, matches, query_fields=[], subject_fields=[], sep="\t", 
                  header=False):
    if header:
        query_field_names = sep.join(query_fields)
        subject_field_names = sep.join(subject_fields)
        fout.write(f"{query_field_names}"
                   f"\t{subject_field_names}"
                    "\tscore\n")
                   
    for label, hit, score in matches:
        query_field_values = sep.join( (repr(label[field])
                                         if field == "text"
                                         else label[field])
                                        if label[field] is not None else ""
                                        for field in query_fields )
        subject_field_values = sep.join( (repr(hit[field])
                                           if field == "text"
                                           else hit[field])
                                          if hit[field] is not None else ""
                                          for field in subject_fields )

        fout.write(f"{query_field_values}"
                   f"\t{subject_field_values}"
                   f"\t{score:.3f}\n")

def parse_labels(f):
    '''
    Parse labels from the input file.
    '''

    # each label is comprised within curly brackets, there are no nested
    # brackets
    s, on = "", False
    for line in f:
        start, end = line.find("{"), line.find("}")
        if start == -1:
            if on: 
                s += line[:end]
                if end > -1:
                    yield mfnb.labeldata.Label(**json.loads("{"+s+"}"))
                    s, on = "", False
            elif end > -1:
                raise ValueError("Input format error: nested curly brackets"
                                 " found")
        else:
            if on:
                raise ValueError("Input format error: nested curly brackets"
                                 " found")
            end = line.find("}")
            s += line[start+1:end]
            if end == -1:
                on = True
            else:
                yield mfnb.labeldata.Label(**json.loads("{"+s+"}"))
                s, on = "", False

def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    db_filename = options.args.pop(0)
    sys.argv[1:] = options.args

    # Load the collecting event DB
    with open(db_filename) as f:
        db = mfnb.labeldata.load_collecting_events(f)
    
    # build the token index with words found in location and collector data
    db.make_index(method=options["method"], 
                  min_len=3,
                  keys=options["text_fields"])
    
    # build the date index
    db.make_date_index()
        
    # print the header for the result table
    write_results(sys.stdout, [], 
                   ["label.ID", "label.text"], 
                   ["CE.ID", "CE.location", "CE.date", "CE.collector", 
                    "CE.text"],
                   header = True)
    
    # save unmatched labels and unmatched collecting events
    unmatched_ce = { ce.ID for ce in db }
    unmatched_labels = set()
    
    # read label text that is stored in one or several JSON input 
    # files
    for label in parse_labels(fileinput.input()):

        # search
        hits = []
        
        # - by date
        if options["date_search"]:
            date, _ = mfnb.date.find_date(label.text)
            if date is None:
                filtering = lambda ce: True
            else:
                hits = db.search_by_date(date, assume_same_century=True)
                ids = set( ce.ID for ce in hits )
                filtering = lambda ce: ce.ID in ids
        else:
            filtering = lambda ce: True
        
        # - by text
        if options["text_search"]:
            hits = db.search(label.text, 
                             mismatch_rule=mfnb.utils.mismatch_rule, 
                             filtering=filtering,
                             scoring=options["scoring"])

            # try on the whole database if --persist option was set
            if all((options["persist"], options["date_search"], 
                    date is not None, not hits)):
                hits = db.search(label.text, 
                                 mismatch_rule=mfnb.utils.mismatch_rule, 
                                 filtering=lambda ce: True,
                                 scoring=options["scoring"])
        
        # save labels that did not match any collecting events
        if not hits:
            unmatched_labels.add(label.ID)
        
        # remove matched collecting from the set of unmatched 
        # collecting events
        for ce, score in hits:
            try:
                unmatched_ce.remove(ce.ID)
            except KeyError:
                pass
        
        # print the result
        matches = ( (label.export(), ce.export(), score) 
                        for ce, score in hits )
        write_results(sys.stdout, matches, 
                        ["ID", "text"],
                        ["ID", "location", "date", "collector", "text"])
                
    # print the unmatched item log
    if options["unmatched_logs"]:
        with open("__unmatched_labels.txt", "w") as fout:
            fout.writelines( f"{ID}\n" for ID in unmatched_labels )
        with open("__unmatched_ce.txt", "w") as fout:
            fout.writelines( f"{ID}\n" for ID in unmatched_ce )
    else:
        sys.stderr.write("__unmatched_labels\n")
        sys.stderr.writelines( f"\t{ID}\n" for ID in unmatched_labels )
        sys.stderr.write("__unmatched_ce\n")        
        sys.stderr.writelines( f"\t{ID}\n" for ID in unmatched_ce )
        
    return 0
    
if __name__ == "__main__":
    sys.exit(main())
    