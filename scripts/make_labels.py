#!/usr/bin/env python3

'''
USAGE
    make_labels.py [OPTION] [FILE...]

DESCRIPTION
    Build label objects from an input table and store the data in a 
    JSON file.
   
OPTIONS
        
    -i, --id=COL
        Indicate which column contains the identifier. Default = 1

    -f, --id-format=FORMAT
        Each collecting event is given an identifier value (under the 
        key "ID"). This option allows to define the format of this 
        value.
        
        The FORMAT is written <prefix>:<n>
    
            <prefix>    any str
            <n>         a positive integer giving the number of digits  
        
        Overrides option -i.
        
    -h, --header
        The input data contains a header line that is to be ignored.

    -s, --separator=STR
        Set the field separator to read the table. Default = TAB
    
    -t, --text=COL
        Indicate which column contain the label text. Default = 2
    
    --googlevision
        If this option is set, extract label text from  Google Vision 
        output. With this option, the default ID is written 
        label<5-digit code>.
    
    --dir=DIR
        Read all files in DIR and concatenate the information in a 
        single output. Works with --googlevision
    
    --help
        Display this message

'''

import getopt, sys, fileinput, json, os
from mfnb.utils import table_to_dicts, range_reader, get_id_formatter
from mfnb.labeldata import data_from_googlvision
from io import StringIO

class Options(dict):

    def __init__(self, argv):
        
        # set default
        self.set_default()
        
        # handle options with getopt
        try:
            opts, args = getopt.getopt(argv[1:],
                                       "i:f:hs:t:", 
                                       ['id=', 'header',
                                        'separator=', 'text=',
                                        'id-format=', 'googlevision',
                                        'dir=', 'help'])
        except getopt.GetoptError as e:
            sys.stderr.write(str(e) + '\n' + __doc__)
            sys.exit(1)

        for o, a in opts:
            if o == '--help':
                sys.stdout.write(__doc__)
                sys.exit(0)
            elif o in ('-i', '--id'):
                self["id"] = int(a)-1
            elif o in ('-f', '--id-format'):
                self["id_formatter"] = get_id_formatter(a)
            elif o in ('-h', '--header'):
                self["header"] = True
            elif o in ('-s', '--separator'):
                self["separator"] = a
            elif o in ('-t', '--text'):
                self["text"] = int(a)-1
            elif o == '--googlevision':
                self["googlevision"] = True
            elif o == '--dir':
                self["dir"] = a
        
        if self["googlevision"] and self["id_formatter"] is None:
            self["id_formatter"] = get_id_formatter("label:5")
        if self["id_formatter"] is not None:
            self["id"] = None
        
        self.args = args
    
    def set_default(self):
    
        # default parameter value
        self["id"] = 0
        self["header"] = True
        self["separator"] = "\t"
        self["text"] = 1
        self["id_formatter"] = None
        self["googlevision"] = False
        self["dir"] = None

def main(argv=sys.argv):
    
    # read options and remove options strings from argv (avoid option 
    # names and arguments to be handled as file names by
    # fileinput.input().
    options = Options(argv)
    sys.argv[1:] = options.args
    
    # organize the main job...
    if options["googlevision"]:
        data_list = []
        if options["dir"] is None:
            f = StringIO("".join( line for line in fileinput.input() ))
            data_list += data_from_googlvision(f, options["id_formatter"])
        else:
            for fname in os.listdir(options["dir"]):
                path = os.path.join(options["dir"], fname)
                with open(path) as f:
                    data_list += data_from_googlvision(f, 
                                                       options["id_formatter"], 
                                                       start=len(data_list)+1)
                    
    else:
        data_list = table_to_dicts(fileinput.input(), 
                                    skip_first=options["header"],
                                    sep=options["separator"],
                                    identifier=options["id_formatter"],
                                    ID=options["id"],
                                    text=options["text"])
    
    json.dump(data_list, sys.stdout, ensure_ascii=False, indent=4)
        
    # return 0 if everything succeeded
    return 0

# does not execute main if the script is imported as a module
if __name__ == '__main__': sys.exit(main())

