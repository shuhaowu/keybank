from __future__ import absolute_import, print_function

import logging
import getpass
import os
import socket

from ..gitlite import Repo
from ..utils import chdir, hash_file


class BaseStore(object):
  GIT_ENABLED = True

  @classmethod
  def initialize_directory_structure(cls, keybank_mount_path):
    with chdir(keybank_mount_path):
      os.mkdir(cls.DIRECTORY_NAME)
      path = os.path.join(keybank_mount_path, cls.DIRECTORY_NAME)
      with chdir(path):
        cls.create_initial_files()

        if cls.GIT_ENABLED:
          Repo.init(path)
          store = cls(path)
          store._gitcommit("initial commit")
        else:
          store = cls(path)

    return store

  @classmethod
  def create_initial_files(cls):
    raise NotImplementedError

  def __init__(self, path):
    self.logger = logging.getLogger(self.__class__.__name__)
    self.path = path
    if self.__class__.GIT_ENABLED:
      self.repo = Repo(self.path)
    else:
      self.repo = None

  def get_author(self):
    username = getpass.getuser()
    hostname = socket.gethostname()
    return "{} <{}@{}>".format(username, username, hostname)

  def verify(self):
    raise NotImplementedError

  def commit(self, dry_run=False):
    raise NotImplementedError

  def backup(self, config, dry_run=False):
    self.logger.debug("no backup action is defined for this store.")

  def restore(self, config, dry_run=False):
    self.logger.debug("no restore action is defined for this store.")

  def _gitcommit(self, msg="update"):
    self.repo.commit_all(msg, self.get_author())

  def detect_file_changes(self):
    if self.repo is None:
      raise NotImplementedError("cannot detect file changes without git backend")

    changes = {
      "added": set(),
      "changed": set(),
      "deleted": set(),
    }

    files = [(s[:2], s[2:]) for s in self.repo.git.status(porcelain=True).split("\n")]
    # See git status porcelain format for details
    for status, path in files:
      if not path.startswith("/"):
        path = "/" + path

      if status == "??":
        changes["added"].add(path)
      elif status == " M":
        changes["modified"].add(path)
      elif status == " D":
        changes["deleted"].add(path)
      else:
        raise RuntimeError("please do not use git directly. this will cause issues, use keybank commit instead. (run git status on your stores to diagnose)")

    return changes

  def has_uncommited_changes(self):
    changes = self.detect_file_changes()
    return sum(map(len, changes.values())) > 0

  def compute_file_hashes(self, excludes={".git", }):
    hashes = {}
    for root, dirs, files in os.walk(self.path):
      # Inefficient but sufficient for now
      for d in dirs[:]:
        if d in excludes:
          dirs.remove(d)

      for fn in files:
        path = os.path.join(root, fn)
        relative_absolute_path = self.get_relative_absolute_path(path, self.path)

        if relative_absolute_path in excludes:
          continue
        else:
          hashes[relative_absolute_path] = hash_file(path)

    return hashes

  def get_relative_absolute_path(self, path, root):
    """Gets an absolute path that's based on the root directory in the argument.
    """
    path = path[len(root):]
    path = path.lstrip("/")
    path = "/" + path
    return path


class VerificationStatus(object):
  GOOD = "good"
  BAD = "bad"

  def __init__(self, store):
    self.store = store

    self.uncommited_changes = False

    self.git_repo_status = None
    self.git_repo_error_messages = None

    self.files_overall_status = None
    self.files_errors = {}  # path => error info

    self.other_status = None
    self.other_errors = {}  # whatever format

  def has_uncommited_changes(self):
    return self.uncommited_changes

  def is_good(self):
    return (not self.uncommited_changes) and self.git_repo_status and self.files_overall_status and self.other_status
