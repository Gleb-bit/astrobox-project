# -*- coding: utf-8 -*-

from .base import *

try:
    from .local import *
except ImportError:
    raise Warning(f'No settings.local module. Skipping.')
