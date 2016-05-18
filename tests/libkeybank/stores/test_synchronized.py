from __future__ import absolute_import, print_function

import json
import os
import random

from libkeybank.stores.synchronized import SynchronizedStore
from libkeybank.utils import execute_with_postprocessing

from .helpers import StoreTestCase


class TestSynchronizedStore(StoreTestCase):
  store_cls = SynchronizedStore
