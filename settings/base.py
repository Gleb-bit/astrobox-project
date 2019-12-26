# -*- coding: utf-8 -*-
import os

PROJECT_PATH = os.path.dirname(os.path.dirname(__file__))

ELO_COEFFICIENTS = ((1000, 10), (700, 20), )
INITIAL_RATING = 700

DB_URL = f'sqlite:///{PROJECT_PATH}/astro.sqlite'

BATTLES_LOG = os.path.join(PROJECT_PATH, 'LOCAL_LOGS.md')
RATING_FILE = os.path.join(PROJECT_PATH, 'LOCAL_RATING.md')
