from __future__ import absolute_import, print_function

import unittest
import os
import shutil
import tempfile

from libkeybank.gitlite import Repo
from libkeybank.utils import chdir

from ..helpers import TESTDATA_PATH, execute


class GitliteTest(unittest.TestCase):
  def setUp(self):
    self.basepath = tempfile.mkdtemp(prefix="keybank-gitlite-test")
    self.corrupted_git_repo_path = os.path.join(self.basepath, "corrupted-git-repos")
    shutil.copytree(os.path.join(TESTDATA_PATH, "corrupted-git-repos"), self.corrupted_git_repo_path)

    self.corrupted_repos = os.listdir(self.corrupted_git_repo_path)
    self.corrupted_repos = map(lambda d: os.path.join(self.corrupted_git_repo_path, d), self.corrupted_repos)

  def test_init(self):
    repo_path = os.path.join(self.basepath, "inittest")
    repo = Repo.init(repo_path)
    self.assertEqual(repo_path, repo.path)

    with chdir(repo_path):
      with execute("git status") as p:
        self.assertEqual(0, p.returncode)

      self.assertTrue(os.path.isdir(".git"))

  def test_commit_all(self):
    repo_path = os.path.join(self.basepath, "committest")
    repo = Repo.init(repo_path)
    with chdir(repo_path):
      with open("testfile", "w") as f:
        f.write("123")

      repo.commit_all("added a file", "test <test@test.com>")

      with execute("git log --pretty=oneline --no-color") as p:
        self.assertEqual(0, p.returncode)
        lines = p.stdout.readlines()

      self.assertEqual(1, len(lines))
      self.assertTrue("added a file" in lines[0].decode("utf-8"))

  def test_fsck(self):
    pass

  def tearDown(self):
    shutil.rmtree(self.basepath)
