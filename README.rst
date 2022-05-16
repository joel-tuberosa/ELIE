mfnb
========================================================================
*A Python package for the Berlin Natural History Museum*

.. contents ::

Introduction
------------
This package contains a serie of classes and functions to handle
specimen label information. Its installation also includes scripts 
designed for label parsing and classification.

Installation
------------
1. Download python-mfnb.
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
   uses the third-party package pygeo package to search localization in
   http://www.geonames.org. 
   
* mfnb.labeldata
    This module contains classes and functions to handle and integrate
    information extracted from specimen labels. It allows to build 
    searchable label databases using token extraction and text feature 
    scoring. This module uses the third-party packages regex, sklearn, 
    nltk and leven.
    
* mfnb.name
    This module contains classes and functions designed to recognize 
    and store people names information. It uses the third-party 
    packages nltk and regex.

* mfnb.utils
    This module gathers generic functions for text data handling, 
    manipulation and formatting.
    
Scripts
-------
For usage information, run any of these scripts with the option --help.

* make_collecting_events.py
   Build collecting event objects from an input table and store the 
   data in a JSON file.

* make_labels.py
   Build label objects from an input table and store the data in a JSON 
   file.
   
* match_collecting_events.py
   Match labels with collecting events according to the resemblance of 
   their raw text data. Dates can be parsed in the label data to limit
   the search to collecting event in the same date range.

* search_labels.py
   Text search in a collection of labels.

* sort_labels.py
   Cluster label based on text similarity and parse localisation, date
   and collector's names in the raw text.
