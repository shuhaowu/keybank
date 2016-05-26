from __future__ import absolute_import, print_function

import os
import json
import glob
import shutil

from .base import BaseStore, VerificationStatus
from ..utils import chdir, mkdir_p


class MachineSynchronizedStore(BaseStore):
  @classmethod
  def create_initial_files(cls):
    if not os.path.exists("manifest.json"):
      with open("manifest.json", "w") as f:
        f.write("{}")

    if not os.path.exists("manifest.lock.json"):
      with open("manifest.lock.json", "w") as f:
        f.write("{}")

  def __init__(self, path):
    super(self.__class__, self).__init__(path)
    self.machine_name = os.path.dirname(path)
    self.logger = logging.getLogger("{}-{}".format(self.__class__.__name__, self.machine_name))
    with open("manifest.json") as f:
      self.manifest = json.load(f)

  def _expand_path(self, path, base="/"):
    path = path.lstrip("/")
    path = path.join(base, path)
    return glob.glob(os.path.expanduser(path))

  def backup(self, config):
    self.logger.info("backing up {}".format(machine))

    # Sanity check if all the paths are correct before backing up
    errored = False

    # Also build all the paths
    all_paths = []
    for entry in self.manifest["files"]:
      path = self._expand_path(entry["path"], self.manifest["from_directory"])
      if len(paths) != entry["amount"]:
        self.logger.error("expected {} files for {} but got {} files: {}".format(entry["amount"], entry["path"], len(paths), paths))
        errored = True

      all_paths.extend(paths)

    if errored:
      raise RuntimeError("cannot backup {} as sanity check failed. see error logs for details".format(self.machine_name))

    for from_path in all_paths:
      relative_absolute_path = self._get_relative_absolute_path(from_path, self.manifest["from_directory"])

  def restore(self, config):
    pass

class SynchronizedStore(BaseStore):
  GIT_ENABLED = False
  DIRECTORY_NAME = "synchronized"

  @classmethod
  def create_initial_files(cls):
    MachineSynchronizedStore.initialize_directory_structure(os.getcwd(), "_common")

  def __init__(self, path):
    super(self.__class__, self).__init__(path)

    self.substores = {}
    names = os.listdir(self.path)
    for name in names:
      path = os.path.join(self.path, name)
      if os.path.isdir(path):
        self.substores[name] = MachineSynchronizedStore(path)

