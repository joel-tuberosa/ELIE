mfnb
========================================================================
*A Python package for the Berlin Natural History Museum*

.. contents ::

Introduction
------------
This package contains a serie of classes and functions to handle
collecting event label information. Its installation also includes 
scripts designed for collecting event label parsing and classification.

Installation
------------
1. Clone python-mfnb from https://code.naturkundemuseum.berlin/collection-mining/python-mfnb.

::

    git clone https://code.naturkundemuseum.berlin/collection-mining/python-mfnb

2. cd in python-mfnb/

::

   cd python-mfnb
   
3. Install with pip, which will automatically fetch the requirements if
   you don't have it already.

::

   pip install .

Modules
-------
* mfnb.date 
    This module contains classes and functions related to time data. It
    uses fuzzy regular expressions from the third party package regex to
    find dates within OCR extracted text and the dateparser package to 
    interpret the diversity of date formats. The Date and DateRange
    classes allow to store dates with various precision levels, 
    reflecting the data status collected among labels.

* mfnb.geo
   This module contains classes and function related to geocoding. It 
   uses the package geopy package to search location in 
   http://www.geonames.org. 
   
* mfnb.labeldata
    This module contains classes and functions to handle and integrate
    information extracted from specimen labels. It allows to build 
    searchable text databases using token extraction and text feature 
    scoring. This module uses the packages regex, sklearn, nltk and
    leven.
    
* mfnb.name
    This module contains classes and functions designed to store people
    names or entity information as well as matching abbreviated text
    with full text. It uses the packages nltk and regex.

* mfnb.utils
    This module gathers generic functions for text data handling, 
    manipulation and formatting.
    
Scripts
-------
For usage information, run any of these scripts with the option --help.

* checkout_collecting_events.py
   Identify inconsistensies between the outputs of sort_labels.py and 
   match_collecting_events.py in order to validate collecting event 
   attributions.

* make_collecting_events.py
   Build collecting event objects from an input table and store the 
   data in a JSON file for usage with match_collecting_events.py.

* make_labels.py
   Build label objects from an input table and store the data in a JSON 
   file for usage with sort_labels.py, search_labels.py and
   match_collecting_events.py.
   
* match_collecting_events.py
   Match labels with collecting events using full-text search and 
   similarity scoring. Dates can be parsed in the label data to limit
   the search to collecting event with overlapping dates.

* search_labels.py
   Full-text search in a collection of labels.

* sort_labels.py
   Cluster label based on text similarity and parse localisation, date
   and collector's names in the raw text.

* subset_db.py
   Subset a label or a collecting event database in JSON format.

* table_export.py
   Make a TSV file from a JSON file containing a label or a collecting
   event database.

Dataset preparation
-------------------

**Transcripts**

These are raw transcripts of collecting event labels. They are stored in a JSON file containing a list of dictionary objects, each one having two keys:

* “ID”, a string used as a unique identifier for the transcript.
* "text”, the transcribed text.

Example:  

::

    [
        {
            "ID": "coll.mfn-berlin.de_u_c2ebe3",
            "text": "Abessinien Dire Daoua 3.-6.1936 Uhlenhuth"
        }, …
    ]

You can convert a dataset in tabular format, for instance, a TSV file with two columns containing respectively the ID and the text of each transcript, into this JSON format using the script make_labels.py.

**Collecting Events**

These are individual collecting events, a unique combination of a location, a date and collectors’ names. They are stored in a JSON file containing a list of dictionary objects, each one having five keys:

* “ID”, a unique identifier for the collecting event.
* “location”, an address and/or a longitude/latitude coordinate
* “date”, a date
* “collector”, one or more collector names or alternatively, a responsible entity (for instance, the name of an expedition)
* “text”, a representative transcript from which this information was collected.

Example:

::
    [
        {
            "ID": "BeesNbytes00001",
            "location": "Argentina, Buenos Aires",
            "date": "15.12.1905",
            "collector": "Frank",
            "text": "Argentina Buen. Aires 15. 12. 05 Frank”
        }, …
    ]

You can convert a dataset in tabular format, for instance, a TSV file containing each of these different fields into this JSON format using the script make_collecting_event.py.

**Collectors**

These are people or collecting entities. They are stored in a JSON file containing a list of dictionary object with the following keys:

* “ID”, a unique identifier for the collecting event.
* “name”, the surname of the collector or the name of the entity.
* “firstname”, for humans, the firstname of the collectors.
* “metadata”, a dictionary object with other information attached to the person.

Example:

::
    [
        {
            "ID": "collector00001",
            "name": "Walz",
            "firstname": "A J",
            "metadata": {
                "entity_type": "person"
            }
        }, …
    ]
