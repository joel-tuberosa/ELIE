
'''
   This module contains classes and function related to geocoding. It 
   uses the third-party package pygeo package to search localization in
   http://www.geonames.org. 
'''

# known conventions
# 40° 31' 21" North by 105° 5' 39" West
# 40 31 21 N, 105 5 39 W
# 403121N, 1050539W
# 403121, 1050539
# 

from multiprocessing.sharedctypes import Value
import regex, sys

class Distance(object):
    '''
    Store a distance value.
    '''
    
    pattern = regex.compile(r"(?P<value>[0-9]+)\s?(?P<unit>k?m|ft)", regex.I)

    def __init__(self, value, unit=None):

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

class LatLng(object):
    
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
         """, flags=regex.X | regex.BESTMATCH)
    
    ### include a pattern with -+ coordinates (without NSWE)
    
    def __init__(self, value):
        '''
        Parse the input str to identify latitude and longitude 
        coordinates.
        '''
    
        m = LatLng.pattern.fullmatch(value.upper())
        if m is None:
            raise ValueError(f'Coordinates could not be found in "{value}"')
        
        numberp = regex.compile(r"\d+(?:\.\d+)?")
        get_float = lambda x: float(numberp.match(x).group())
        
        ### Convert to int and pass the division remaining to the 
        ### subsequent value. Round seconds.
        self._data = {
            "lat": {
                "degrees": get_float(m.group("lat_deg")),
                "minutes": get_float(m.group("lat_min")),
                "seconds": get_float(m.group("lat_sec")) 
                    if m.group("lat_sec") is not None else 0,
                "cardinal": guess_cardinal(m.group("lat_car")),
                   },
            "lng": {
                "degrees": get_float(m.group("lng_deg")),
                "minutes": get_float(m.group("lng_min")),
                "seconds": get_float(m.group("lng_sec")) 
                    if m.group("lng_sec") is not None else 0,
                "cardinal": guess_cardinal(m.group("lng_car"))
                    }
                }
    
    @property
    def lat(self):
        '''
        Returns decimal latitude value.
        '''
        
        value = (self._data["lat"]["degrees"]    +
                 self._data["lat"]["minutes"]/60 + 
                 self._data["lat"]["seconds"]/60)
        value *= 1 if self._data["lat"]["cardinal"] == "N" else -1
        return value
    
    @property
    def lng(self):
        '''
        Returns decimal longitude value.
        '''
        
        value = (self._data["lng"]["degrees"]    +
                 self._data["lng"]["minutes"]/60 + 
                 self._data["lng"]["seconds"]/60)
        value *= 1 if self._data["lgn"]["cardinal"] == "E" else -1
        return value

    @property
    def latlng(self):
        return (self.lat, self.lng)

    def __str__(self):
        return (f'{self._data["lat"]["degrees"]}°'
                f"{self._data['lat']['minutes']}'" 
                f'{self._data["lat"]["seconds"]}"'
                f'{self._data["lat"]["cardinal"]}"'
                ' '
                f'{self._data["lng"]["degrees"]}°'
                f"{self._data['lng']['minutes']}'" 
                f'{self._data["lng"]["seconds"]}"'
                f'{self._data["lng"]["cardinal"]}"'
                )
        
def guess_cardinal(value):
    '''
    Guess the cardinal according to the first letter of 'value'.
    '''
    
    if value[0] in "CN":
        return "N"
    elif value[0] in "ЮS":
        return "S"
    else:
        raise ValueError(f'unrecognized cardinal: "{value}"')

def find_lat_lng(s, get_span=True):
    '''
    Find latitude and longitude str in a text.
    '''
    
    m = LatLng.pattern.search(s.upper())
    if m is None:
        result = span = None
    else:
        result = m.group()
        span = m.span()
    return (result, span) if get_span else result

def find_distance(s, get_span=True):
    '''
    Find a distance in a text.
    '''

    m = Distance.pattern.search(s)
    if m is None:
        result, span = None
    else:
        result = m.group()
        span = m.span()
    return (result, span) if get_span else result