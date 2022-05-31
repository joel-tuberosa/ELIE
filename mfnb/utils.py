
'''
    This module gathers generic functions for text data handling, 
    manipulation and formatting.
'''

import regex
import unicodedata
import numpy as np
from kneed import KneeLocator
from math import log
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn_extra.cluster import KMedoids
from sklearn.metrics import silhouette_score
from leven import levenshtein
from nltk import regexp_tokenize, word_tokenize


# =============================================================================
# CONSTANTS
# -----------------------------------------------------------------------------
### allow 2-3 items in the URL
NURI_pattern = regex.compile(r"(?:http://(?:[\w\s.-]+/)+\s?[\w]+){s<=3}",
                             flags=regex.MULTILINE | regex.V1)

# =============================================================================
# FUNCTIONS
# -----------------------------------------------------------------------------
def mismatch_rule(s):
    '''
    Returns the regular expression part parametring a fuzzy match 
    according to length of the input string.
    '''

    if not s: return ""
    e = int(log(len(s), 2)) - 1
    if e < 1: return ""
    return "{e<=" + str(e) + "}"

def range_reader(s):
    '''
    Extract a list of 0-based index from a 1-based range expression. 
    Keep the provided order.
    '''
    
    r = []
    for x in s.split(","):
        if "-" in x:
            start, end = map(int, x.split("-"))
            if end >= start:
                r += list(range(start-1, end))
            else:
                r += list(range(start, end-1, -1))
        else:
            r.append(int(x)-1)
    return r


def table_to_dicts(f, skip_first=False, sep="\t", data_sep=", ", 
                   identifier=None, **kwargs):
    '''
    Convert data from a tabular format to a list of dict. Data is only 
    interpreted as character strings.
    
    Parameters
    ----------
        skip_first : bool
            If set True, skip the first line of the input file. 
            Default = False
            
        sep : str
            Character string that is used as field separators in the 
            input table. Default = "\t".
        
        data_sep : str
            Character string that is used as data separators in the 
            ouput values. Default = ", ".
        
        identifier : None|function
            Use the provided function to generate an identifier from a 
            positive integer representing the row number in the input
            table. It is added to the data with the key "ID".
        
        * : int|list
            Any keyword argument is interpreted as a field name. If the 
            parameter value is an int, data from the corresponding 
            column will be retrieved as the field value. If the 
            parameter is a list of int, data from the corresponding 
            columns will be retrieved and concatenated with the value
            of data_sep as separators.
            
    '''
    
    ### could add an option "use header" to use the header names instead of the
    ### kwargs to name fields
    
    for key in kwargs:
        if type(kwargs[key]) is list and all( type(x) is int
                                               for x in kwargs[key] ):
            continue
        elif type(kwargs[key]) is int:
            kwargs[key] = [kwargs[key]]
            continue
        elif kwargs[key] is None:
            continue
        raise TypeError(f'Value for "{key}" ({repr(kwargs[key])}) is' 
                         ' not an int or a list of int.')
    
    first_line = True
    data_list = []
    i = 1
    for line in f:
        if skip_first and first_line:
            first_line = False
            continue
        fields = line.split(sep)
        data = dict( (key, data_sep.join( fields[i].strip() 
                                           for i in kwargs[key] 
                                           if fields[i].strip() ))
                      for key in kwargs 
                      if kwargs[key] is not None )
        if identifier is not None:
            data["ID"] = identifier(i)
        data_list.append(data)
        i += 1
    return data_list

def overlap(a, b):
    '''
    Return True if interval a overlap with interval b.
    
    Parameters
    ----------
        a, b : list|tuple of int
            Intervals, defined by int bounds.
    '''
    
    return min(a[1], b[1]) >= max(a[0], b[0])
    
def roman_to_int(value):
  '''
  Convert a Roman number into an integer.
  
  Arguments
  ---------
    value : str
        A roman number.
  '''
  
  roman = {'I':1,'V':5,'X':10,'L':50,'C':100,'D':500,'M':1000,
           'IV':4,'IX':9,'XL':40,'XC':90,'CD':400,'CM':900}
  value = value.upper()
  i = 0
  num = 0
  while i < len(value):
     if i+1 < len(value) and value[i:i+2] in roman:
        num += roman[value[i:i+2]]
        i += 2
     else:
        num += roman[value[i]]
        i += 1
  return num

