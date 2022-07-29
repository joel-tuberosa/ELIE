'''Date module
    
This module contains classes and functions related to time data. It
uses fuzzy regular expressions from the third party package regex to
find dates within OCR extracted text and the dateparser package to 
interpret the diversity of date formats. The Date and DateRange classes
allow to store dates with various precision levels, reflecting the data
status collected among labels.
'''

import json, regex, dateparser, sys
from mfnb.utils import overlap, roman_to_int

# delete the dateparser warning
if not sys.warnoptions:
    import warnings
    warnings.filterwarnings(
        "ignore",
        message="The localize method is no longer necessary")

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------

class DatePatterns(object):
    '''
    A collection of regular expression patterns to match a broad range 
    of date or date range formats.
    '''
    
    # days are always written in digits
    day_patterns = {
        "digit"         :   r'(?P<day2>[0-3]?[0-9])'} 

    # month can be either written in:
    month_patterns = { 
        "digit"         :   r'(?P<month2>1[0-2]|0?[0-9])',
        "roman"         :   r'(?P<month2>[iIvVxX]{1,2}[iI]*)', 
        "literal"       :   r'(?P<month2>[[\w]--[0-9_]]+)' }
    ### literal pattern encompass the roman one... remove the roman pattern
    ### and detect it afterwards?
    
    # year are written in:    
    year_patterns = {   
        "two-digit"     :   r'(?P<year2>[0-9]{2})',
        "four-digit"    :   r'(?P<year2>[12][0-9]{3})'}

    ### warning, altitude could be misinterpreted for years

    # separators can be the followings:
    separator_patterns = { 
        "set1"          :   r'(?:[:\|/.,]){i<=1,s<=1:\s}'}

    ### to be included: 
    ### - if there is more than a dash, then dash is not 
    ###   interpreted as a range but as a separator 
    
    # date can take any of the following format.
    possible_formats = r'''
    \b{year}\b
    \b{month}{sep}{year}\b
    \b{day}{sep}{month}{sep}{year}\b
    \b{month}{sep}{day}{sep}{year}\b
    \b{year}-{year}\b
    \b{month}(?:{sep})?-{month}{sep}{year}\b
    \b{day}(?:{sep})?-{day}{sep}{month}{sep}{year}\b
    \b{month}{sep}{day}(?:{sep})?-{day}{sep}{year}\b
    \b{day}{sep}{month}(?:{sep})?-{day}{sep}{month}{sep}{year}\b
    \b{month}{sep}{day}(?:{sep})?-{month}{sep}{day}{sep}{year}\b
    \b{day}{sep}{month}{sep}{year}-{day}{sep}{month}{sep}{year}\b
    '''.split()  
    
    def __init__(self, **allow_tags):
        '''
        Compile regular expressions for date parsing.

        Parameters
        ----------
            **allow_tags
                Keyword arguments correspondig to valid DatePatternTag 
                can be used here to limit date parsing to specific 
                format or precision level.
        '''
        
        # initialize the data container variable
        self._data = []
        
        # possible formats x patterns
        for date_format in self.possible_formats:
            for day_format in self.day_patterns:
                for month_format in self.month_patterns:
                    for year_format in self.year_patterns:
                        for sep_format in self.separator_patterns:
                            pattern = date_format.format(
                                day=self.day_patterns[day_format],
                                month=self.month_patterns[month_format], 
                                year=self.year_patterns[year_format], 
                                sep=self.separator_patterns[sep_format])
                            
                            # Patterns of the fields year, month and day are 
                            # named so that they can be retrieved. To include
                            # date ranges, patterns are also numbered (i.e 
                            # year1, year2, month1, month2, etc.).
                            pattern = pattern.replace("year2", "year1", 1)
                            pattern = pattern.replace("month2", "month1", 1)
                            pattern = pattern.replace("day2", "day1", 1)
                            pattern = pattern.replace("sep2", "sep1", 1)
                            
                            # a serie of tags is added for further filtering
                            tags = tag_date_pattern(pattern, 
                                                    day_pattern=day_format,
                                                    month_pattern=month_format,
                                                    year_pattern=year_format)
                            
                            self._data.append({"pattern": 
                                                    regex.compile(pattern, 
                                                    flags=regex.BESTMATCH | regex.V1),
                                               "tags": tags})
                            
    def get_patterns(self, **allow_tags):
        '''
        Returns all compiled patterns, with the possibility of 
        filtering out given formats or precision levels.

        Parameters
        ----------
            **allow_tags
                Keyword arguments correspondig to valid DatePatternTag 
                can be used here to limit date parsing to specific 
                format or precision level.
        '''
        
        allow_tags = DatePatternTags(**allow_tags)
        return [ (element["pattern"], element["tags"]) 
                  for element in self._data
                  if allow_tags.match(element["tags"]) ]
        
    def search(self, value, **allow_tags):
        '''
        Searches all possible date patterns in a text. Returns a list 
        of hits (DateMatch objects) ranked by accuracy level.

        Parameters
        ----------
            value : str
                Any text.

            **allow_tags
                Keyword arguments correspondig to valid DatePatternTag 
                can be used here to limit date parsing to specific 
                format or precision level.
        '''
        
        hits = []
        for pattern, tags in self.get_patterns(**allow_tags):
            m = pattern.search(value)
            if m is None: continue
            
            # score is the total length of the matched strings
            score = sum( len(x) for x in m.groups() ) 
            
            # name data values for date 1 and date 2
            fields = [ x+i 
                        for x in ("year", "day", "month")
                        for i in ("1", "2") ]
            
            # get values that where matched in the best hit
            matched_groups = [ key 
                        for key, value in pattern.groupindex.items() 
                        if not key.startswith("sep")
                           and m.group(value) is not None ]
            
            # store each stripped value in a dictionnary, unmatched values are stored
            # as None
            data = dict( (field, m.group(field).strip()
                          if field in matched_groups else None)
                          for field in fields )
            
            # update the dictionnary with best match info
            data.update(dict(match = m,
                             pattern = pattern,
                             score = score,
                             tags = tags))
                             
            # return a DateMatch object with data
            hits.append(DateMatch(**data))            
            
        # extract date and sort hits
        hits.sort(key = lambda x: x.get_scores(), reverse=True)
        return hits
    
    def find_date(self, value, get_span=False, **allow_tags):
        '''
        Finds a date in a text. Returns the date as a Date object, 
        optionnally with the span of the match in the parsed text.

        Parameters
        ----------
            value : str
                Any text.

            get_span : bool
                Returns the Date object along with the span of the 
                match in the parsed text.
            
            **allow_tags
                Keyword arguments correspondig to valid DatePatternTag 
                can be used here to limit date parsing to specific 
                format or precision level.
        '''
        
        for hit in self.search(value, **allow_tags):
            date1, date2 = hit.get_dates()
            if date1 is None: continue
            skip = False
            
            # extracted date must be of the same precision level than the 
            # pattern used
            for x in (date1, date2):
                if x.precision_level < hit.get_scores()[0]:
                    # sys.stderr.write("Warning: the date could not be extracted"
                                     # " with the expected precision level given"
                                     # " the pattern that was detected! Date"
                                     # " skipped.")
                    skip = True
                    break
            if skip: continue
            
            if date1 == date2: 
                if get_span:
                    return date1, hit.get_value("match").span()
                return date1
            else:
                if get_span:
                    return DateRange(date1, date2), hit.get_value("match").span()
                return DateRange(date1, date2)
        
        # nothing to return
        return (None, None) if get_span else None

