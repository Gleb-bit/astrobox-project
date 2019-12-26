# -*- coding: utf-8 -*-
import warnings

from .base import *

try:
    from .local import *
except ImportError:
    warnings.warn(f'No settings.local module. You can make it empty to avoid this message.')
