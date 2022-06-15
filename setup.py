#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name='mfnb',
    description='A Python package from the Natural History Museum of Berlin'
                ' for digitalized specimen label classification.',
    url='https://github.com/joel-tuberosa/python-mfnb',
    author='Joel Tuberosa',
    author_email='joel.tuberosa@unige.ch',
    license='GNU',
    install_requires=[
          'nltk',
          'dateparser',
          'sklearn',
          'regex',
          'leven',
          'scikit-learn-extra',
          'kneed'
      ],
    packages=["mfnb"],
    scripts=['scripts/make_collecting_events.py', 
             'scripts/match_collecting_events.py',
             'scripts/make_labels.py',
             'scripts/search_labels.py',
             'scripts/sort_labels.py',
             'scripts/checkout_collecting_events.py',
             'scripts/subset_db.py'
            ],
    platforms=['any'],
    version='1.0a1',
    classifiers=[
        'Development Status :: 1 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: >=3.7',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        ],
    python_requires='>=3.7',
      )