def get_id_formatter(s):   
    '''
    Return a function that generate and identifier with a given format,
    from a provided number.
    '''
    
    prefix, n = s.split(":")
        
    def f(x):
        return prefix + ("{:0" + n + "d}").format(x)
    return f

def clear_text(text, ranges, sub=" "):
    if is_range(ranges):
        ranges = [ranges]
    for r in ranges:
        if type(r) is int:
            text = f"{text[:r]}{sub}{text[r+1:]}"
        elif len(r) == 2:
            l = (r[1]-r[0])+1
            mask = sub*l
            text = f"{text[:r[0]]}{mask}{text[r[1]+1:]}"
        else:
            raise ValueError(f"unrecognized range value: {r}")
    return text

def is_range(r):
    '''
    Return True if the provided value is either an single integer or an array
    containing two integers.
    '''
        
    try:
        return len(r) == 2 and type(r[0]) is int and type(r[1]) is int
    except TypeError:
        return type(r) is int

def write_ranges(ranges):
    result = ""
    if is_range(ranges):
        ranges = [ranges]
    if not list(ranges):
        return result
    for r in ranges:
        if type(r) is int:
            result += f", {r}"
        elif len(r) == 2:
            result += f", {r[0]}-{r[1]}"
        else:
            raise ValueError(f"unrecognized range value: {r}")
    return result[2:]

def find_pattern(text, pattern):
    m = pattern.search(text)
    if m is not None:
        return m.group(), m.span()
    else:
        return None, None

def is_float(value):
    '''
    Check if value can be converted into a float.
    '''
    
    try:
        value = float(value)
    except ValueError:
        return False
    return True

def get_word_tokenize_pattern(min_len=1):
    min_char = "".join( "\w" for i in range(min_len-1) )
    return fr'\b{min_char}\w+\b'
                                        
def tokenize(value, min_len=1, method="words"):
    '''
    Extract lowercase tokens.
    
    Parameters
    ----------
        value : str
            input string
            
        min_len : int
            Discards tokens with less than the provided character 
            number.
        
        tokenize_method : str
            Set the method for tokenization. Can take one of the 
            following values:
                "words"     Split with white space characters and special
                            characters, ignore numbers.
                "standard"  Use the word_tokenize method from the NLTK 
                            package.
                "all"       Split with white spaces, keep every character
                            string.
    '''
    
    if method == "words":
        token_pattern = get_word_tokenize_pattern(min_len)
        tokens = regexp_tokenize(value, token_pattern)
    elif method == "standard":
        tokens = [ token for token in word_tokenize(value) 
                    if len(token) >= min_len ]
    elif method == "all":
        tokens = [ token for token in value.split() 
                    if len(token) >= min_len ]
    else:
        raise ValueError(f'Unknown tokenize method: "{method}"')
    
    return [ token.lower() for token in tokens ]

def get_ngrams(text, n, tokenize_method="words", ordered=True):
    tokens = tokenize(text, min_len=1, method=tokenize_method)
    if ordered:
        return [ tuple(tokens[i:i+n]) for i in range(len(tokens)-n+1) ]
    else:    
        return { tuple(sorted(tokens[i:i+n])) for i in range(len(tokens)-n) }
     
def get_text_segments(text, segments, get_intervals=False):
    if not segments: return [text]
    intervals = [(0, segments[0])]
    text_segments = [text[slice(*intervals[-1])]]
    if len(segments) > 1:
        for i in range(len(segments)-1):
            intervals.append((segments[i], segments[i+1]))
            text_segments.append(text[slice(*intervals[-1])])
    intervals.append((segments[-1], len(text)))
    text_segments.append(text[slice(*intervals[-1])])
    return zip(text_segments, intervals) if get_intervals else text_segments

def ngram_dist(a, b):
    if len(a) > len(b):
        a, b = b, a
    a = list(a) + [""]*(len(b)-len(a))
    l = len(a)
    for i in range(l):
        a = [ a[i+j-1%l] for j in range(l) ]
        dists = [ levenshtein(x, y) for x, y in zip(a, b) ]
    dists.sort()
    return dists[0]