class DatePatternTag(object):
    '''
    A serie of tags that characterize a date pattern.
    '''
    
    _allowed_values = { "fields": set(["year1", "year2", "month1", "month2", "day1", "day2"]),
                        "precision_level" : set([-1,0,1,2]),
                        "day_pattern": set(DatePatterns.day_patterns.keys()),
                        "month_pattern": set(DatePatterns.month_patterns.keys()),
                        "year_pattern": set(DatePatterns.year_patterns.keys()),
                        "is_us": set([False, True, None]),
                        "is_range": set([False, True, None]) }
    
    def __init__(self, name, value):
        '''
        Build the DatePatternTag object from a tag name and a 
        corresponding value.

        Parameters
        ----------
            name : str
                A tag name from the known tags.

            value : str
                A value for the tag, in the range of possible tag value.
        
        Tags and possible values
        ------------------------
            fields
                "year1", "year2", "month1", "month2", "day1", "day2"
            
            precision_level
                -1 (none), 0 (year), 1 (month), 2 (day)

            day_pattern
                "digit"

            month_pattern
                "digit", "roman", "literal"
            
            year_pattern
                "two-digit", "four-digit"
            
            is_us
                True, False

            is_range
                True, False
        '''
        
        if name not in DatePatternTag._allowed_values.keys():
            raise ValueError(f'Unknown tag name: "{name}"')
        if name == "fields":
            check = all( x in DatePatternTag._allowed_values[name] for x in value )
        else:
            check = value in DatePatternTag._allowed_values[name]
        if not check:
            raise ValueError(f'Tag value not valid for "{name}": "{value}"')
        self._data = (name, value)
    
    def match(self, other):
        '''
        Returns True if the other DatePatternTag is compatible with the 
        value of the object.

        Rules for given tags
        --------------------
            fields
                For the "fields" tag, check that all field values from
                this tag is included in the other tag.
            
            precision_level
                Check that the precision level of the other tag is 
                equal or lower than this tag.
            
            (all other tags)
                Check that the values are equivalent.
        '''
        
        # Type and value checking
        if type(other) is not DatePatternTag:
            raise TypeError("The value to be compared with must be another"
                           f" DatePatternTag object, '{type(other)}' found"
                            " instead.")
        if self.name != other.name:
            raise ValueError("Tags to be compared must have the same name.")
        
        # For field, return True if all values of 'self' is found in 'other'
        if self.name == "fields":
            return all( x in other.value for x in self.value )
        
        # For precision level, return True if the precision_level of 'self' is 
        # lower or equal to the 'other'.
        elif self.name == "precision_level":
            return self.value <= other.value
        
        # For other values, check if there are equivalent
        else:
            return self.value == other.value
            
    @property
    def name(self):
        return self._data[0]
    
    @property
    def value(self):
        return self._data[1]
    
    @value.setter
    def value(self, value):
        if value not in DatePatternTag._allowed_values[self.name]:
            raise ValueError(f'Tag value not valid for "{self.name}":'
                             f' "{value}"')
        self._data = (self.name, value)
    
    def __repr__(self):
        return f"DatePatternTag({self.name}: {self.value})"
    
    def __hash__(self):
        return hash(self._data)
        
