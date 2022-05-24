
'''
    This module contains classes and functions to handle and integrate
    information extracted from specimen labels. It allows to build 
    searchable label databases using token extraction and text feature 
    scoring. This module uses the third-party packages regex, sklearn, 
    nltk and leven.
'''

import json, sys, mfnb.date, regex
from nltk import regexp_tokenize
from math import log
from mfnb.utils import mismatch_rule, get_word_tokenize_pattern, strip_accents
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from leven import levenshtein

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------
class Label(object):
    '''
    Store raw label data along with an identifier.
    '''
    
    keys = ("ID", "text")
    
    def __init__(self, ID=None, text=None):
        self._data = {"ID": ID, "text": text}
    
    def export(self):
        return dict(**self._data)
    
    def get_tuple(self, keys=None):
        if keys is None: keys=self.keys
        return tuple( self._data[key] for key in keys ) 
    
    @property
    def ID(self):
        return self._data["ID"]
    
    @property
    def text(self):
        return self._data["text"]
    
    def __hash__(self):
        return hash(self.get_tuple())

    def __repr__(self):
        return f'Label(ID: {self.ID}, text: {repr(self.text)})'
    
class CollectingEvent(Label):
    '''
    Store collecting event data, which include a label raw data and extracted
    information.
    '''
    
    ### implement a function to identity the different elements of a label text
    ### and make a collecting event object from a label object
    
    keys = ("ID", "location", "date", "collector", "text")
    
    def __init__(self, ID=None, location=None, date=None, collector=None, 
                 text=None):
        '''
        Load collecting event data.
        '''
        
        self._data = {"ID": ID, 
                      "location": location, 
                      "date": date,
                      "collector": collector,
                      "text": text}
    
    @property
    def location(self):
        return self._data["location"]
    
    @property
    def date(self):
        return self._data["date"]
    
    @property
    def collector(self):
        return self._data["collector"]
    
    def __repr__(self):
        return (f'CollectingEvent(ID: {self.ID},'
                f' Location: {self.location},'
                f' Date: {self.date}, Collector: {self.collector},'
                f' text: {repr(self.text)}')

