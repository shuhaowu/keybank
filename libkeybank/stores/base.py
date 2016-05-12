from __future__ import absolute_import, print_function

import logging
import getpass
import json
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

  def verify_against_locked_manifest(self, excludes):
    status = VerificationStatus(self)

    status.git_repo_status, status.git_repo_error_messages = self.repo.fsck()
    if not status.git_repo_status:
      self.logger.error("detected issue with git repo: %s", status.git_repo_error_messages)

    with chdir(self.path):
      with open("manifest.lock.json") as f:
        previous_manifest = json.load(f)

    current_manifest = self.compute_file_hashes(excludes=excludes)
    status.files_overall_status = current_manifest == previous_manifest
    if not status.files_overall_status:
      previous_set, current_set = set(previous_manifest.keys()), set(current_manifest.keys())
      common_set = current_set.intersection(previous_set)

      added = current_set - common_set
      removed = previous_set - common_set
      changed = [p for p in common_set if previous_manifest[p] != current_manifest[p]]

      for path in added:
        self.logger.error("extra file detected: %s", path)
        status.files_errors[path] = "added"

      for path in removed:
        self.logger.error("file removed: %s", path)
        status.files_errors[path] = "removed"

      for path in changed:
        self.logger.error("file changed: %s", path)
        status.files_errors[path] = "changed"

    status.other_status = True
    return status

  def lock_and_gitcommit(self, excludes, dry_run=False):
    files_changed = self.detect_file_changes()
    for key, files in files_changed.items():
      for f in files:
        self.logger.info("%s %s", key, f)

    if dry_run:
      self.logger.info("nothing is being committed as this is just a dry run")
      return files_changed

    self.logger.info("committing files...")
    current_manifest = self.compute_file_hashes(excludes=excludes)
    with chdir(self.path):
      with open("manifest.lock.json", "w") as f:
        json.dump(current_manifest, f, sort_keys=True, indent=4, separators=(",", ": "))

    self._gitcommit()
    self.logger.info("committed.")

    return files_changed

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

    files = [(s[:2], s[2:]) for s in self.repo.status().split("\n")]
    # See git status porcelain format for details
    for status, path in files:
      path = path.strip()
      if not path.startswith("/"):
        path = "/" + path

      if status == "??":
        changes["added"].add(path)
      elif status == " M":
        changes["changed"].add(path)
      elif status == " D":
        changes["deleted"].add(path)
      else:
        raise RuntimeError("please do not use git directly. this will cause issues, use keybank commit instead: {}".format(files))

    return changes

  def has_uncommited_changes(self):
    changes = self.detect_file_changes()
    return sum(map(len, changes.values())) > 0

  def compute_file_hashes(self, basepath=None, excludes={".git", }):
    if basepath is None:
      basepath = self.path

    hashes = {}
    for root, dirs, files in os.walk(basepath):
      # Inefficient but sufficient for now
      for d in dirs[:]:
        if d in excludes:
          dirs.remove(d)

      for fn in files:
        filepath = os.path.join(root, fn)
        relative_absolute_path = self.get_relative_absolute_path(filepath, basepath)

        if relative_absolute_path in excludes:
          continue
        else:
          hashes[relative_absolute_path] = hash_file(filepath)

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

    self.git_repo_status = None
    self.git_repo_error_messages = None

    self.files_overall_status = None
    self.files_errors = {}  # path => error info

    self.other_status = None
    self.other_errors = {}  # whatever format

  def has_uncommited_changes(self):
    return self.uncommited_changes

  def is_good(self):
    return self.git_repo_status and self.files_overall_status and self.other_status