class DatePatternTags(object):
    '''
    A collection of tags to be attached with a date pattern.
    '''
    
    def __init__(self, **tags):
        '''
        Build the tag collection from a provided series of tags to 
        build individual DatePatternTag object.

        Parameters
        ----------
            fields : str
                Which fields were found in the matching text.
                Possible values: "year1", "year2", "month1", "month2", 
                                 "day1", "day2"
            
            precision_level : int
                The precision level of the date.
                Possible values: -1 (none), 0 (year), 1 (month), 
                                 2 (day)

            day_pattern : str
                The day format.
                Possible value: "digit"

            month_pattern : str
                The month format.
                Possible values: "digit", "roman", "literal"
            
            year_pattern : str
                The year format.
                Possible values: "two-digit", "four-digit"
            
            is_us : bool
                Set True if the date is in US format, namely, with the 
                month before the day.

            is_range : bool
                Set true if the match is a date range.    
        '''
        
        self._data = set()
        for name, value in tags.items():
            tag = DatePatternTag(name, value)
            self.add(tag)
    
    def contains(self, tag):
        '''
        Returns True if an equivalent of the provided DatePatternTag 
        is in the collection.
        '''
        
        return tag in self._data
    
    def add(self, tag):
        '''
        Add a new DatePatternTag to the collection.
        '''
        
        if type(tag) is not DatePatternTag:
            raise TypeError("Value is not a DatePatternTag object,"
                           f" '{type(tag)}' found instead")
        self._data.add(tag)    
    
    def get(self, name):
        '''
        Get the DatePatternTag corresponding to the provided name.
        '''
        
        for tag in self:
            if tag.name == name:
                return tag
        raise KeyError(f"Tag '{name}' not found")
    
    def get_value(self, name):
        '''
        Get the value of the DatePatternTag corresponding to the 
        provided name.
        '''
        
        return self.get(name).value
    
    def match(self, other):
        '''
        Check whether all tags match those of the other object.
        '''
        
        return all( tag.match(other.get(tag.name)) for tag in self )
    
    def __repr__(self):
        tags = ", ".join( repr(tag) for tag in self._data )
        return f"DatePatternTags({tags})"
    
    def __iter__(self):
        return iter(self._data)

