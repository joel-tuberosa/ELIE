
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

def search_collectors(s, collectors, mismatch_rule=mismatch_rule):
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
            results.append((collector, my.span(), 0, x))
    results.sort(key=lambda x: (x[2], x[3]), reverse=True)

    return [ (collector, span, s)
             if first_name_matched 
             else (collector, span, s*0.9) 
              for collector, span, first_name_matched, s in results ]

def find_collectors(s, collectors, mismatch_rules=mismatch_rule):
    '''
    Search collector names in the input string and return the highest scoring 
    and non-overlapping matches. 
    '''

    # aggregate overlapping matches, always keep the highest scoring match
    results = []
    matches = search_collectors(s, collectors, mismatch_rules)
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

def abbreviation_search(query, target):
    '''
    Tokenize the query and the target, then try to match a similar 
    token sequence with the same starts.
    '''

    query_tokens = regexp_tokenize(query.lower(), "\w+")
    target_tokens = regexp_tokenize(target.lower(), "\w+")
    start, i = -1, 0
    for j in range(len(target_tokens)):
        if abbreviation_match(query_tokens[i], target_tokens[j]):
            if start == -1: start = j
            i += 1
        else:
            start = -1
            i = 0
        if i == len(query_tokens): break
    if i == len(query_tokens) and start > -1:
        p = regex.compile(r"\W+".join(target_tokens[start:start+i]), regex.I)
        m = p.search(strip_accents(target))
        if m is None:
            raise AssertionError("Problem while retrieving the original text")
        return target[slice(*m.span())]
    else:
        return None

def abbreviation_match(query, target):
    '''
    Return True if the query is contains the first letters of the
    target.
    '''

    query, target = simplify_str(query), simplify_str(target)
    query = query.rstrip(".")
    if not query: return False
    try:
        return all( query[i] == target[i] for i in range(len(query)) )
    except IndexError:
        return False
    
