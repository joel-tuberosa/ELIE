
'''
    This module contains classes and functions designed to recognize 
    and store people names information. It uses the third-party 
    packages nltk and regex.
'''

import regex
from nltk import regexp_tokenize
from mfnb.utils import strip_accents

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------
class NamePatterns(object):
    '''
    A collection of regular expression patterns and rules to identify people
    name in text.
    '''
    
    # Names can be abbreviated, composed names use an hyphen or spaces, dots 
    # can indicate abbreviations.
    patterns = {
        'abbr-dots'     :   r"(?:[[\w]--[0-9_]]\.)(?:[-\s][[\w]--[0-9_]]\.)*",
        'abbr-nodots'   :   r"(?:[[\w]--[0-9_]])(?:[-\s][[\w]--[0-9_]])*",
        'full'          :   r"(?:[[\w]--[0-9_]][[\w']--[0-9_]]+)(?:[-\s][[\w]--[0-9_]][[\w']--[0-9_]]+)*"}
    
    # W. Weise, A. Prick
    # firstnames are abbreviated, surname not, different entity separated by 
    # comma or ampersand, firstnames before surnames
    # -> one name: {abbr-dots}\s+{full} or {abbr-nodots}\s+{full}
    
    # Wilfried Weise, Albert Prick or Weise Wilfried, etc.
    # same as the above or the other way around, but names not abbreviated
    # -> one name: {full}
    
    possible_formats = r'''
    \b{abbr}\s+{full}
    \b{full},?\s+{abbr}
    \b{full}
    '''.split()
    
    def __init__(self):
        '''
        Compile regular expression patterns.
        '''
        
        self._data = []
        for name_format in self.possible_formats:
            for abbr in ("abbr-dots", "abbr-nodots"):
                p = name_format.format(abbr=self.patterns[abbr], 
                                       full=self.patterns["full"])
                structure = regex.findall("abbr|full", name_format)
                if "abbr" in structure:
                    structure[structure.index("abbr")] = abbr
                self._data.append({"pattern": regex.compile(p, regex.V1),
                                   "format": structure})
    
    def get_patterns(self, formats=None):
        return [ (x["pattern"], x["format"]) 
                  for x in self._data 
                  if formats is None or x["format"] in formats ] 
    
    def get_pattern(self, f):
        for x in self._data:
            if x["format"] == f:
                return x["pattern"]
        raise ValueError(f"Unknown format: {f}")
    
    def search(self, value, formats=None):
        hits = []
        for p, f in self.get_patterns(formats):
            m = p.search(value)
            if m is None: continue
            score = 1 if f == ["abbr"] else 2
            l = len(m.group())
            hits.append(m, score, l)
        hits.sort(keys=lambda x: (x[1], x[2]), reverse=True)
        return hits

def validate_names(names, db, thresh=0):
    result = []
    for name in names:
        hits = db.search(name)
        if hits:
            match, score = hits[0]
            if score >= thresh:
                result.append((match.text, score))
    return result

def find_names(s, get_span=True, formats=None, db=None, thresh=0):
    '''
    Comma or ampersand characters are interpreted as separators for several 
    names. If single
    '''
    
    # find possible separators for multiple names
    parser = NamePatterns()
    hits = []
    
    # *score is 0-1 for each name found. If no DB is provided, the score is 
    #  always 1 for each name, otherwise it reflect the hit relevance.
    # *l is the number of characters in the identified text
    for p, f in parser.get_patterns():
        score = 0
        
        # try without separator
        m = p.search(s)
        if m is None: continue
        names = [m.group()]
        
        # validation with existing names
        if db is not None:
            names_scores = validate_names(names, db, thresh)
            if not names_scores: continue
            names = []
            for name, x in names_scores:
                names.append(name)
                score += x**2 ### rapid decrease of score
        else:
            score = 1
        l = len(names[0])
        hits.append((names, m.span(), l*score))
        
        # try with separators
        for sep in (",", "&"):
            score = 0
            fullp = regex.compile(fr"(?:{p.pattern})(?:\s*{sep}\s*{p.pattern}\s*)+", regex.V1)
            m = fullp.search(s)
            if m is None: continue
            names = p.findall(s[slice(*m.span())])
            
            # validation with existing names
            if db is not None:
                names_scores = validate_names(names, db, thresh)
                names = []
                for name, x in names_scores:
                    names.append(name)
                    score += x**2
            else:
                score = len(names)
            l = sum( len(x) for x in names )
            hits.append((names, m.span(), l*score))
    
    # no-hit result
    if not hits: 
        return ([], None) if get_span else []

    # sort by number of retrieved names
    hits.sort(key=lambda x: x[2], reverse=True)
    
    # return the best hit
    if get_span:
        return hits[0][0], hits[0][1]
    else:
        return hits[0][0]