class DateMatch(object):
    '''
    Contains data from a match of the DatePatterns.match method.
    '''
    
    _types = {"year1": str, "month1": str, "day1": str,     
              "year2": str, "month2": str, "day2": str, 
              "pattern": regex.Pattern, 
              "match": regex.Match,
              "score": int, 
              "tags": DatePatternTags}
    
    def __init__(self, **kwargs):
        '''
        Build the object from a series of keywords arguments that 
        describe the parsed information and the regular expression that
        was used.

        Parameters
        ----------
            year1 : str
                Interpreted year value. If the match is a date ranges, 
                this would store the earliest date.
            
            year2 : str
                Interpreted latest year value in a date range.

            month1 : str
                Interpreted month value. If the match is a date ranges, 
                this would store the earliest date.

            month2 : str
                Interpreted latest month value in a date range.

            day1 : str
                Interpreted day value. If the match is a date ranges, 
                this would store the earliest date.

            day2 : str
                Interpreted latest day value in a date range.

            pattern : regex.Pattern
                Compiled regular expression pattern (from the regex 
                module), that was used to parse the date value.

            match : regex.Match
                Match object from the regex module, corresponding to 
                the parsed date.

            score : int
                Match score, representing the information level. A 
                higher score indicates a higher information level.

            tags : DatePatternTags
                A series of tags describing the date format and its
                precision level.
        '''

        self._data = dict( (key, None) for key in DateMatch._types )
        self.update(**kwargs)
    
    def update(self, **kwargs):
        '''
        Updates the object internal data.

        Parameters
        ----------
            year1 : str
                Interpreted year value. If the match is a date ranges, 
                this would store the earliest date.
            
            year2 : str
                Interpreted latest year value in a date range.

            month1 : str
                Interpreted month value. If the match is a date ranges, 
                this would store the earliest date.

            month2 : str
                Interpreted latest month value in a date range.

            day1 : str
                Interpreted day value. If the match is a date ranges, 
                this would store the earliest date.

            day2 : str
                Interpreted latest day value in a date range.

            pattern : regex.Pattern
                Compiled regular expression pattern (from the regex 
                module), that was used to parse the date value.

            match : regex.Match
                Match object from the regex module, corresponding to 
                the parsed date.

            score : int
                Match score, representing the information level. A 
                higher score indicates a higher information level.

            tags : DatePatternTags
                A series of tags describing the date format and its
                precision level.
        '''
        
        for (key, value) in kwargs.items():
            if value is not None and type(value) is not DateMatch._types[key]:
                raise TypeError(f"Wrong type when updating the '{key}' variable"
                                f" of a DateMatch object. Expected"
                                f" '{DateMatch._types[key]}', found"
                                f" '{type(value)}' instead.")
            self._data[key] = value        

    def get_scores(self):
        '''
        The score of a match is defined by:
            1) the precision level
            2) if applicable, whether the month value was matched by 
               the literal pattern (\W+), which is very permissive and
               not preferred.
            3) the length of the matched string
        
        The higher the score, the better it is.
        '''
        
        precision_level = self.get_value("tags").get_value("precision_level")
        month_pattern = self.get_value("tags").get_value("month_pattern")
        score = self.get_value("score")
        return (precision_level, int(month_pattern != "literal"), score)    
    
    def get_value(self, name):
        '''
        Returns the value of a specific feature.
        '''
        
        return self._data[name]
    
    def get_dates(self):
        '''
        Returns a tuple with two Date objects. If the match is a single 
        date, the two dates are identical. If the match is a date 
        range, the tuple will contain the dates corresponding to the 
        limits of this range.
        '''
        
        # report year data of date1 on date2 when missing
        if self._data["year2"] is None: 
            self._data["year2"] = self._data["year1"]
        
        # if the year string is represented by 2 digits, consider that the 
        # century is not known
        for year in ("year1", "year2"):
            if len(self._data[year]) == 2:
                self._data[year] = "'" + self._data[year]
        
        # report month and day data of date1 on date2 when missing
        if self._data["month2"] is None:
            self._data["month2"] = self._data["month1"]
        if self._data["day2"] is None: 
            self._data["day2"] = self._data["day1"]
        
        # if month were found in Roman number, convert to integer for better
        # compatibility with the dateparser module
        if self.get_value("tags").get_value("month_pattern") == "roman":
            self._data["month1"] = str(roman_to_int(self._data["month1"]))
            self._data["month2"] = str(roman_to_int(self._data["month2"]))
        
        # make a Date object from date1 and date2
        date1 = Date(self._data["year1"], 
                     self._data["month1"], 
                     self._data["day1"])

        date2 = Date(self._data["year2"], 
                     self._data["month2"], 
                     self._data["day2"])

        # sometime, patterns where not recognized by the Date constructor, so
        # the Date object remains empty
        if date1.is_empty() or date2.is_empty():
            return None, None

        # in any cases, return two dates
        return date1, date2      
    
