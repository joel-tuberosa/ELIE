
'''
   This module contains classes and function related to geocoding. It 
   uses the package geopy package to search location in 
   http://www.geonames.org. 
'''

import regex, sys
import xml.etree.ElementTree as ET
from nltk import regexp_tokenize
from mfnb.utils import simplify_str, strip_accents
from geopy.geocoders import GeoNames
from urllib.request import urlopen

GEONAMES_USERNAME = "joel.tuberosa"

# =============================================================================
# CLASSES
# -----------------------------------------------------------------------------
class Distance(object):
    '''
    Store a distance value.
    '''
    
    pattern = regex.compile(r"(?P<value>[0-9]+)\s?(?P<unit>k?m|ft)", regex.I)

    def __init__(self, value, unit=None):
        '''
        Instanciate a Distance object from a provided value of a 
        provided unit. The value is stored internally as meters.

        Parameters
        ----------
            value : float | str
                A distance value, either in a numerical type or in a 
                string. The string can contain the unit specification.
        
            unit : str
                The unit, can reflect different unit systems. Possible
                values:
                    "m"  (meter)
                    "km" (kilometer)
                    "ft" (feet)
                If not provided, the unit must feature in the value.
        '''

        if type(value) is str:

            # value is a str, unit is provided with the parameter
            if value.isnumeric():
                value = float(value)

            # value and unit are provided within an expression such as 1m, 1km 
            # or 3ft
            else:
                m = self.pattern.fullmatch(value)
                if m is None:
                    raise ValueError("distance value could not be parsed from"
                                     " input str")
                value, unit = float(m.group("value")), m.group("unit").lower()

        # input value is a real number in any compatible format
        else:
            try:
                value = float(value)
            except ValueError:
                raise ValueError("input value must be either a str expression"
                                 " of a distance, or a real value")

        # verify that unit has been provided if needed
        if unit == "ft":
            value *= 3.2808399
        elif unit == "km":
            value *= 1000
        elif unit != "m":
            if unit is None:
                raise ValueError("unit must be provided either through the"
                                 " input expression or through the"
                                 " corresponding parameter.")
            else:
                raise ValueError(f'unrecognized unit: {repr(unit)}. Possible'
                                  ' units are "m", "km", or "ft".')

        # stored value
        self._value = value
        
    @property
    def meters(self):
        return self._value
    
    @property
    def feet(self):
        return self._value * 0.3048

    def __repr__(self):
        return f"Distance({self.meters:.03f}m)"
    
    def __float__(self):
        return self._value

    def __eq__(self, other):
        return float(self) == float(other)

class Degree(object):
    '''
    Store a degree value, that can be decomposed into minutes and 
    seconds.
    '''

    def __init__(self, degrees=0, minutes=0, seconds=.0):
        '''
        Instanciate a Degree object using the provided input values.

        Parameters
        ----------
            degrees : float
                Numerical value representing degrees.

            minutes : float
                Numerical value representig minutes (1/60th degree).

            seconds : float
                Numerical value representig seconds (1/60th minutes).
                
        '''

        # degrees
        value, degrees = degrees, int(degrees)
        rest = value - degrees

        # minutes
        value = minutes + 60*rest
        minutes = int(value)
        rest = value - minutes

        # seconds
        seconds = seconds + 60*rest

        self._data = {"degrees": degrees, 
                      "minutes": minutes,
                      "seconds": seconds,
                      "raw_value": degrees + (minutes + (seconds/60))/60}

    @property
    def degrees(self):
        return self._data["degrees"]

    @property
    def minutes(self):
        return self._data["minutes"]

    @property
    def seconds(self):
        return self._data["seconds"]
    
    @property
    def value(self):
        return self._data["raw_value"]
    
    def __str__(self):
        return f'''{self.degrees:d}°{self.minutes:d}'{self.seconds:0.1f}"'''
    
    def __repr__(self):
        return f'{self}'
        
