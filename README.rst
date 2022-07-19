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

`git clone https://code.naturkundemuseum.berlin/collection-mining/python-mfnb`

2. cd in python-mfnb/

`cd python-mfnb`
   
3. Install with pip, which will automatically fetch the requirements if
   you don't have it already.

`pip install .`

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

Example of usage
----------------

**Problem:** You dispose of a set of collecting event label transcripts (transcripts.json) on the one side and have already identified a few collecting events corresponding to this collection (col_ev.json). You want to attribute the new labels to the existing collecting events and identify the labels for which a new collecting event must be written. 

**Step 1)** Cluster transcripts by similarity to regroup labels pertaining to the same collecting events. In the same time, parse the transcripts to identify collecting event information:

    `sort_labels.py -d -c collectors.json -g transcripts.json >sorted_transcripts.txt`

* Option `-d` will activate date string parsing and add two output fields with the identified verbatim and the interpreted colleting event date.
* Option `-c` collectors.json will search names of collectors or collecting entities from the database collectors.json in the transcripts and add two output fields with the identified verbatim and the interpreted collector names.
* Option `-g` will try to guess the collecting event location from the remaining text by searching the terms in the GeoNames database via the online API. Beware that the current default setting uses a free account (login: joel.tuberosa) which is limited to 1000 requests per days. If transcripts within the groups are mostly identical, you can use the option `-v pick`, which will select a representative transcript amongst each group, on which parsing will be performed.

Parsing is optional here, it is only meant to help later collecting event determination.

**Step 2)** Identify the closest collecting event for each transcript using full-text search on the representative transcript attached to each collecting event.

    `match_collecting_events.py -d -p col_ev.json transcripts.json >matched_col_ev.txt`

* Option `-d` will activate date string parsing and for each transcript where a date was identified, limit the search to collecting event with an overlapping date.
* Option `-p` will allow transcripts with an identified date but no matching collecting event in that date range to be search against the rest of the collecting events anyway. This allows to have a matching score anyway for later evaluation, and sometimes also allows to save some matches when the date parsing is faulty.

This will return a table showing input transcripts along with matching collecting events and a hit score that represent the hit accuracy. This score takes a value between 0 and 1, with higher value indicating higher accuracy.

**Step 3)**	Evaluate the correspondence between identified transcripts clusters and existing collecting events. This is done by computing a confidence score for each cluster, representing how much the cluster correspond to the most frequently matched collecting event among its transcripts. This confidence score is calculated as a product of the frequency of the most matched collecting events and its average hit score.

    `checkout_collecting_events.py sorted_transcripts.txt matched_col_ev.txt >checkout.txt`

With the output of this program, you should be able to identify clear correspondences between transcripts clusters and collecting event. For example, if you spot a cluster of 20 transcripts that correspond to a given collecting event with a confidence score close to 1, you can trustfully annotate the corresponding labels as pertaining to that collecting event. On the contrary, if these 20 transcripts are assigned to a given collecting event with a lower confidence score, it would be worth to go back to individual transcripts best matches to figure out whether they all pertain to the same collecting event or not, and whether you need to create a new collecting event for any of them. Finally, this program also gives you the collecting event that were not matched with any transcripts, and inversely.

**Refinment:** The above example would work well with a set of faithful transcripts and with easily differentiable transcript groups. In other cases, you could face the following issues:

**Case 1)** Transcripts typographic errors or misinterpreted text makes the whole dataset noisy. The default full-text search scoring method relies on near-exact token matches and can be too stringent. Depending on your clustering results, you can alternatively run the following command, which resort on Levenshtein distances to aggregate similar label together.

    `sort_labels.py -d -c collectors.json -g transcripts.json -s 0.3 -r >sorted_transcripts.txt`

* Option `-s 0.3` lower the similarity threshold for aggregation (default is 0.8).
* Option `-r` orders to compute pairwise Levenshtein distances within the aggregated group and to attempt to find subcluster using a K-medoid clustering approach.

In addition, if parsing is impaired by transcription errors, you try the option `-v alignment` to align the transcripts and generate a character frequency based consensus transcript on which data will be parsed.

    `match_collecting_events.py -d -p col_ev.json transcripts.json -s l >matched_col_ev.txt`

* Option `-s l` indicates to use levenshtein distance instead of token-based scoring to find the best hits.

**Case 2)** Very similar transcripts, that just differ from a single number (for instance a different day), that could nevertheless be very relevant, could be seen as more similar than they actually are with the default search method. To overcome this, the above method, using levenshtein distance, could be a solution. If the transcripts are faithfull enough, you could also try a different aggregation method, based on the parsed information using the following command.

    `sort_labels.py -d -c collectors.json -g transcripts.json -p >sorted_transcripts.txt`

* Option `-p` orders to parse the required information (here: dates, collectors and locations) and aggregate labels that contain the same information.