class Date(object):
    '''
    Store date data with information on the precision level.
    '''
    
    year_pattern = regex.compile(r"[1-9][0-9]{3}|'[0-9][0-9]")
    ddp = dateparser.date.DateDataParser()
    
    def __init__(self, year, month=None, day=None):
        '''
        Initialize the object with date data.
        
        Parameters
        ----------
            year : int|str
                If year is an integer, it will be interpreted as 
                provided, with no ambiguity on the century. If it is
                provided as a str, it can be interpreted in two way:
                with a leading ' and only two digits, it is interpreted
                as if the century was not known, otherwise, it is 
                interpreted as it is provided. Warning, year value 
                cannot exceed 9999.
            
            month : int|str
                Month value can be either an integer between 1 and 12, 
                or any str that can be recognized as a month by the 
                dateparser module.
            
            day : int|str
                Month value is always provided as digits between 1-31, 
                either as an int or a str type.
        '''
        
        # type check
        
        # -- year
        if type(year) is int:
            if 0 <= year < 10000:
                year = str(year)
            else:
                raise ValueError("Year value must be between 0 and 9999")
        elif type(year) is not str:
            raise TypeError("Year value type must be str or int,"
                           f" {type(year)} found.")
            
        # -- month
        if type(month) is int:
            if 1 <= month <= 12:
                month = str(month)
            else:
                raise ValueError("If provided as an int value, month value"
                                 " must be between 1 and 12")
        elif type(month) is not str and month is not None:
            raise TypeError("Month value type must be int, str or None,"
                           f" {type(month)} found.")

        # -- day
        if type(day) is int:
            if 1 <= day <= 31:
                day = str(day)
            else:
                raise ValueError("If provided as an int value, day value"
                                 " must be between 1 and 31")
        elif type(day) is not str and day is not None:
            raise TypeError("Day value type must be int, str or None,"
                           f" {type(day)} found.")
        
        # raw data is stored as str to match any format
        self._rawdata = (year, month, day)

        # loose format check
        if Date.year_pattern.match(year) is None:
            raise ValueError(f'str "{year}" not recognized as a year')
        
        # record in this variable whether the century is known
        century_known = year[0] != "'"
        
        # express the date in a string to be interpreted by the parser
        date_str = ""
        
        # -- year
        if century_known:
            date_str += f"{year}"
            formats = ["%Y"]
        else:
            date_str += f'19{year[-2:]}'
            formats = ["%y"]
        
        # -- month
        if month is not None:
            if month.isdigit():
                date_str += f"-{int(month):02d}"
                formats = [ f"{formats[0]}-%m" ]
            else:
                date_str += f"-{month}"
                formats = [ f"{formats[0]}-%b", f"{formats[0]}-%B" ]
            
        # -- day
        if day is not None:
            date_str += f"-{int(day):02d}"
            formats = [ f"{f}-%d" for f in formats ]
        
        # parse with dateparser
        ### issue with year-only date: when the date format is specified, it
        ### set the month as January and the period as month
        if month is None and day is None:
            date = Date.ddp.get_date_data(date_str)
        else:
            date = Date.ddp.get_date_data(date_str, date_formats=formats)

        if date.date_obj is None:
            self._parseddata = { "year" : None,
                                 "month" : None,
                                 "day" : None,
                                 "precision" : None,
                                 "century": "unknown" }
        else:
            self._parseddata = { "year": date.date_obj.year 
                                    if century_known 
                                    else int(self._rawdata[0][-2:]), 
                                 "month": date.date_obj.month 
                                    if date.period in ("month", "day")
                                    else None,
                                 "day": date.date_obj.day 
                                    if date.period == "day"
                                    else None,
                                 "precision": date.period,
                                 "century": "known" if century_known 
                                                    else "unknown"
                                }
        
    @property
    def year(self):
        return self._parseddata["year"]
    
    @property
    def century(self):
        if self.century_known:
            return self.year // 100
        raise ValueError("century not known")
            
    @property
    def month(self):
        return self._parseddata["month"]
    
    @property
    def day(self):
        return self._parseddata["day"]
    
    @property
    def precision(self):
        return self._parseddata["precision"]
    
    @property
    def precision_level(self):
        if self.precision is None: 
            return None
        elif self.precision == "year":
            return 0
        elif self.precision == "month":
            return 1
        elif self.precision == "day":
            return 2
        else:
            raise ValueError("offending value for self.precision:"
                            f" {repr(self.precision)}")
    
    @property
    def century_known(self):
        return self._parseddata["century"] == "known"
    
    def get_isoformat(self, century=None):
        '''
        Return the date as a ISO8601 formatted string.

        Parameters
        ----------
            century : int
                Override or add the century value.
        '''
        
        # year
        if century:
            datestr = f"{century}{self.year[:-2]}"
        elif self.century_known:
            datestr = f"{self.year}"
        else:
            datestr = f"-{self.year}"
        
        # month
        if self.month:
            datestr += f"-{self.month}"
        
        # day
        if self.day:
            datestr += f"-{self.day}"
        
        return datestr
        
    def set_century(self, value):
        '''
        Changes the century value of the date.
        '''
        
        decades = self.year % 100
        year = value*100 + decades
        self.__init__(year, self.month, self.day)
    
    def is_empty(self):
        '''
        Returns True if the Date object does not contain any 
        information.
        '''
        
        return self.precision is None
    
    def is_in(self, daterange, assume_same_century=False):
        '''
        Evaluates whether the date is within a provided daterange.
        
        Parameters
        ----------
            daterange : DateRange
                A DateRange object of any precision. If the precision is 
                lower than that of the range, it will always return
                False.
                
            assume_same_century : bool
                Assume that the evaluated dates are of the same century
                Does not take effect if both dates have a known century.
        '''
        
        if type(daterange) is not DateRange:
            raise TypeError("the Date.is_in method works on DateRange objects")
        
        # return False if the precision level of the queried object is lower than
        # that of the target range
        if self.precision_level < daterange.precision_level:
            return False
        
        # if both century are known, compare the date with the range values
        if self.century_known and daterange.century_known:
            return self._is_in(daterange)
        
        # if not, and if one does not assume that this is the same century, 
        # return False
        elif not assume_same_century:
            return False
        
        # if the century of the queried object is known, it is reported on the 
        # range
        elif self.century_known:
            daterange = DateRange(
                Date((daterange.start.year%100) + (self.century*100), 
                      daterange.start.month, 
                      daterange.start.day),
                Date((daterange.end.year%100) + (self.century*100), 
                      daterange.end.month, 
                      daterange.end.day))
            return self.is_in(daterange)
        
        # if the century of the target range is known, it is reported on the 
        # queried object.
        elif daterange.start.century_known:
            a = Date((self.year%100) + (daterange.start.century*100), 
                      self.month, 
                      self.day) 
            return a.is_in(daterange)
        
        # if none of the date or the range century is known, it is compared
        # with the current values
        else:
            return self._is_in(daterange)
    
    def _is_in(self, daterange):
        '''
        Returns True if the date is in the provided range. Both date 
        and the range needs the same precision level.
        '''

        # year
        year_in_range = daterange.start.year <= self.year <= daterange.end.year
        
        # month
        if daterange.precision != "year":
            month_in_range = daterange.start.month <= self.month <= daterange.end.month
        else:
            month_in_range = True
            
        # day
        if daterange.precision == "day":
            day_in_range = daterange.start.day <= self.day <= daterange.end.day
        else:
            day_in_range = True

        return all((year_in_range, month_in_range, day_in_range))
    
    def overlap_with(self, other, assume_same_century=False):
        '''
        Test whether the Date has an overlap with the other Date or 
        DateRange object.

        Parameters
        ----------
            other : Date
                Any Date object.
            
            assume_same_century : bool
                If set True, trims the century value before comparing 
                the provided dates and assumes they are the same.
        '''
        
        if type(other) is Date:
            other = DateRange(other, other)
        elif type(other) is not DateRange:
            raise TypeError("Date object can only be compared with other Date" 
                            " or DateRange object with the method"
                            " overlap_with")
        return DateRange(self, self).overlap_with(other, assume_same_century)
        
    def __str__(self):
        res = ""
        
        # year
        if self.century_known:
            res = f'Year: {self.year}'
        else:
            res = f'Year: {self.year} (unknown century)'
        
        # month
        if self.precision == "month":
            res += f', Month: {self.month}'
        
        # day
        elif self.precision == "day":
            res += f', Month: {self.month}, Day: {self.day}'
        return res
    
    def __repr__(self):
        return f"Date({self})"
    
    def __eq__(self, other):
        if type(other) is not Date:
            raise TypeError("Date object can only be compared with other Date"
                            " objects")
        return self._parseddata == other._parseddata
    
    def __ne__(self, other):
        return not self == other
    
    def __lt__(self, other):
        if type(other) is not Date:
            raise TypeError("Date object can only be compared with other Date"
                            " objects")
        if self.year < other.year:
            return True
        elif self.precision == "year" or other.precision == "year":
            return False
        elif self.month < other.month:
            return True
        elif self.precision == "month" or other.precision == "month":
            return False
        elif self.day < other.day:
            return True
        return False      
    
    def __gt__(self, other):
        return other < self
    
    def __le__(self, other):
        return self < other or self == other            
    
    def __ge__(self, other):
        return other < self or self == other
    
    def get_json_data(self):
        return json.dumps(self._parseddata, ensure_ascii=False, indent=4)

