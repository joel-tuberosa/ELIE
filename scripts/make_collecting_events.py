#!/usr/bin/env python3

'''
USAGE
    make_collecting_events.py [OPTION] [FILE...]

DESCRIPTION
    Build collecting event object from an input table and store the data 
    in a JSON file.

OPTIONS
    -c, --collector=COL
        Indicate which columns contains the name of the collector.
        Default = 3
        
    -d, --date=COL
        Indicate which column contains the date. Default = 1
    
    -f, --id-format=FORMAT
        Each collecting event is given an identifier value (under the 
        key "ID"). This option allows to define the format of this 
        value.
        
        The FORMAT is written <prefix>:<n>
    
            <prefix>    any str
            <n>         a positive integer giving the number of digits        
    
    -h, --header
        The input data contains a header line that is to be ignored.
    
    -i, --id=COL
        Indicate which column contains the identifiers. The default run 
        attributes newly created identifiers.
    
    -l, --location=COL[,...]
        Indicate which column(s) contain(s) the location information, 
        the different fields are separated by semi-columns in the
        final value. Default = 2

    -s, --separator=STR
        Set the field separator to read the table. Default = '\t'
    
    -v, --text=COL[,...]
        Indicate which column(s) contain(s) a reprensentative text 
        label transcript. Default = 4
    
    --help
        Display this message

'''

import getopt, sys, fileinput, json
from mfnb.utils import table_to_dicts, range_reader, get_id_formatter

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "c:d:f:hi:l:s:v:", 
                                       ['collector=', 'date=',
                                        'location=', 'header',
                                        'id=',
                                        'separator=', 'text=', 
                                        'id-format=', 'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)

        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-c', '--collector'):
                self["collector"] = int(a)-1
            elif o in ('-d', '--date'):
                self["date"] = int(a)-1
            elif o in ('-h', '--header'):
                self["header"] = True
            elif o in ('-f', '--id-format'):
                self["id_formatter"] = get_id_formatter(a)
            elif o in ('-l', '--location'):
                self["location"] = range_reader(a)
            elif o in ('-i', '--id'):
                self["ID"] = int(a)-1
            elif o in ('-s', '--separator'):
                self["separator"] = a
            elif o in ('-t', '--text'):
                self["text"] = int(a)-1
        
        self.args = args
        
        # if the ID column is provided, do not use the ID formatter
        if self["ID"] is not None:
            self["id_formatter"] = None
    
    def set_default(self):
    
        # default parameter value
        self["location"] = [0]
        self["date"] = 1
        self["header"] = True
        self["ID"] = None
        self["collector"] = 2
        self["separator"] = "\t"
        self["id_formatter"] = get_id_formatter("colev:5")
        self["text"] = 3
    
def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    sys.argv[1:] = options.args
    
    # set up the column parameters
    columns = dict( (key, options[key]) 
                     for key in ("location", "date", "collector", "text", "ID") 
                     if options[key] is not None )
    
    # extract the data from a table
    data_list = table_to_dicts(fileinput.input(), 
                                skip_first=options["header"],
                                sep=options["separator"],
                                data_sep=", ",
                                identifier=options["id_formatter"],
                                **columns)
    
    # save in a JSON formatted file
    json.dump(data_list, sys.stdout, ensure_ascii=False, indent=4)
        
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

