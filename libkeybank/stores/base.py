from __future__ import absolute_import, print_function

import logging
import getpass
import json
import os
import random
import socket
import string

from ..gitlite import Repo
from ..utils import chdir, hash_file


BASE_IGNORED_FILES = {"/.git", "/manifest.lock.json"}


class BaseStore(object):
  """Contains a feature complete archival store, more or less."""
  GIT_ENABLED = True
  DIRECTORY_NAME = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

  @classmethod
  def initialize_directory_structure(cls, base_path, directory_name=None):
    if directory_name is None:
      directory_name = cls.DIRECTORY_NAME

    with chdir(base_path):
      os.mkdir(directory_name)
      path = os.path.join(base_path, directory_name)
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
    if not os.path.exists("manifest.lock.json"):
      with open("manifest.lock.json", "w") as f:
        f.write("{}")

  def __init__(self, path):
    self.logger = logging.getLogger(self.__class__.__name__)
    self.path = path
    if self.__class__.GIT_ENABLED:
      self.repo = Repo(self.path)
    else:
      self.repo = None

  def _get_author(self):
    username = getpass.getuser()
    hostname = socket.gethostname()
    return "{} <{}@{}>".format(username, username, hostname)

  def _gitcommit(self, msg="update"):
    if self.repo:
      self.repo.commit_all(msg, self._get_author())
    else:
      self.logger.warn("called git commit but store does not define a git repository")

  def _compute_file_hashes_for_path(self, path=None, excludes=BASE_IGNORED_FILES):
    if path is None:
      path = self.path

    hashes = {}
    for root, dirs, files in os.walk(path):
      for d in dirs[:]:
        relative_absolute_path = self._get_relative_absolute_path(os.path.join(root, d), path)
        if relative_absolute_path in excludes:
          dirs.remove(d)

      for fn in files:
        full_path = os.path.join(root, fn)
        relative_absolute_path = self._get_relative_absolute_path(full_path, path)

        if relative_absolute_path in excludes:
          continue
        else:
          hashes[relative_absolute_path] = hash_file(full_path)

    return hashes

  def _get_relative_absolute_path(self, path, root):
    """Gets an absolute path that's based on the root directory in the argument.
    """
    path = path[len(root):]
    path = path.lstrip("/")
    path = "/" + path
    return path

  def _detect_file_changes(self):
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

  def _has_uncommited_changes(self):
    changes = self.detect_file_changes()
    return sum(map(len, changes.values())) > 0

  def _verify_git_repo(self, status):
    status.git_repo_status, status.git_repo_error_messages = self.repo.fsck()

    if not status.git_repo_status:
      self.logger.error("detected issue with git repo: %s", status.git_repo_error_messages)

    return status

  def _verify_against_manifest_lock(self, status, manifest_lock_path=None, root_path=None, path_prefix="/", excludes=BASE_IGNORED_FILES):
    """Verify a sub directory against a manifest lock file.

    status: a VerificationStatus object.
    manifest_lock_path: the path to the manifest.lock.json file.
    root_path: the path where the files specified in the manifest.json file lives.
    path_prefix: the path in the files_error and logger will be prefixed with this

    """

    if root_path is None:
      root_path = self.path

    if manifest_lock_path is None:
      manifest_lock_path = os.path.join(self.path, "manifest.lock.json")

    with open(manifest_lock_path) as f:
      try:
        previous_manifest = json.load(f)
      except ValueError:
        self.logger.error("manifest lock is corrupted")
        status.files_overall_status = False
        status.files_errors[self._get_relative_absolute_path(manifest_lock_path, root_path)] = "not a valid json"
        return status

    current_manifest = self._compute_file_hashes_for_path(path=root_path, excludes=excludes)
    status.files_overall_status = current_manifest == previous_manifest

    if not status.files_overall_status:
      previous_set, current_set = set(previous_manifest.keys()), set(current_manifest.keys())
      common_set = current_set.intersection(previous_set)

      added = current_set - common_set
      removed = previous_set - common_set
      changed = [p for p in common_set if previous_manifest[p] != current_manifest[p]]

      # TODO: refactor this
      for path in added:
        path = path.lstrip("/")
        path = os.path.join(path_prefix, path)
        self.logger.error("extra file detected: %s", path)
        status.files_errors[path] = "added"

      for path in removed:
        path = path.lstrip("/")
        path = os.path.join(path_prefix, path)
        self.logger.error("file removed: %s", path)
        status.files_errors[path] = "removed"

      for path in changed:
        path = path.lstrip("/")
        path = os.path.join(path_prefix, path)
        self.logger.error("file changed: %s", path)
        status.files_errors[path] = "changed"

    return status

  def write_manifest_lock(self, config):
    manifest_lock = self._compute_file_hashes_for_path(path=self.path, excludes=self.excluded_files())
    with chdir(self.path):
      with open("manifest.lock.json", "w") as f:
        json.dump(manifest_lock, f, sort_keys=True, indent=4, separators=(",", ": "))

    return manifest_lock

  def excluded_files(self):
    return BASE_IGNORED_FILES

  def commit(self, config):
    self.logger.info("computing and writing manifest lock")
    self.write_manifest_lock(config)

    if self.GIT_ENABLED:
      self.logger.info("committing into git")
      self._gitcommit()

    self.logger.info("committed.")

  def backup(self, config):
    self.logger.warn("no backup defined for this store")

  def restore(self, config):
    self.logger.warn("no restore defined for this store")

  def verify(self):
    status = VerificationStatus(self)

    self._verify_git_repo(status)
    self._verify_against_manifest_lock(status, manifest_lock_path=os.path.join(self.path, "manifest.lock.json"), root_path=self.path, excludes=self.excluded_files())

    return status


class VerificationStatus(object):
  GOOD = "good"
  BAD = "bad"

  def __init__(self, store):
    self.store = store

    self.git_repo_status = None
    self.git_repo_error_messages = None

    self.files_overall_status = None
    self.files_errors = {}  # path => error info

    self.other_status = True  # Defaults to good.
    self.other_errors = {}  # whatever format

  def has_uncommited_changes(self):
    return self.uncommited_changes

  def is_good(self):
    return self.git_repo_status and self.files_overall_status and self.other_status