class DB(object):
    '''
    Store a searchable collection of elements of the same type.
    '''
        
    def __init__(self, dbtype, values=[]):
        '''
        Load a list of object.
        '''
        
        # dbtype check
        for attr in ("ID", "text"):
            if not hasattr(dbtype, attr):
                raise TypeError("Element type of the database must have an"
                               f" '{attr}' attribute.")
        self.element_type = dbtype
                               
        # type check
        if not all( type(x) is self.element_type for x in values ):
            raise TypeError("Input values must only be"
                           f" {self.element_type.__name__} objects.")
        
        self._dict = dict( (x.ID, x) for x in values )
        self._ids = list(self._dict.keys())    
    
    @property
    def element_type(self):
        if not hasattr(self, "_element_type"):
            raise ValueError("This database has no defined element type.")
        return self._element_type
    
    @element_type.setter
    def element_type(self, value):
        if hasattr(self, "_element_type"):
            raise ValueError("Element type cannot be defined after object"
                             " initialization.")
        self._element_type = value
    
    def get(self, value):
        return self._dict[value]
    
    def is_indexed(self):
        return hasattr(self, "_index")
    
    def make_index(self, method=1, min_len=1, keys=None, ignore_ids=True):
        '''
        Make a database search index out of the tokens collected from
        all elements of the collection.
        
        Parameters
        ----------
            
            method : int
                Select to the method with which to build the index.
                Available methods:    
                    1- Associate tokens with database elements
                    
                    2- Associate tokens with database elements, and
                       a normalized TF-IDF score.
                       
                Default: 1
            
            min_len : int
                Discards tokens with less than the provided character 
                number.
            
            keys : list
                Only fetch tokens from the provided key list. By 
                default, build a database from the value stored in 
                the "text" field.
        '''
        
        # by default, search in all elements of the database items except the 
        # ID.
        if keys is None:
            keys = tuple( key 
                           for key in self.element_type.keys 
                           if not ignore_ids or key != "ID" )
        
        # tokenize pattern
        token_pattern = get_word_tokenize_pattern(min_len)
        corpus = ( "\n".join(x.get_tuple(keys)) for x in self )
        
        # index and stored parameters
        self._index = dict()
        self._parameters = {"method": method, "token_pattern": token_pattern}
        
        # - method 1
        # Associate each unique token with every database item that contains 
        # it. Each item is stored in association with the frequency of the 
        # token in its content.
        if method == 1:
            vectorizer = CountVectorizer(token_pattern=token_pattern, 
                                         strip_accents="unicode")
        
        # - method 2
        # Associate each unique token with every database item that contains 
        # it. Each item is stored in association with the normalized TF-IDF
        # score of the token in its content.
        if method == 2:
            vectorizer = TfidfVectorizer(token_pattern=token_pattern,
                                         strip_accents="unicode")
        
        # Store the matrix containing scores for each unique token in each
        # element of the database, then build the index linking tokens with
        # items and scores.
        self._score_matrix = vectorizer.fit_transform(corpus)
        j = 0
        for token in vectorizer.get_feature_names_out().tolist():
            i = 0
            for x in self:
                score = self._score_matrix[i,j]
                if score:
                    try:
                        self._index[token].append((x, score))
                    except KeyError:
                        self._index[token] = [(x, score)]
                i += 1
            j += 1
        
    def search(self, query, mismatch_rule=mismatch_rule, 
               filtering=lambda ID: True):
        '''
        Search elements using input text.
        '''
                
        if not self.is_indexed():
            raise ValueError("Database must be indexed with the 'make_index'"
                             " method prior to search")
        
        # extract token from the query
        query_tokens = regexp_tokenize(strip_accents(query.lower()), 
                                       self._parameters["token_pattern"])
        
        # with method #2, unique token?
        # query_tokens = set(query_tokens)
        
        # search database tokens with regular expression and score the possible 
        # matches
        results = [ (q, x, matched_token, identity, score)
                     for q in query_tokens
                     for x, matched_token, identity, score 
                      in self.get_token_matches(q, 
                                                mismatch_rule, 
                                                filtering) ]
        
        # for the same token, keep only the best match in each collecting event
        results.sort(key=lambda x: (x[1].ID, x[2], x[3], x[4]), reverse=True)
        results = [ results[i] 
                     for i in range(len(results)) 
                      if i==0 or 
                         results[i-1][1] != results[i][1] or
                        (results[i-1][1] == results[i][1] and 
                         results[i-1][2] != results[i][2]) ]

        # calculate the final score
        hit_scoring = dict()
        for q, x, matched_token, identity, score in results:
        
            # the hit score of a given collecting event is the sum of the 
            # normalized TFIDF scores matched in this collecting event any
            # of the query tokens
            try:
                hit_scoring[x.ID][0] += score*identity
            except KeyError:
                hit_scoring[x.ID] = [score*identity, 0]
            
            # count the number of token that matched this collecting event
            hit_scoring[x.ID][1] += 1
        
        # return a list of the matches ordered by normalized score (high to low)
        result = []
        for ID, scores in hit_scoring.items():
            score, n = scores
            
            # maximum score if all token are matched in the collecting event
            x_max_score = self._score_matrix[self._ids.index(ID)].sum()
            
            # the score is normalized by the maximum score
            score /= x_max_score
            
            # ...and weighted by the number of matching token
            score *= (n/len(query_tokens))
            
            result.append((self.get(ID), score))
        
        # result are sorted from best to lowest matching score    
        result.sort(key=lambda x: x[1], reverse = True)
        return result      
            
    def get_token_matches(self, value, mismatch_rule=mismatch_rule, 
                          filtering=lambda x: True):
        '''
        Find elements with matching tokens, return a list of IDs with 
        the associated token's TF-IDF score.
        
        Parameters
        ----------
        
            value : str
                The token to be searched.
            
            mismatch_rule : function|None
                If defined as a function, this function will take a 
                single argument, the token, and return a fuzzy regular 
                expression. If defined as None, it will look for exact 
                matches.
        '''
        
        # retrieve matching tokens
        if mismatch_rule is None:
            result = [ (self.get(x), value, score) 
                        for x, score in self._index[value] 
                        if filtering(x) ]
        else:
            pattern = regex.compile(fr"(?:{value}){mismatch_rule(value)}")
            
            # list matching collecting events and associated scores
            result = []
            for token, hits in self._index.items():
                m = pattern.fullmatch(token)
                if m is None: continue
                d = levenshtein(token, value)
                l = max((len(token), len(value)))
                identity = 0 if d > l else (1 - d/l)
                for x, score in hits:
                    if not filtering(x): continue
                    result.append((x, token, identity, score))
        
        # when one token in the query matches multiple token of the same 
        # collecting event, only the best match is kept.
        if result:
            result.sort(key=lambda x: (x[0].ID, x[2], x[3]),
                        reverse = True)
            result = [ result[i] 
                        for i in range(len(result)) 
                        if i==0 or result[i-1][0] != result[i][0] ]

        return result    

    def __len__(self):
        '''
        Returns the number of elements in the database.
        '''
        
        return len(self._dict)
    
    def __iter__(self):
        '''
        Iterate over elements of the database.
        '''
        
        return iter( self._dict[key] for key in self._dict )

