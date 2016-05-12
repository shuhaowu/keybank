from __future__ import absolute_import, print_function

import unittest
import json
import os
import random
import shutil
import tempfile

from libkeybank.stores.archival import ArchivalStore
from libkeybank.utils import execute_with_postprocessing


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
    self.assert_number_of_commit_equals(1)

  def test_commits_will_update_manifest(self):
    # add file
    with open("testfile", "w") as f:
      f.write("hello world")

    files_changed = self.store.commit(dry_run=True)
    self.assertEqual(0, len(files_changed["changed"]))
    self.assertEqual(0, len(files_changed["deleted"]))
    self.assertEqual(1, len(files_changed["added"]))
    self.assertEqual({"/testfile"}, files_changed["added"])

    self.assert_manifest_lock_json_is({})
    self.assert_number_of_commit_equals(1)

    self.store.commit()
    self.assert_manifest_lock_json_is({"/testfile": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"})
    self.assert_number_of_commit_equals(2)

    # update file

    with open("testfile", "w") as f:
      f.write("jello world")

    files_changed = self.store.commit(dry_run=True)
    self.assertEqual(1, len(files_changed["changed"]))
    self.assertEqual(0, len(files_changed["deleted"]))
    self.assertEqual(0, len(files_changed["added"]))
    self.assertEqual({"/testfile"}, files_changed["changed"])

    self.assert_manifest_lock_json_is({"/testfile": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"})
    self.assert_number_of_commit_equals(2)

    self.store.commit()
    self.assert_manifest_lock_json_is({"/testfile": "cf1b2b8bccc960a8ffd092ca60843c35e8be79b42ab083f55c9e7375d46f2151"})
    self.assert_number_of_commit_equals(3)

    # delete file
    os.unlink("testfile")
    files_changed = self.store.commit(dry_run=True)
    self.assertEqual(0, len(files_changed["changed"]))
    self.assertEqual(1, len(files_changed["deleted"]))
    self.assertEqual(0, len(files_changed["added"]))
    self.assertEqual({"/testfile"}, files_changed["deleted"])

    self.assert_manifest_lock_json_is({"/testfile": "cf1b2b8bccc960a8ffd092ca60843c35e8be79b42ab083f55c9e7375d46f2151"})
    self.assert_number_of_commit_equals(3)

    self.store.commit()
    self.assert_manifest_lock_json_is({})
    self.assert_number_of_commit_equals(4)

  def test_verify(self):
    with open("testfile", "w") as f:
      f.write("hello world")

    self.store.commit()

    status = self.store.verify()
    self.assertTrue(status.is_good())

    with open("testfile", "w") as f:
      f.write("jello world")

    status = self.store.verify()
    self.assertFalse(status.is_good())
    self.assertTrue(status.git_repo_status)
    self.assertFalse(status.files_overall_status)
    self.assertEqual("changed", status.files_errors["/testfile"])

    os.unlink("testfile")
    status = self.store.verify()
    self.assertFalse(status.is_good())
    self.assertTrue(status.git_repo_status)
    self.assertFalse(status.files_overall_status)
    self.assertEqual("removed", status.files_errors["/testfile"])

    while True:
      d = random.choice(os.listdir(os.path.join(".git", "objects")))
      d = os.path.join(".git", "objects", d)
      stuff = os.listdir(d)
      if len(stuff) > 0:  # delete a directory with things inside...
        break

    shutil.rmtree(d)

    status = self.store.verify()
    self.assertFalse(status.is_good())
    self.assertFalse(status.git_repo_status, "deleted {} (contains {}) but git repo is still intact?".format(d, stuff))
    self.assertFalse(status.files_overall_status)
    self.assertEqual("removed", status.files_errors["/testfile"])

  def assert_manifest_lock_json_is(self, m):
    with open("manifest.lock.json") as f:
      manifest = json.load(f)
      self.assertEqual(m, manifest)

  def assert_number_of_commit_equals(self, n):
    with execute_with_postprocessing("git log --pretty=oneline --no-color") as p:
      commits = p.stdout.read().decode("utf-8").strip().split("\n")
      self.assertEqual(n, len(commits))

  def tearDown(self):
    shutil.rmtree(self.base_path)
    os.chdir(self.previous_pwd)
