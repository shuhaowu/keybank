from __future__ import absolute_import, print_function

import json
import os
import random
import shutil

from libkeybank.stores.archival import ArchivalStore
from libkeybank.utils import execute_with_postprocessing

from .helpers import StoreTestCase


class TestArchivalStore(StoreTestCase):
  store_cls = ArchivalStore

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

    self.store.commit(config=None)
    self.assert_manifest_lock_json_is({"/testfile": "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"})
    self.assert_number_of_commit_equals(2)

    # update file

    with open("testfile", "w") as f:
      f.write("jello world")

    self.store.commit(config=None)
    self.assert_manifest_lock_json_is({"/testfile": "cf1b2b8bccc960a8ffd092ca60843c35e8be79b42ab083f55c9e7375d46f2151"})
    self.assert_number_of_commit_equals(3)

    # delete file
    os.unlink("testfile")

    self.store.commit(config=None)
    self.assert_manifest_lock_json_is({})
    self.assert_number_of_commit_equals(4)

  def test_verify(self):
    with open("testfile", "w") as f:
      f.write("hello world")

    self.store.commit(config=None)

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

  def test_nothing_to_commit(self):
    raise NotImplementedError

  def assert_manifest_lock_json_is(self, m):
    with open("manifest.lock.json") as f:
      manifest = json.load(f)
      self.assertEqual(m, manifest)

  def assert_number_of_commit_equals(self, n):
    with execute_with_postprocessing("git log --pretty=oneline --no-color") as p:
      commits = p.stdout.read().decode("utf-8").strip().split("\n")
      self.assertEqual(n, len(commits))