class LabelDB(DB):
    '''
    Store label data and allow text search.
    '''
    
    def __init__(self, values=[]):
        '''
        Load a list of labels.
        '''
                
        # type check and DB build
        DB.__init__(self, Label, values)
        
class CollectingEventDB(DB):
    '''
    Store collecting events and allow text-based search.
    '''
    
    def __init__(self, values=[]):
        '''
        Load a list of collecting events.
        '''
        
        # type check and DB build
        DB.__init__(self, CollectingEvent, values)
    
    def has_date_index(self):
        return hasattr(self, "_date_index")
    
    def make_date_index(self, **allow_tags):
        '''
        Intepret the date fields of the collecting events to make them 
        searchable with types from the library datetime and the 
        mfnb.date.DateRange type.
        '''
        parser = mfnb.date.DatePatterns(**allow_tags)
        self._date_index = []
        for x in self:
            date = parser.find_date(x.date)
            
            # If no date could be found, the collecting event is not added to 
            # the index
            if date is None:
                continue
            
            # Otherwise, it is always added as a daterange
            elif type(date) is mfnb.date.Date:
                daterange = mfnb.date.DateRange(date, date)
            else:
                daterange = date
            self._date_index.append([daterange, x.ID])
    
    def search_by_date(self, query, assume_same_century=False, **allow_tags):
        '''
        Find collecting events that overlap with the given date or
        daterange.
        '''
        
        if not self.has_date_index():
            raise ValueError("You must build the date index with the"
                             " make_date_index method prior to use the" 
                             " search_by_date method")
        
        if type(query) is str:
            parser = mfnb.date.DatePatterns(**allow_tags)
            date = parser.find_date(query)
            if date is None:
                raise ValueError(f"{query} was not recognized as a date")
            query = date
        elif type(query) not in (mfnb.date.Date, mfnb.date.DateRange):
            raise TypeError(f"Invalid type for the query ({type(query)}),"
                             " should be str, mfnb.date.Date or"
                             " mfnb.date.DateRange")
        return [ self.get(ID) 
                  for daterange, ID in self._date_index 
                  if daterange.overlap_with(query, 
                                            assume_same_century) ]
        
# =============================================================================
# FUNCTIONS
# -----------------------------------------------------------------------------
def load_labels(f):
    '''
    Build a label database from data stored in a JSON file.
    
    Parameters
    ----------
        f : file
            File object to access JSON data with the json.load method.
    '''
    
    return LabelDB([ Label(**x) for x in json.load(f) ])

def load_collecting_events(f):
    '''
    Build a collecting event database from data stored in a JSON file.
    
    Parameters
    ----------
        f : file
            File object to access JSON data with the json.load method.
    '''

    return CollectingEventDB([ CollectingEvent(**x) for x in json.load(f) ])

def read_googlevision_output(f):
    '''
    Read a Google Vision JSON output and return the full text.
    
    Parameter
    ---------
        f : 
    '''
    for response in json.load(f)["responses"]:
        yield response["fullTextAnnotation"]["text"]

def data_from_googlevision(f, identifier, start=1):
    data_list = []
    for text in read_googlevision_output(f):
        data_list.append({
            "ID": identifier(len(data_list)+start),
            "text": text})
    return data_list
