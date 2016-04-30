from __future__ import absolute_import, print_function

import logging
import os

from ..utils import execute, chdir, hash_file


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
          execute("git init")
          execute("git add .")
          execute("git commit -am 'Initializing keybank generic'")

  @classmethod
  def create_initial_files(cls):
    raise NotImplementedError

  def __init__(self, path):
    self.logger = logging.getLogger(self.__class__.__name__)
    self.path = path

  def verify(self):
    raise NotImplementedError

  def commit(self, dry_run=False):
    raise NotImplementedError

  def backup(self, config, dry_run=False):
    self.logger.debug("no backup action is defined for this store.")

  def restore(self, config, dry_run=False):
    self.logger.debug("no restore action is defined for this store.")

  def compute_file_hashes(self, excludes={".git", "/manifest.json", "/manifest.json.lock"}):
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
