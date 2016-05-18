from __future__ import absolute_import, print_function

import unittest
import os
import os.path
import shutil
import tempfile


class StoreTestCase(unittest.TestCase):
  def setUp(self):
    self.base_path = tempfile.mkdtemp(prefix=self.__class__.__name__)
    self.store = self.store_cls.initialize_directory_structure(self.base_path)
    self.store_path = os.path.join(self.base_path, self.store_cls.DIRECTORY_NAME)
    self.previous_pwd = os.getcwd()
    os.chdir(self.store_path)

  def tearDown(self):
    shutil.rmtree(self.base_path)
    os.chdir(self.previous_pwd)
