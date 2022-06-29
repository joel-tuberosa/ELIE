
'''
    This module gathers generic functions for text data handling, 
    manipulation and formatting.
'''

import subprocess
import regex, unicodedata
import numpy as np
from kneed import KneeLocator
from math import log
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
WS_pattern = regex.compile(r"\s+", flags=regex.MULTILINE)

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
                   identifier=None, clean=[], **kwargs):
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
        
        clean : list
            Quotes will be stripped from the string at the provided 
            column indexes and newline character notation "\\n" will be
            converted to actual newline characters.
        
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
        data = dict( (key, data_sep.join( clean_str(fields[i].strip())
                                          if i in clean else fields[i].strip()
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

def smoothen_white_spaces(s, pattern=WS_pattern):
    '''
    Strip white spaces from the input string and convert other 
    consecutive white spaces into single space characters.
    '''

    return pattern.sub(" ", s.strip())

def strip_accents(s):
    '''
    Strip accent from a unicode character string.
    '''
    return ''.join(c for c in unicodedata.normalize('NFD', s)
                   if unicodedata.category(c) != 'Mn')

def simplify_str(s):
    '''
    Strip the input string, convert any remaining consecutive white 
    spaces into single space characters, convert to lowercase and
    strip accents.
    '''

    s = smoothen_white_spaces(s)
    s = strip_accents(s)
    s = s.lower()
    return s

def get_norm_leven_dist(a, b, simplify=False):
    '''
    Calculate the Levenshtein distance between two character strings, 
    then normalize this score by the length of the longest string.
    
    Parameters
    ----------
        a : str
            A character string.
        
        b : str
            Another character string.

        simplify : bool
            If set True, convert any consecutive white spaces into
            single space characters, convert to lowercase and strip
            accents.
    '''
    if simplify:
        a, b = simplify_str(a), simplify_str(b)
    l = max([len(a), len(b)])
    return levenshtein(a, b)/l

def get_pairwise_leven_dist(lines, simplify=False):
    '''
    Calculate Levenshtein distances between all possible pairs of lines
    provided in input.
    
    Parameters
    ----------
        lines : list
            A list of str that will be compared by pair.

        simplify : bool
            If set True, convert any consecutive white spaces into
            single space characters, convert to lowercase and strip
            accents.
    '''
    
    # calculate all possible pairwise distance (avoid diagonal and duplicate 
    # comparisons)
    n = len(lines)
    dist = np.array([ [ get_norm_leven_dist(lines[i], lines[j], simplify=simplify) 
                          if j < i else 0
                         for i in range(n) ]
                         for j in range(n) ])
    
    # copy values from the matrix upper triangle to the lower triangle
    i_lower = np.tril_indices(dist.shape[0], -1)
    dist[i_lower] = dist.T[i_lower]
    
    # return the pairwise distance matrix
    return dist

def get_median_dists(dist):
    '''
    Extract the median values for each row of the input matrix.

    Parameters
    ----------
        dist : ndarray
            A pairwise distance matrix embedded in a 2D array. The 
            diagonal of this matrix is supposed to go from top left to
            bottom right and is ignored during median extraction.
    '''
    
    # check matrix
    check = (np.allclose(dist, dist.T, atol=1e-8, rtol=1e-8),
             len(dist.shape) == 2) 
    if not all(check):
        raise ValueError("input must be a symetrical pairwise distance"
                         " matrix")
    n = dist.shape[0]

    # calculate median value while ignoring the diagonal values
    return [ np.median([ dist[i,j] for j in range(n) if i != j ])
                          for i in range(n) ]

def get_levenKMedoids(x, n_clusters=8, simplify=False, random_state=12345):
    '''
    Attempt to cluster strings given their similarity (expressed as 
    Levenshtein distance).
    
    Parameters
    ----------
        x : list|ndarray
            Can be either a list of str that will be compared by pair
            or a pairwise distance matrix embedded in an 2D array.
            
        n_clusters : int
            The number of clusters to define. Default=8.
        
        simplify : bool
            If set True, convert any consecutive white spaces into
            single space characters, convert to lowercase and strip
            accents.

        random_state : int
            A random seed
    '''
    
    # check x
    if all( type(e) is str for e in x ):
        str_input = True
    elif len(x.shape) == 2 and x.shape[0] == x.shape[1]:
        str_input = False
    else:
        raise ValueError('x must be either a list of str to be'
                         ' compared, or the corresponding pairwise'
                         ' distance matrix.')

    # calculate pairwise distances between input strings
    if str_input:
        x = get_pairwise_leven_dist(x, simplify=simplify)
        
    # find n_clusters KMedoids
    kmedoids = KMedoids(n_clusters=n_clusters, 
                        metric="precomputed",
                        init="k-medoids++",
                        random_state=random_state).fit(x)
    return (kmedoids, x)

def find_levenKMedoids(lines, max_cluster=8, method="elbow", 
                       simplify=False, random_state=12345):
    '''
    Optimize clustering of strings given their similarity (expressed as
    Levenshtein distance).
    
    Parameters
    ----------
        lines : list
            A list of str that will be compared by pair.
        
        max_cluster : int
            Attempt clustering up to this number of clusters. 
            Default=8, minimum=2.
        
        method : str
            Specify the selection method.
                elbow       Select the cluster number corresponding to 
                            the elbow of the SSE curve.
                
                silhouette  Select the cluster number corresponding to 
                            the maximum silhouette coefficient.
        
        simplify : bool
            If set True, convert any consecutive white spaces into
            single space characters, convert to lowercase and strip
            accents.

        random_state : int
            A random seed
    '''
    
    # check max_cluster value
    if max_cluster < 2:
        raise ValueError("max_cluster value must be an integer greater than 1")
    
    # calculate KMedoids for 1 to max_cluster cluster numbers
    kmedoids_results = [ get_levenKMedoids(lines, i, simplify, random_state) 
                          for i in range(1, max_cluster+1) ]
    
    # elbow selection
    if method == "elbow":
    
        # extract the sum of squared error (SSE) for each KMedoids
        sse = [ kmedoids.inertia_ for kmedoids, dist in kmedoids_results ]
                
        # locate the knee, assuming that SSE values are decreasing with increased 
        # cluster number and forming a convex curve
        kl = KneeLocator(range(max_cluster), sse, curve="convex", 
                         direction="decreasing")
        
        # best takes the value -1 if the method failed
        if kl.elbow is None:
            best = -1
        
        # get the KMedoids clustering at the elbow of the SSE curve
        else:
            best = kl.elbow
        
    # silhouette coefficient selection
    elif method == "silhouette":
        
        # extract the silhouette coefficient for each KMedoids
        silhouette_coeff = [ silhouette_score(dist, kmedoids.labels_, 
                                              metric="precomputed", 
                                              random_state=random_state)
                              for kmedoids, dist in kmedoids_results[1:] ]
                
        # locate the higher silhouette coefficient
        best = silhouette_coeff.index(max(silhouette_coeff)) + 1
    
    # wrong method value
    else:
        raise ValueError(f'unknown method: {repr(method)}, method can be'
                          ' either "elbow" or "silhouette"')
    
    # return the best KMedoids according to the chosed method
    if best == -1:
        return None
    return kmedoids_results[best][0]

def clean_str(s):
    '''
    Stip quotes, convert \\n to newline characters and \\t to 
    tabulations.
    '''
    
    # remove quotes
    if s[0] == "'" and s[-1] == "'":
        s = s.strip("'")
    elif s[0] == '"' and s[-1] == '"':
        s = s.trip('"')
    
    # convert newline
    s = s.replace(r"\n", "\n")

    # convert TABs
    s = s.replace(r"\t", "\t")
    return s

def mask_special_char(text, charset, mask="~"):
    '''
    Masks and indexes the special character found in the input text. 
    Returns a the masked text along with a list of the substituted 
    characters, in the order they were found.
    '''

    charset = list(charset) + [mask]
    masked_chars = []
    masked_text = ""
    for i in range(len(text)):
        c = text[i]
        if c in charset:
            masked_text += mask
            masked_chars.append(c)
        else:
            masked_text += c
    return (masked_text, masked_chars)

def unmask_special_char(masked_text, masked_chars, mask="~"):
    '''
    Recovers the original text from the return values of the function
    mask_special_char.
    '''

    text = ""
    i = 0
    for c in masked_text:
        if c == mask:
            text += masked_chars[i]
            i += 1
        else:
            text += c
    return text    

def text_alignment(lines, simplify=False):
    '''
    Align multiple text lines with MAFFT aligner.
    '''

    # some characters must be replaced, accent characters are used here as 
    # replacement for special characters that are not processed by the aligner
    # program. this implies that the input must not contains these characters.
    charset = "<>=- "

    # format the text to be aligned
    formated_lines = []
    lines_masked_chars = []
    for line in lines:
        
        # simplify the input text
        if simplify:
            line = simplify_str(line)

        # substitue special characters
        line, masked_chars = mask_special_char(line, charset)
        formated_lines.append(line)
        lines_masked_chars.append(masked_chars)

    # FASTA formating
    input_text = ""
    for i in range(len(formated_lines)):
        input_text += f">{i}\n{formated_lines[i]}\n"
    
    # run MAFFT as a subprocess
    cmd = ["mafft", "--text", "--maxiterate", "1000", "--globalpair", "--quiet", "-"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE,
                         stdout=subprocess.PIPE, text=True)
    o, _ = p.communicate(input_text)

    # retrieve aligned lines
    aligned_formated = regex.findall(r"(?<=>.+\n)[^>]+", o, flags=regex.M)

    # convert back the special characters
    aligned = []
    for line, masked_chars in zip(aligned_formated,
                                   lines_masked_chars):
        
        # remove newline characters
        line = line.replace("\n", "")

        # convert gaps to _
        line = line.replace("-", "_")

        # unmask special characters
        line = unmask_special_char(line, masked_chars)
        aligned.append(line)

    return aligned

def text_alignment_consensus(lines, simplify=False, remove_gaps=True):
    '''
    Simplifies the input strings, align with MAFFT, then returns a 
    single string corresponding to the most frequent character finds
    at each position of the alignment. Gaps created by the alignement
    are removed when they are consensus at a given position.
    '''

    # align the text using MAFFT, which requires the MAFFT program to be 
    # installed and located by the PATH variable. 
    aligned = text_alignment(lines, simplify=simplify)

    # build the consensus
    consensus = ""
    for column in zip(*aligned):
        freq = [ (c, column.count(c)) for c in set(column) ]
        freq.sort(key=lambda x: x[1])
        consensus += freq[-1][0]
    if remove_gaps:
        consensus = consensus.replace("_", "")
    return consensus

def text_pick_consensus(lines, simplify=False):
    '''
    Simplifies the input strings, calculate the Levenshtein pairwise 
    distance and pick the string that have the lowest median distance 
    with other strings.
    '''

    if simplify:
        lines = [ simplify_str(line) for line in lines ]
    dist = get_pairwise_leven_dist(lines)
    median_dist = get_median_dists(dist)
    sorted_median_dist = sorted(zip(lines, median_dist), key=lambda x: x[1])
    return sorted_median_dist[-1][0]
