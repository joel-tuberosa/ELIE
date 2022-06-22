
'''
    This module contains classes and functions designed to recognize 
    and store people names information. It uses the third-party 
    packages nltk and regex.
'''

import regex, json
from mfnb.utils import mismatch_rule, overlap, simplify_str, strip_accents
from nltk import regexp_tokenize

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------
class Collector(object):
    '''
    Store the name of a collector or an entity.
    '''

    def __init__(self, ID, name, firstname="", metadata={}):
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
            {q}     first letter(s) of the first name(s), with dots
            {F}     full first name
            {N}     full last name
        '''
        
        if self.firstname is None:
            F = f = q = ""
        else:
            f = abbreviate_name(self.firstname)
            q = abbreviate_name(self.firstname, dots=True)
            F = self.firstname
        return format.format(f=f,
                             q=q,
                             F=F,
                             N=self.name)
    
    def all_formats(self):
        '''
        Returns a list of the names in all possible formats along with 
        the corresponding format expression.
        '''

        # surname only
        formats = [(self.formats(r"{N}"), r"{N}")]

        # first name + surname
        if self.firstname is not None:
            formats += [ (self.formats(" ".join(format)), " ".join(format))
                          for firstname in [r"{f}", r"{q}", r"{F}"]
                          for format in ([firstname, r"{N}"],
                                         [r"{N}", firstname]) ]
        return formats

    def export(self):
        '''
        Export object data to a dictionnary object.
        '''

        return dict(**self._data)

    def to_json(self):
        '''
        Dump object data in JSON format
        '''

        json.dumps(self.export(), ensure_ascii=False, indent=4)

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

def search_collectors_regex(s, collectors, mismatch_rule=mismatch_rule):
    '''
    Parse the input string s to identify any name from the provided 
    list of Collector object.
    '''

    # try to find surname only
    surname_matches = []
    for collector in collectors:
        name_regex = r"\b" + collector.name + r"\b"
        name = collector.name
        p = regex.compile(name_regex + mismatch_rule(name), 
                          regex.BESTMATCH | regex.V1)
        m = p.search(s)
        if m is not None:
            mismatches = sum(m.fuzzy_counts)
            score = (len(name)-mismatches)/len(name)
            surname_matches.append((m, collector, len(name)*score))
    
    # try to identify the full names
    fullname_matches = []
    for m, collector, score in surname_matches:
        matches = []
        for name, format in collector.all_formats():
            name_regex = r"\b" + name.replace(".", r"\.") + r"\b"
            p = regex.compile(name_regex + mismatch_rule(name), 
                              regex.BESTMATCH | regex.V1)
            m = p.search(s)
            if m is not None:
                mismatches = sum(m.fuzzy_counts)
                score = (len(name)-mismatches)/len(name)
                matches.append((m, score*len(name)))
        
        # record the best match
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            fullname_matches.append(matches[0])
        else:
            fullname_matches.append((None, 0))
    
    # summarise the result
    results = []
    for (mx, collector, x), (my, y) in zip(surname_matches, fullname_matches):
        first_name_matched = y > 0
        if first_name_matched:    
            results.append((collector, my.span(), 1, y))
        else:
            results.append((collector, mx.span(), 0, x))
    results.sort(key=lambda x: (x[2], x[3]), reverse=True)

    return [ (collector, span, score)
             if first_name_matched 
             else (collector, span, score*0.9) 
              for collector, span, first_name_matched, score in results ]

def search_collectors_abbr(s, collectors):
    results = []
    for collector in collectors:
        for format in collector.all_formats():
            hit, span = abbreviation_search(format, s, get_span=True)
            if hit is None:
                continue
            else:
                results.append(hit, span, 1)
    return results

def default_search_method_selector(collector):
    try:
        if collector.metadata["entity_type"] == "person":
            return search_collectors_regex
        else:
            return search_collectors_abbr
    except KeyError:
        return search_collectors_regex

def search_collectors(s, collectors,
                      search_rule=default_search_method_selector):

    # sort collectors with different search methods
    searches = dict()
    for collector in collectors:
        try:
            searches[search_rule(collector)].append(collector)
        except KeyError:
            searches[search_rule(collector)] = [collector]
    
    # perform searches on the different subset, with the attributed methods
    results = []
    for search_function in searches:
        collectors = searches[search_function]
        results += search_function(s, collectors)
    return results

def find_collectors(s, collectors,
                    search_rule=default_search_method_selector):
    '''
    Search collector names in the input string and return the highest scoring 
    and non-overlapping matches. 
    '''

    # aggregate overlapping matches, always keep the highest scoring match
    results = []
    matches = search_collectors(s, collectors, search_rule)
    sorted_matches = sorted(matches, key=lambda x: x[1])
    results.append(sorted_matches[0])
    for collector, span, score in sorted_matches[1:]:
        group_span = results[-1][1]
        item = (collector, span, score)
        if overlap(group_span, span) and score > results[-1][2]:
            results[-1] = item
        else:
            results.append(item)
    return results

def load_collectors(f):
    '''
    Import a list of collector from a collector database in JSON format.
    '''

    return [ Collector(**data) for data in json.load(f) ]

def fullname_search(abbreviation, target, get_span=False):
    '''
    Tokenize the abbreviation and the target, then try to match a
    similar token sequence with the same starts.
    '''

    abbreviation_tokens = regexp_tokenize(abbreviation.lower(), "\w+")
    target_tokens = regexp_tokenize(target.lower(), "\w+")
    start, i = -1, 0
    for j in range(len(target_tokens)):
        if fullname_match(abbreviation_tokens[i], target_tokens[j]):
            if start == -1: start = j
            i += 1
        else:
            start = -1
            i = 0
        if i == len(abbreviation_tokens): break
    if i == len(abbreviation_tokens) and start > -1:
        p = regex.compile(r"\W+".join(target_tokens[start:start+i]), regex.I)
        m = p.search(strip_accents(target))
        if m is None:
            raise AssertionError("Problem while retrieving the original text")
        hit = target[slice(*m.span())]
        return (hit, m.span()) if get_span else hit
    else:
        return (None, None) if get_span else None

def fullname_match(abbreviation, target):
    '''
    Return True if the provided string is an abbreviation of the
    target, namely, having matching first letters with optional dots.
    '''

    abbreviation, target = simplify_str(abbreviation), simplify_str(target)
    abbreviation = abbreviation.rstrip(".")
    if not abbreviation: return False
    try:
        return all( abbreviation[i] == target[i] 
                     for i in range(len(abbreviation)) )
    except IndexError:
        return False

def abbreviation_search(fullname, target, get_span=False):
    '''
    Search abbreviation in the target string that could correspond to
    the query text.
    '''

    fullname_tokens = regexp_tokenize(fullname.lower(), "\w+")
    target_tokens = regexp_tokenize(target.lower(), "\w+")
    start, i = -1, 0
    for j in range(len(target_tokens)):
        if fullname_match(target_tokens[j], fullname_tokens[i]):
            if start == -1: start = j
            i += 1
        else:
            start = -1
            i = 0
        if i == len(fullname_tokens): break  
    if i == len(fullname_tokens) and start > -1:
        p = regex.compile(r"\W+".join(target_tokens[start:start+i]), regex.I)
        m = p.search(strip_accents(target))
        if m is None:
            raise AssertionError("Problem while retrieving the original text")
        hit = target[slice(*m.span())]
        return (hit, m.span()) if get_span else hit
    else:
        return (None, None) if get_span else None

def read_metadata(s):
    '''
    Interpret a metada string, returns a dictionnary object. Metadata 
    string are formatted as such:

    key1="value"[; key2="value"...]

    - key1[, key2...] must be compatible with python variable syntax.
    - "value" will be interpreted as str, by stripping the double 
      quotes.
    - key-value pairs must separated by ";".
    - keys and values must be linked by an "=". 
    - keys must be unique.
    '''
    
    # data are contained in a dict object
    metadata = dict() 

    # key-value pair regular expression
    p = regex.compile(r"""
            # key
            (?P<key>[A-z_]\w*)
            # equal
            (?:\s*=\s*)
            # value
            (?P<value>(?P<quote>['"])(?P<string>.*?)(?<!\\)(?P=quote))
            """, regex.X)

    # parse key-value pairs
    for item in s.split(";"):
        item = item.strip()
        if not item: continue
        m = p.search(item)
        if m is None:
            raise ValueError(f"Invalid key-value pair syntax: {repr(item)}")
        key = m.group("key")
        value = m.group("value")
        quote = m.group("quote")
        metadata[key] = value.strip(quote)
    return metadata
