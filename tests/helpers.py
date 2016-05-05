from __future__ import absolute_import, print_function

from contextlib import contextmanager
import os.path
import subprocess
import shutil
import tempfile
import unittest

TESTS_PATH = os.path.dirname(os.path.abspath(__file__))
TESTDATA_PATH = os.path.join(TESTS_PATH, "testdata")


@contextmanager
def execute(command):
  p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  p.stdin.close()
  p.wait()
  try:
    yield p
  finally:
    p.stdout.close()


class StoresTestCase(unittest.TestCase):
  store_cls = None

  def setUp(self):
    self.store_path = tempfile.mkdtemp(prefix="keybank.{}".format(self.__class__.__name__))
    self.store = self.__class__.store_cls.initialize_directory_structure(self.store_path)

  def tearDown(self):
    shutil.rmtree(self.store_path)