def ngram_search(a, ngrams, mismatch_rule=mismatch_rule):
    matching_ngrams = ngrams
    for token in a:
        p = regex.compile(f"(?:{token}{mismatch_rule(token)}")
        matching_ngrams = [ ngram   
                             for ngram in matching_ngrams
                             if any( p.fullmatch(x) is not None 
                                      for x in ngram ) ]
    return sorted( (ngram, ngram_dist(a, ngram)) 
                    for ngram in matching_ngrams )

def strip_accents(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

def get_norm_leven_dist(a, b):
    '''
    Calculate the Levenshtein distance between two character strings, 
    then normalize this score by the length of the longest string.
    
    Parameters
    ----------
        a : str
            A character string.
        
        b : str
            Another character string.
    '''
    
    l = max([len(a), len(b)])
    return levenshtein(a, b)/l

def get_pairwise_leven_dist(lines):
    '''
    Calculate Levenshtein distances between all possible pairs of lines
    provided in input.
    
    Parameters
    ----------
        lines : list
            A list of str that will be compared by pair.
    '''
    
    # calculate all possible pairwise distance (avoid diagonal and duplicate 
    # comparisons)
    n = len(lines)
    dist = np.array([ [ get_norm_leven_dist(lines[i], lines[j]) if j < i else 0
                         for i in range(n) ]
                         for j in range(n) ])
    
    # copy values from the matrix upper triangle to the lower triangle
    i_lower = np.tril_indices(dist.shape[0], -1)
    dist[i_lower] = dist.T[i_lower]
    
    # return the pairwise distance matrix
    return dist

def get_levenKMedoids(lines, n_clusters=8, random_state=12345):
    '''
    Attempt to cluster strings given their similarity (expressed as 
    Levenshtein distance).
    
    Parameters
    ----------
        lines : list
            A list of str that will be compared by pair.
            
        n_clusters : int
            The number of clusters to define. Default=8.
    '''

    kmedoids = KMedoids(n_clusters=n_clusters, 
                        metrics=get_pairwise_leven_dist,
                        random_state=random_state).fit(lines)

def find_levenKMedoids(lines, max_cluster=8, method="elbow", 
                       random_state=12345):
    '''
    Optimize clustering of strings given their similarity (expressed as
    Levenshtein distance).
    
    Parameters
    ----------
        lines : list
            A list of str that will be compared by pair.
        
        max_cluster : int
            Attempt clustering up to this number of clusters.
        
        method : str
            Specify the selection method.
                elbow       Select the cluster number corresponding to 
                            the elbow of the SSE curve.
                
                silhouette  Select the cluster number corresponding to 
                            the maximum silhouette coefficient.
    '''
    
    # calculate KMedoids for 1 to max_cluster cluster numbers
    kmedoids_results = [ get_levenKMedoids(lines, i, random_state) 
                          for i in range(1, max_cluster+1) ]
    
    # elbow selection
    if method == "elbow":
    
        # extract the sum of squared error (SSE) for each KMedoids
        sse = [ kmedoids.inertia_ for kmedoids in kmedoids_results ]
        
        # locate the knee, assuming that SSE values are decreasing with increased 
        # cluster number and forming a convex curve
        kl = KneeLocator(range(1, max_cluster+1), sse, curve="convex", 
                         direction="decreasing")
        
        # get the KMedoids clustering at the elbow of the SSE curve
        best = kl.elbow-1
        
    # silhouette coefficient selection
    elif method == "silhouette":
        
        # extract the silhouette coefficient for each KMedoids
        silhouette_coeff = [ silhouette_score(lines, kmedoids.labels_, 
                                              metric=get_pairwise_leven_dist, 
                                              random_state=random_state)
                              for kmedoids in kmedoids_results ]
        
        # locate the higher silhouette coefficient
        best = silhouette_coeff.index(max(silhouette_coeff))
    
    # wrong method value
    else:
        raise ValueError(f'unknown method: {repr(method)}, method can be'
                          ' either "elbow" or "silhouette"')
    
    # return the best KMedoids according to the chosed method
    return kmedoids_results[best]