class DateRange(object):
    '''
    Store a date range, based on two Date objects defining a closed 
    interval.
    '''
    
    def __init__(self, a, b):
        '''
        Builds the object from two Date objects setting the limits of 
        the range, which is considered as a closed interval.
        '''
        
        if a.is_empty() or b.is_empty():
            raise ValueError("cannot make a range with an 'empty' Date object")
        
        if a.precision != b.precision:
            raise ValueError("the two dates must have the same level of"
                             " precision")
        if a.century_known != b.century_known:
            raise ValueError("the two dates must have the same century_known"
                             " value")
        
        if a <= b:
            self._data = (a, b)
        else:
            self._data = (b, a)
    
    @property
    def start(self):
        return self._data[0]
    
    @property
    def end(self):
        return self._data[1]    
    
    @property
    def precision(self):
        return self._data[0].precision
    
    @property
    def precision_level(self):
        return self._data[0].precision_level
    
    @property
    def century_known(self):
        return self.start.century_known
    
    def get_isoformat(self):
        return f"{self.start.get_isoformat()}/{self.end.get_isoformat()}"
    
    def is_one_date(self):
        '''
        Check if start and end dates designate the same time point.
        '''
        
        return self.start == self.end
    
    def overlap_with(self, other, assume_same_century=False):
        '''
        Evaluate whether the provided date or date range overlaps with 
        the object's date range.
        
        Parameters
        ----------
            other : Date|DateRange
                A Date or a DateRange object of any precision. 
                            
            assume_same_century : bool
                Assume that the evaluated date or date range is of the 
                same century than that of the DateRange object. Does
                not take effect if both of the evaluated date ranges 
                have a known century.
        '''        
        
        if type(other) is Date:
            return other.overlap_with(self, assume_same_century)
        
        elif type(other) is DateRange:

            if self.century_known and other.century_known:
                
                # year
                years_overlap = overlap((self.start.year, self.end.year), 
                                        (other.start.year, other.end.year))
                
                # month
                if self.precision_level > 0 & other.precision_level > 0:
                    months_overlap = overlap((self.start.month, self.end.month), 
                                             (other.start.month, other.end.month))
                else:
                    months_overlap = True
                    
                # day
                if self.precision_level > 1 & other.precision_level > 1:
                    days_overlap = overlap((self.start.day, self.end.day), 
                                           (other.start.day, other.end.day))
                else:
                    days_overlap = True
                
                # final result
                return all((years_overlap, months_overlap, days_overlap))                
            
            # compare date as if there were of the same century, taking as 
            # self as reference if possible
            
            ### warning: could yield unexpected results if the date range 
            ### spans different century
            elif assume_same_century:
                if self.century_known:
                    other = DateRange(
                        Date((other.start.year%100) + (self.start.century*100), 
                              other.start.month, 
                              other.start.day),
                        Date((other.end.year%100) + (self.start.century*100), 
                              other.end.month, 
                              other.end.day))
                    return self.overlap_with(other)
                elif other.century_known:
                    a = DateRange(
                        Date((self.start.year%100) + (other.start.century*100), 
                              self.start.month, 
                              self.start.day),
                        Date((self.end.year%100) + (other.start.century*100), 
                              self.end.month, 
                              self.end.day))
                    return a.overlap_with(other)
                else:
                    return self.overlap_with(other)
            else:
                return False
        else:
            return TypeError("DateRange object can only be compared with other"
                             " Date or DateRange objects")
        
    def __repr__(self):
        return f"DateRange({self.start} - {self.end})"
    
