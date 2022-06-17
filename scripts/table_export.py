#!/usr/bin/env python3

'''
USAGE
    table_export.py [OPTION] FILE

DESCRIPTION
    Make a TSV file from a JSON file containing a label or a collecting
    event database.

OPTIONS
    --help
        Display this message

'''

import getopt, sys, fileinput, json

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
    sys.argv[1:] = options.args
    
    # organize the main job...
    for line in fileinput.input():
        pass
    
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

