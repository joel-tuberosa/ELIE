#!/usr/bin/env python3

'''
USAGE
    search_labels.py [OPTION] QUERY DB

DESCRIPTION
    Load a label database (DB, a JSON formatted file), and search items 
    matching the QUERY text. Hits are displayed with an accuracy score 
    that is caculated according to the selected method (see option 
    --method).

OPTIONS

    -l, --min-length=INT
        Set up the minimum number of characters of a token to be used
        in the search. Default: 3
    
    -m, --method=METHOD
        Provide with the search method to use.

            (1) (Default) Every exactly matched token adds 1 unit to 
            the scoring The scoring is calculated as the expected 
            amount of units in case of a perfect match, divided by the
            actual amounts of units.

            (2) Similar as method 1, but units are weighted according
            to their relative TF-IDF score.

    -r, --raw
        Do not interpret \\n and \\t in the input string.

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

    -t, --threshold=SCORE
        Set the minimum score value for a hit to be displayed in the 
        output.

    --help
        Display this message
'''


import sys, getopt, fileinput
from elieclustering.labeldata import load_labels
from elieclustering.utils import clean_str

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "l:m:rs:t:",
                                       ['min-length=', 
                                        'method=',
                                        'raw',
                                        'scoring=',
                                        'threshold=',
                                        'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)
        
        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-l', '--min-length'):
                self["min_len"] = int(a)
            elif o in ('-m', '--method'):
                self["method"] = int(a)
            elif o in ('-r', '--raw'):
                self["raw"] = True
            elif o in ('-s', '--scoring'):
                self["scoring"] = a
            elif o in ('-t', '--threshold'):
                self["threshold"] = float(a)

        self.args = args
        
    def set_default(self):
    
        # default parameter value
        self["min_len"] = 3
        self["method"] = 1
        self["raw"] = False
        self["scoring"] = "w"
        self["threshold"] = 0

def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    query = options.args.pop(0)
    db_filename = options.args.pop(0)
    sys.argv[1:] = options.args
    
    # Load the collecting event DB
    with open(db_filename) as f:
        db = load_labels(f)
    
    # build the DB index
    db.make_index(method=options["method"], 
                  min_len=options["min_len"], 
                  keys=["text"])
    
    # output header
    sys.stdout.write("hit\tscore\n")

    # interpret \n and \t characters in the input string
    if not options["raw"]:
        query = clean_str(query)

    for x, score in db.search(query, scoring=options["scoring"]):
        if score >= options["threshold"]:
            sys.stdout.write(f"{x.ID}\t{score:.3f}\n")
        
    return 0
    
if __name__ == "__main__":
    sys.exit(main())