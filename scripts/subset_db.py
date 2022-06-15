#!/usr/bin/env python3

'''
USAGE
    subset_db.py [OPTION] DB [FILE...]

DESCRIPTION
    Subset a label or a collecting event database (DB) in JSON format 
    according to the input ID list.

OPTIONS
    --help
        Display this message

'''

import getopt, sys, fileinput, mfnb.labeldata

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
    
def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    db_fname = options.args.pop(0)
    sys.argv[1:] = options.args
    
    # load the database to subset
    with open(db_fname) as f:
        db = mfnb.labeldata.load_db(f)

    # load the IDs of the element to be kept
    id_list = [ line.strip() for line in fileinput.input() ]
    
    # subset the DB
    db = db.subset(lambda x: x.ID in id_list)

    # write the subset DB in stdout
    db.dump_db(sys.stdout)

    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

