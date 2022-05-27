#!/usr/bin/env python3

'''
USAGE
    match_collecting_events.py [OPTION] DB FILE[...]

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
                                       "di:f:ux", 
                                       ['date-search',
                                        'text-fields=',
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
                allowed_keys = mfnb.labeldata.CollectingEvent.keys
                notvalid = [ x 
                             for x in self["text_fields"] 
                             if x not in mfnb.labeldata.CollectingEvent.keys ]
                if notvalid:
                    notvalid = ', '.join( repr(x) for x in notvalid )
                    raise ValueError("The following keys are not valid:"
                                    f" {notvalid}.")
            elif o in ('-u', '--unmatched-logs'):
                self["unmatched_logs"] = True
            elif o in ('-x', '--no-text-search'):
                self["text_search"] = False
            
        if len(args) < 2:
            raise ValueError("At least the database file and one input"
                             " file has to be provided.")
        self.args = args
    
    def set_default(self):
    
        # default parameter value
        self['date_search'] = False
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
    db.make_index(min_len=3, keys=options["text_fields"])
    
    # build the date index
    db.make_date_index()
    
    # make a date_parser
    date_parser = mfnb.date.DatePatterns()        
    
    # compile the URL pattern (only needed if option --clear-url was set
    url_pattern = regex.compile(r"(?:http://[/\w]){i<=2}")
    
    # display parameter
    sys.stderr.write(f'''
    Parameters
    ----------
        Search in:
            date    {"yes" if options["date_search"] else "no"}
            text    {"yes" if options["text_search"] else "no"}
        
        Collecting text fields:
            "{'", "'.join(options["text_fields"])}"
        
    ----------\n''')
    
    # print the header for the result table
    write_results(sys.stdout, [], 
                   ["label.ID", "label.text"], 
                   ["CE.ID", "CE.location", "CE.date", "CE.collector", 
                    "CE.text"],
                   header = True)
    
    # save unmatched labels and unmatched collecting events
    unmatched_ce = { ce.ID for ce in db }
    unmatched_labels = set()
    
    # read label text that is stored in a JSON input file
    while sys.argv[1:]:
        with open(sys.argv.pop(1)) as f:
            for label in mfnb.labeldata.load_labels(f):
                
                # search
                hits = []
                
                # - by date
                if options["date_search"] and date is not None:
                    hits = db.search_by_date(date, assume_same_century=True)
                    ids = set( ce.ID for ce in hits )
                    filtering = lambda ce: ce.ID in ids
                else:
                    filtering = lambda ce: True
                
                # - by text
                if options["text_search"]:
                    hits = db.search(label.text, 
                                     mismatch_rule=mfnb.utils.mismatch_rule, 
                                     filtering=filtering)
                
                # save labels that did not match any collecting events
                if not hits:
                    unmatched_labels.add(label.text)
                
                # remove matched collecting from the set of unmatched 
                # collecting events
                for ce, score in hits:
                    unmatched_ce.remove(ce.ID)
                
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
    