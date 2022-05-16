
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

import regex, sys

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
    
        m = LatLng.pattern.search(value.upper())
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

def find_lat_lng_str(value, get_span=True):
    '''
    Find latitude and longitude str in a text.
    '''
    
    m = LatLng.pattern.search(value.upper())
    if m is None:
        result = span = None
    else:
        result = m.group()
        span = m.span()
    return (result, span) if get_span else result
