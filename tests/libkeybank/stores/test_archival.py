from __future__ import absolute_import, print_function

import unittest
import os
import shutil
import tempfile

from libkeybank.stores.archival import ArchivalStore
from libkeybank.utils import chdir

from ...helpers import execute


class TestArchivalStore(unittest.TestCase):
  def setUp(self):
    self.base_path = tempfile.mkdtemp(prefix="test-fake-kb-archival-store")
    self.store = ArchivalStore.initialize_directory_structure(self.base_path)
    self.store_path = os.path.join(self.base_path, ArchivalStore.DIRECTORY_NAME)
    self.previous_pwd = os.getcwd()
    os.chdir(self.store_path)

  def test_setup_has_locked_manifest_and_git(self):
    self.assertTrue(os.path.isdir(".git"))
    self.assertTrue(os.path.isfile("manifest.lock.json"))
    with open("manifest.lock.json") as f:
      content = f.read().strip()

    self.assertEqual("{}", content)

  def tearDown(self):
    shutil.rmtree(self.base_path)
    os.chdir(self.previous_pwd)