class LatLng(object):
    '''
    Store a geographic coordinate (latitude and longitude).
    '''

    pattern = regex.compile(r"""
        \b(?<lat>
            (?P<lat_deg>\d+(?:\.\d+)?°)\s?  # degree
            (?P<lat_min>\d+(?:\.\d+)?')\s?  # minute
            (?P<lat_sec>\d+(?:\.\d+)?")?\s? # second
            (?P<lat_car>[CNЮS][A-Z]*)       # north/south
            ){e<=1:[°'",.*]}
            
            (?P<sep>[,.]\s+|\s+)            # separator    
    
        \b(?<lng>
            (?P<lng_deg>\d+(?:\.\d+)?°)\s?  # degree
            (?P<lng_min>\d+(?:\.\d+)?')\s?  # minute
            (?P<lng_sec>\d+(?:\.\d+)?")?\s? # second
            (?P<lng_car>[ВЗEW][A-Z]*)       # east/west
            ){e<=1:[°'",.*]}\b
         """, flags=regex.X | regex.BESTMATCH | regex.I)
    
    def __init__(self, value):
        '''
        Parse the input str to identify latitude and longitude 
        notations.
        '''

        # initiate from an str containing a latitude/longitude notation
        if type(value) is str:
            coordinates = read_latlng(value)
            self._data = (coordinates["lat"], coordinates["lng"])

        # initiate from a 2-element array containing latitude and longitude as
        # float values
        elif len(value) == 2 and all( type(x) is float for x in value ):
            
            # latitude
            lat = (Degree(abs(value[0])), "N" if value[0] >= 0 else "S")
            
            # longitude
            lng = (Degree(abs(value[1])), "E" if value[1] >= 0 else "N")
            self._data = (lat, lng)
    
    @property
    def lat(self):
        '''
        Decimal latitude value.
        '''
        
        value = self._data[0][0].value
        if self._data[0][1] == "N":
            return value
        else:
            return value*-1
    
    @property
    def lng(self):
        '''
        Decimal longitude value.
        '''
        
        value = self._data[0][0].value
        if self._data[1][1] == "E":
            return value
        else:
            return value*-1

    @property
    def latlng(self):
        '''
        Tuple with decimal latitude and longitude values. 
        '''
        
        return (self.lat, self.lng)

    def __str__(self):
        return (f"{self._data[0][0]}{self._data[0][1]}"
                f" {self._data[1][0]}{self._data[1][1]}")
    
    def __repr__(self):
        return f"LatLng({self})"

# =============================================================================
# FUNCTIONS
# -----------------------------------------------------------------------------
def read_latlng(s):
    '''
    Parse latitude and longitude coordinate notation in the input str.
    '''
    
    m = LatLng.pattern.fullmatch(s)
    if m is None:
        raise ValueError(f'Expression "{s}" does not match a known'
                          ' latitude/longitude notation syntax')
    
    numberp = regex.compile(r"\d+(?:\.\d+)?")
    def get_float(x, p=numberp): 
        return float(p.match(x).group())
    
    data = {"lat": {}, "lng": {}}
    for coordinate in data:
        
        # degrees
        degrees = get_float(m.group(f"{coordinate}_deg"))
        
        # minutes
        minutes = get_float(m.group(f"{coordinate}_min"))

        # seconds 
        if m.group(f"{coordinate}_sec") is None:
            seconds = 0
        else:
            seconds = get_float(m.group(f"{coordinate}_sec")) 
            
        # cardinal
        cardinal = guess_cardinal(m.group(f"{coordinate}_car").upper(), 
                                    restrict="NS" 
                                            if coordinate == "lat" 
                                            else "WE")
        data[coordinate] = (Degree(degrees, minutes, seconds), cardinal)
    return data

def degree_decomp(value):
    '''
    Decompose a degree value into degrees, minutes and seconds. 
    '''

    # degrees
    degrees = int(value)
    rest = value - degrees

    # minutes
    value = 60*rest
    minutes = int(value)
    rest = value - minutes

    # seconds
    seconds = 60*rest

    return {"degrees": degrees, 
            "minutes": minutes,
            "seconds": seconds}

def guess_cardinal(value, restrict="NSEW"):
    '''
    Guess the cardinal according to the first letter of 'value'.

    Parameters
    ----------
        value : str
            The putative cardinal notation.

        restrict : str
            A character set restricting the search to given cardinals.
    '''
    
    if value[0] in "CN" and "N" in restrict:
        return "N"
    elif value[0] in "ЮS" and "S" in restrict:
        return "S"
    elif value[0] in "ВE" and "E" in restrict:
        return "E"
    elif value[0] in "ЗW" and "W" in restrict:
        return "W"
    else:
        raise ValueError(f'unrecognized cardinal: "{value}"')

def find_lat_lng(s, get_span=True):
    '''
    Find latitude and longitude str in a text.

    Parameters
    ----------
        s : str
            The text to be parsed.

        get_span : bool
            If set True, the function returns the span of the match in
            the input text along with the match, in a tuple.
    '''
    
    m = LatLng.pattern.search(s)
    if m is None:
        result = span = None
    else:
        result = LatLng(m.group())
        span = m.span()
    return (result, span) if get_span else result

def find_distance(s, get_span=True):
    '''
    Find a distance in a text.
    
    Parameters
    ----------
        s : str
            The text to be parsed.

        get_span : bool
            If set True, the function returns the span of the match in
            the input text along with the match, in a tuple.
    '''

    m = Distance.pattern.search(s)
    if m is None:
        result, span = None
    else:
        result = Distance(m.group())
        span = m.span()
    return (result, span) if get_span else result

