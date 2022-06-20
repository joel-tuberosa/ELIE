
'''
    This module contains classes and functions designed to recognize 
    and store people names information. It uses the third-party 
    packages nltk and regex.
'''

from tkinter.ttk import Separator
import regex
from mfnb.utils import mismatch_rule

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------
class Collector(object):
    '''
    Store the name of a collector or an entity.
    '''

    def __init__(self, ID, name, firstname="", **metadata):
        self._data = {
            "ID": ID,
            "name": name,
            "firstname": firstname,
            "metadata": metadata
        }

    @property
    def ID(self):
        return self._data["ID"]

    @property
    def name(self):
        return self._data["name"]

    @property
    def firstname(self):
        if self._data["firstname"]:
            return self._data["firstname"]
        else:
            return None

    @property
    def text(self):
        return self.formats("{F} {N}")

    def formats(self, format):
        '''
        Write the name in the desired format. Format specification:
            {f}     first letter(s) of the first name(s)
            {f}.    first letter(s) of the first name(s), with dots
            {F}     full first name
            {N}     full last name
        '''
        
        format = format.replace(r"{f}.", r"{q}")
        if self.firstname is None:
            f = q = ""
        else:
            f = abbreviate_name(self.firstname)
            q = abbreviate_name(self.firstname, dots=True)
        return format.format(f=f,
                             q=q,
                             F=self.firstname,
                             N=self.name)
    
    def all_formats(self):
        '''
        Returns a list of the names in all possible formats.
        '''

        # surname only
        formats = [self.formats(r"{N}")]

        # first name + surname
        if self.firstname is not None:
            formats += [ self.formats(" ".join(format))
                          for firstname in [r"{f}", r"{q}", r"{F}"]
                          for format in ([firstname, r"{N}"],
                                         [r"{N}", firstname]) ]
        return formats

def abbreviate_name(s, dots=False):
    '''
    Returns the first letter of each element of the input name. 
    '''

    sep = regex.compile(r"(?P<ws>\s+)|(?P<dash>-)")
    s = s.strip()
    m = sep.search(s)
    names = ""
    dot = "." if dots else ""
    span = (None, 0)
    while m is not None:
        if m.group("ws") is not None:
            sep_char = " "
        else:
            sep_char = "-"
        names += s[span[1]:span[1]+1].upper() + dot + sep_char
        span = m.span()
        m = sep.search(s, span[1])
    names += s[span[1]:span[1]+1].upper() + dot
    return names

def search_collectors(s, collectors, mismatch_rule=mismatch_rule):
    '''
    Parse the input string s to identify any name from the provided 
    list of Collector object.
    '''

    # try to find surname only
    surname_matches = []
    for collector in collectors:
        p = regex.compile(collector.name + mismatch_rule(collector.name), 
                          regex.V1)
        m = p.search(s)
        if m is not None:
            surname_matches.append(collector.ID)
    ### unfinished