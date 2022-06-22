#!/usr/bin/env python3

'''
USAGE
    make_collectordb.py [OPTION] [FILE...]

DESCRIPTION
    Make a collector database in JSON format from a TSV input. The 
    script will identify standard attribute names in the TSV header
    and fetch the corresponding values in each columns to build a 
    Collector object. Therefore, the input TSV file must at least
    contains the columns ID and name, which are mandatory to create
    the Collector object. 

OPTIONS
    --help
        Display this message

'''

import getopt, sys, fileinput, json
from multiprocessing.sharedctypes import Value
from mfnb.name import Collector, read_metadata

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

def locate_attributes(headerline):
    header = headerline.strip().split("\t")
    attributes = {
        "ID": -1,
        "name": -1,
        "firstname": -1,
        "metadata": -1
    }
    for i in range(len(header)):
        try:
            attributes[header[i]] = i
        except KeyError:
            raise AttributeError(f"{repr(header[i])} is not a valid attribute"
                                  " of the Collector class")
    
    # check mandatory attributes
    for key in ("ID", "name"):
        if attributes[key] == -1:
            raise ValueError(f"column {repr(key)} is missing")
    
    # remove unset attributes
    for key in ("firstname", "metadata"):
        if attributes[key] == -1:
            del attributes[key]
    
    return attributes

def read_collectors(f):
    '''
    Build collector instances from a TSV input
    '''

    attributes = None
    for line in fileinput.input():

        # interpret the first line as a header to locate the different columns
        if attributes is None:
            attributes = locate_attributes(line)
            continue
            
        # fetch attribute values from the corresponding columns
        fields = [ field.strip() for field in line.split("\t") ]
        data = dict( (key, fields[attributes[key]]) for key in attributes )
        
        # interpret the metadata string
        try:
            data["metadata"] = read_metadata(data["metadata"])
        except KeyError:
            data["metadata"] = {}

        # stream Collector instances built from the data
        yield Collector(**data)

def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    sys.argv[1:] = options.args
    
    # organize the main job...
    data = [ collector.export() 
              for collector in read_collectors(fileinput.input()) ]
    json.dump(data, 
              sys.stdout, 
              ensure_ascii=False, 
              indent=4)
    
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())