def parse_geo(s, username=GEONAMES_USERNAME):
    '''
    Attempt to find a location in the provided string by sending 
    queries to GeoNames using a registered account.

    Parameters
    ----------
        s : str
            Text to be parsed.
        
        username : str
            GeoNames user account name.
    '''

    geocoder = GeoNames(username=username)

    # 1- attempt to find a latitude-longitude coordinate
    latlng, span = find_lat_lng(s)
    if latlng is not None:
        return (latlng, geocoder.reverse(str(latlng)).address, span)

    # 2- attempt to find a location using GeoNames
    # extract words of more than 3 characters
    s = simplify_str(s)
    tokens = regexp_tokenize(s, pattern="[A-z]{3,}")

    # get location hints from all possible tokens n-grams, stop at the first 
    # found location
    hit, query = parse_geo_from_ngrams(geocoder, tokens)
    if hit is None:
        return (None, None, None)

    # retrieve the original text
    p = regex.compile(r"(?:.*?)".join( fr"(?:{token})"  
                                        for token in query ),
                      regex.MULTILINE)
    m = p.search(strip_accents(s.lower()))
    if m is None:
        sys.stderr.write("parse_geo warning: impossible to retrieve the"
                         " original text.\n")
        span = (None, None)
    else:
        span = m.span()

    return (LatLng((hit.latitude, hit.longitude)), hit.address, span)

def parse_geo_from_ngrams(geocoder, tokens):
    '''
    Attempts to find a geolocation with the provided tokens, by using 
    queries constituted of all possible n-grams formed with successive 
    tokens.

    Parameters
    ----------
        geocoder : pygeo.geocoders.GeoNames
            Geocoder instance for GeoNames.

        tokens : list
            List of tokens (str) that will be use to build the queries 
            for GeoNames. 
    '''

    for l in range(len(tokens), 0, -1):
        hits = []
        queries = dict()
        for i in range(len(tokens)-l+1):
            query = tokens[i:i+l]
            hit = geocoder.geocode(" ".join(query))
            if hit is not None:
                hits.append(hit)

                # associated the query with hit ID for further retrieval
                queries[hit.raw["geonameId"]] = query
        
        # if no hits were found, continue with smaller n-grams
        if not hits:
            continue
            
        # group the hits by country
        groups = GeoNames_group_by_country(hits)

        # sort each group by feature rank
        for country in groups:
            groups[country].sort(key=GeoNames_feature_rank)

        # unless this is the only group, do not keep location that are above 
        # country level
        if list(groups.keys()) == ["no_country"]:
            hits = groups["no_country"]

        # otherwise, keep the group that countains the highest information 
        # level (i.e country over city)
        else:
            try:
                del groups["no_country"]
            except KeyError:
                pass
            hits = sorted(groups.values(), 
                          key=lambda group: GeoNames_feature_rank(group[0]))[0]
        
        # keep the hit with the most precise information level
        hit = hits[-1]

        # stop the search and return the best hit
        return (hit, queries[hit.raw["geonameId"]])
         
    return (None, [])

def GeoNames_feature_rank(hit):
    '''
    Return the ranking of the GeoNames result's feature. 
    '''
    
    fcl_order = [
        "A", #country, state, region,...
        "P", #city, village,...
        "H", #stream, lake, ...
        "L", #parks,area, ...
        "T", #mountain,hill,rock,...
        "U", #undersea
        "V", #forest,heath,...
        "R", #road, railroad
        "S"  #spot, building, farm
        ]
    
    return fcl_order.index(hit.raw["fcl"])

def GeoNames_group_by_country(hits):
    '''
    Groups GeoNames results by country.
    '''

    groups = dict()
    for hit in hits:

        # try to retrieve the country name, if the location is affiliated to a
        # country
        try:
            country = hit.raw["countryCode"]
        except KeyError:
            country = "no_country"

        # regroup hits by country
        try:
            groups[country].append(hit)
        except KeyError:
            groups[country] = [hit]
    return groups

def GeoNames_iscountry(hit):
    '''
    Returns True if the evaluated GeoNames result is a country.
    '''

    return hit.raw["name"] == hit.raw["countryName"]

def GeoNames_hierarchy(hit, username=GEONAMES_USERNAME):
    '''
    Retrieves the upper hierarchy of the provided hit.
    '''

    url = ("http://api.geonames.org/hierarchy?"
           f"geonameId={hit.raw['geonameId']}&"
           f"username={username}")
    with urlopen(url) as page:
        root = ET.fromstring(page.read().decode())
    return [ entity.find("name").text 
              for entity in root.findall("geoname") ]
