'''
This module contains classes and functions designed to store people 
names or entity information as well as matching abbreviated text with 
full text. It uses the packages nltk and regex.
'''

import regex, json
from elieclustering.utils import mismatch_rule, overlap, simplify_str, strip_accents
from nltk import regexp_tokenize
from functools import partial

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------
class Collector(object):
    '''
    Store the name of a collector or an entity.
    '''

    def __init__(self, ID, name, firstname="", metadata={}):
        '''
        Instanciate a Collector object by providing with attribute 
        data.

        Parameters
        ----------
            ID : str
                A unique identifier, for database registry.

            name : str
                The surname, or the name of the entity if not a 
                person.
            
            firstname : str
                For persons, the firstname, if known. Default = "".

            metadate : dict
                Any metadata to be attached to the collecting entity.
        '''
        
        # store internal data
        self._data = {
            "ID": ID,
            "name": name,
            "firstname": firstname,
            "metadata": metadata,
            "simplified_name": simplify_str(name),
            "simplified_firstname": simplify_str(firstname)
        }

    @property
    def ID(self):
        return self._data["ID"]

    @property
    def name(self):
        return self._data["name"]

    @property
    def simple_name(self):
        return self._data["simplified_name"]

    @property
    def firstname(self):
        if self._data["firstname"]:
            return self._data["firstname"]
        else:
            return None

    @property
    def simple_firstname(self):
        if self._data["simplified_firstname"]:
            return self._data["simplified_firstname"]
        else:
            return None

    @property
    def text(self):
        return self.formats("{F} {N}")

    def formats(self, format, lowercase=False, simplified_str=False):
        '''
        Write the name in the desired format. 
        
        Parameters
        ----------
            format : str
                Fields to be replaced by corresponding values in 
                specific formats.

                Format specification:
                {f}     first letter(s) of the first name(s)
                {q}     first letter(s) of the first name(s), with dots
                {F}     full first name
                {N}     full last name

            lowercase : bool
                Convert the values in lowercases. Default = False.

            simplified_str : bool
                Simplifies the output character string (remove accents, 
                convert to lowercase and replace consecutive white 
                spaces by single space characters). Default = False. 
        '''
        
        # preprocess fields
        if simplified_str:
            name, firstname = self.simple_name, self.simple_firstname
        elif lowercase:
            name, firstname = self.name.lower(), self.firstname.lower()
        else:
            name, firstname = self.name, self.firstname

        if firstname is None:
            F = f = q = ""
        else:
            f = abbreviate_name(firstname)
            q = abbreviate_name(firstname, dots=True)
            F = firstname
        text = format.format(f=f,
                             q=q,
                             F=F,
                             N=name).strip()
        return text
    
    def all_formats(self, lowercase=False, simplified_str=False):
        '''
        Returns a list of the names in all possible formats along with 
        the corresponding format expression.

        Parameters
        ----------
            lowercase : bool
                Convert the values in lowercases. Default = False.

            simplified_str : bool
                Simplifies the output character string (remove accents, 
                convert to lowercase and replace consecutive white 
                spaces by single space characters). Default = False. 
        '''

        # surname only
        formats = [(self.formats(r"{N}", lowercase=lowercase,
                                 simplified_str=simplified_str),
                    r"{N}")]

        # first name + surname
        if self.firstname is not None:
            formats += [ (self.formats(" ".join(format), 
                                       lowercase=lowercase,
                                       simplified_str=simplified_str), 
                          " ".join(format))
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

    def __repr__(self):
        return f'Collector({self.text})'

def abbreviate_name(s, dots=False):
    '''
    Returns the first letter of each element of the input name. 

    Parameters
    ----------
        s : str
            Any text.
        
        dots : bool
            If set True, adds a dot after each abbreviation letter.
            Default = False.
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

def search_collectors_regex(s, collectors, mismatch_rule=mismatch_rule, 
                            ignore_case=False, simplified_str=False):
    '''
    Parse the input string s to identify any name from the provided 
    list of Collector object.

    Parameters
    ----------
        s : str
            Any text.
        
        collectors : list
            A list of Collector objects.
        
        mismatch_rule : function
            A function that takes the query value as unique argument
            and returns the regular expression part parametring a fuzzy
            match. Default = mfnb.utils.mismatch_rule (see module doc).
    
        ignore_case : bool
            Sets the search method to ignore case. Default = False.

        simplify_str : bool
            Discard case and accents from the queries and the subject.
    '''
    
    # preprocess the target input
    if simplified_str:
        target = strip_accents(s).lower()
    elif ignore_case:
        target = s.lower()

    # try to find surname only
    surname_matches = []    
    for collector in collectors:
        if simplified_str:
            name = collector.simple_name
        else:
            name = collector.name
        name_regex = r"\b" + name + r"\b"
        p = regex.compile(name_regex + mismatch_rule(name), 
                          regex.BESTMATCH | regex.V1 | regex.M)
        m = p.search(target)
        if m is not None:
            mismatches = sum(m.fuzzy_counts)
            score = (len(name)-mismatches)/len(name)
            surname_matches.append((m, collector, len(name)*score))
    
    # try to identify the full names
    fullname_matches = []
    for m, collector, score in surname_matches:
        matches = []
        for name, format in collector.all_formats(ignore_case, simplified_str):
            name_regex = r"\b" + name.replace(".", r"\.") + r"\b"
            p = regex.compile(name_regex + mismatch_rule(name), 
                              regex.BESTMATCH | regex.V1 | regex.M)
            m = p.search(target)
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

def search_collectors_abbr(s, collectors, ignore_case=False,
                           simplified_str=False):
    '''
    Search the input text for abbreviations that match collector names 
    from the provided list.

    Parameters
    ----------
        s : Any text.

        collectors : list
            A list of Collector objects.
        
        ignore_case : bool
            Sets the search method to ignore case. Default = False.

        simplify_str : bool
            Discard case and accents from the queries and the subject.
    '''
    
    # preprocess the query
    if simplified_str:
        
        # do not use simplify_str function to preserve the query length
        s = strip_accents(s).lower()

    elif ignore_case:
        s = s.lower()

    results = []
    for collector in collectors:
        for name, format in collector.all_formats(ignore_case, simplified_str):
            hit, span = abbreviation_search(name, s, get_span=True)
            if hit is None:
                continue
            else:
                results.append((collector, span, 1))
    return results

default_search_methods = {
        "person": partial(search_collectors_regex, simplified_str=True),
        "other": partial(search_collectors_abbr, simplified_str=True)
        }

def default_search_method_selector(collector):
    '''
    Assign the default search method to a collector object according to
    the metadata entry "entity_type". This instructs to use pattern 
    search if the entity is a person and abbreviation search otherwise.
    '''
    
    global default_search_methods
    try:
        if collector.metadata["entity_type"] == "person":
            return default_search_methods["person"]
        else:
            return default_search_methods["entity"]
    except (AttributeError, KeyError):
        return default_search_methods["person"]

def search_collectors(s, collectors,
                      search_rule=default_search_method_selector):
    '''
    Searches individual occurences of collector's name in the input 
    text.

    Parameters
    ----------
        s : str
            Any text.
        
        collectors : list
            A list of Collector objects.
        
        search_rule : function
            A function that takes a collector object as argument and 
            return the search method to use. 
            Default = default_search_method_selector (uses pattern 
            search for people and abbreviation search for any other 
            kinds of entity).
    '''
    
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

    Parameters
    ----------
        s : str
            Any text.
        
        collectors : list
            A list of Collector objects.
        
        search_rule : function
            A function that takes a collector object as argument and 
            return the search method to use. 
            Default = default_search_method_selector (uses pattern 
            search for people and abbreviation search for any other 
            kinds of entity).
    '''

    # aggregate overlapping matches, always keep the highest scoring match
    results = []
    matches = search_collectors(s, collectors, search_rule)
    if not matches:
        return []
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

def fullname_search(abbreviation, target, get_span=False, ignore_case=False, 
                    simplified_str=False):
    '''
    Tokenize the abbreviation and the target, then try to match a
    similar token sequence with the same starts.

    Parameters
    ----------
        abbreviation : str
            Any text.

        target : str
            Any text.
        
        get_span : bool
            Returns the span of the match in the abbreviation text.
            Default = False.
        
        ignore_case : bool
            Sets the search method to ignore case. Default = False.

        simplify_str : bool
            Discard case and accents from the queries and the subject.
    '''

    abbreviation_tokens = regexp_tokenize(abbreviation.lower(), "\w+")
    target_tokens = regexp_tokenize(target.lower(), "\w+")
    start, i = -1, 0
    for j in range(len(target_tokens)):
        if fullname_match(abbreviation_tokens[i], target_tokens[j],
                          ignore_case=ignore_case, 
                          simplified_str=simplified_str):
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

def fullname_match(abbreviation, target, ignore_case=False, 
                   simplified_str=False):
    '''
    Return True if the provided string is an abbreviation of the
    target, namely, having matching first letters with optional dots.

    Parameters
    ----------
        abbreviation : str
            Any text.

        target : str
            Any text.
        
        ignore_case : bool
            Sets the search method to ignore case. Default = False.

        simplify_str : bool
            Discard case and accents from the queries and the subject.
    '''

    # pre-processes input strings
    if ignore_case:
        abbreviation, target = abbreviation.lower(), target.lower()
    if simplified_str:   
        abbreviation, target = simplify_str(abbreviation), simplify_str(target)
    abbreviation = abbreviation.rstrip(".")
    
    if not abbreviation: return False
    try:
        return all( abbreviation[i] == target[i] 
                     for i in range(len(abbreviation)) )
    except IndexError:
        return False

def abbreviation_search(fullname, target, get_span=False, ignore_case=False,
                        simplified_str=False):
    '''
    Search abbreviation in the target string that could correspond to
    the query text.

    Parameters
    ----------
        fullname : str
            Any text.

        target : str
            Any text.
        
        get_span : bool
            Returns the span of the match in the fullname text.
            Default = False.
        
        ignore_case : bool
            Sets the search method to ignore case. Default = False.

        simplify_str : bool
            Discard case and accents from the queries and the subject.
    '''

    # pre-processes input strings
    original_target = target
    if simplified_str:
        fullname, target = simplify_str(fullname), simplify_str(target)
    elif ignore_case:
        fullname, target = fullname.lower(), target.lower()

    fullname_tokens = regexp_tokenize(fullname, "\w+")
    target_tokens = regexp_tokenize(target, "\w+")
    
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
        if ignore_case:
            p = regex.compile(r"\W+".join(target_tokens[start:start+i]), regex.I)
        else:
            p = regex.compile(r"\W+".join(target_tokens[start:start+i]))
        if simplified_str:
            m = p.search(strip_accents(original_target))
        else:
            m = p.search(original_target)
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