# =============================================================================
# FUNCTIONS
# -----------------------------------------------------------------------------
def tag_date_pattern(pattern, **other_tags):
    '''
    Analyse the features of a date regular expression pattern (one 
    included by the class DatePatterns) and build DatePatternTags 
    including these features as different DatePatternTag objects.
    Keywords arguments can be use to complete the pattern description
    or override values.
    
    Parameters
    ----------
        year1 : str
            Interpreted year value. If the match is a date ranges, 
            this would store the earliest date.
        
        year2 : str
            Interpreted latest year value in a date range.

        month1 : str
            Interpreted month value. If the match is a date ranges, 
            this would store the earliest date.

        month2 : str
            Interpreted latest month value in a date range.

        day1 : str
            Interpreted day value. If the match is a date ranges, 
            this would store the earliest date.

        day2 : str
            Interpreted latest day value in a date range.

        pattern : regex.Pattern
            Compiled regular expression pattern (from the regex 
            module), that was used to parse the date value.

        match : regex.Match
            Match object from the regex module, corresponding to the 
            parsed date.

        score : int
            Match score, representing the information level. A higher 
            score indicates a higher information level.

        tags : DatePatternTags
            A series of tags describing the date format and its 
            precision level.
    '''
    
    # will be used to construct the DatePatternTags object
    tags = dict()
    
    # - fields in found order
    tags["fields"] = tuple(regex.findall(
                            "(?:year|month|day)(?:[12])", pattern))
    
    # - precision level
    tags["precision_level"] = -1
    if "day1" in tags["fields"]:
        tags["precision_level"] = 2
    elif "month1" in tags["fields"]:
        tags["precision_level"] = 1
    else:
        tags["precision_level"] = 0
    
    # - is it a date range?
    tags["is_range"] = any(("day2" in tags["fields"], 
                            "month2" in tags["fields"], 
                            "year2" in tags["fields"]))
    
    # - is it in US format?
    try:
        tags["is_us"] = (tags["fields"].index("month1") <
                         tags["fields"].index("day1"))
    except ValueError:
        tags["is_us"] = None
    
    tags.update(**other_tags)
    
    return DatePatternTags(**tags)

def find_date(text, **allow_tags):
    '''
    Attempts to find a date in a given text.

    Parameters
    ----------
        fields : str
            Which fields should be found in the matching text.
            Possible values: "year1", "year2", "month1", "month2", 
                             "day1", "day2"
        
        precision_level : int
            The minimum precision level of the date.
            Possible values: -1 (none), 0 (year), 1 (month), 2 (day)

        day_pattern : str
            Restrict the match to include the given day format.
            Possible value: "digit"

        month_pattern : str
            Restrict the match to include the given month format.
            Possible values: "digit", "roman", "literal"
        
        year_pattern : str
            Restrict the match to include the given year format.
            Possible values: "two-digit", "four-digit"
        
        is_us : bool
            Restrict the match to either US or non-US format.

        is_range : bool
            Restrict the match to either a single date or a date range.
    '''
    
    date_parser = DatePatterns(**allow_tags)
    return date_parser.find_date(text, get_span=True)
