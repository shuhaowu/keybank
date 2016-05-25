from __future__ import absolute_import, print_function

import os
import json

from .base import BaseStore, VerificationStatus
from ..utils import chdir


class SynchronizedStore(BaseStore):
  @classmethod
  def create_initial_files(cls):
    if not os.path.exists("_common.manifest.json"):
      with open("_common.manifest.json", "w") as f:
        f.write("{}")

    if not os.path.exists("_common.manifest.lock.json"):
      with open("_common.manifest.lock.json", "w") as f:
        f.write("{}")

  def __init__(self, path):
    super(self.__class__, self).__init__(path)

    self.manifests = {}
    for name, fn in self._manifest_files():
      with open(fn) as f:
        self.manifests[name] = json.load(f)

  def _manifest_files(self):
    filenames = os.listdir(self.path)
    for fn in filenames:
      if fn.endswith(".manifest.json"):
        name = fn[:-14]
        yield name, fn

  def write_manifest_lock(self, config):
    manifest_locks = {}
    for name, fn in self._manifest_files():
      # Subfolders have no ignored files in theory.
      manifest_lock = self._compute_file_hashes_for_path(path=os.path.join(self.path, name), excludes=[])
      with chdir(self.path):
        with open("{}.manifest.lock.json", "w") as f:
          json.dump(manifest_lock, f, sort_keys=True, indent=4, separators=(",", ": "))

      manifest_locks[name] = manifest_lock

    return manifest_locks

  def exclude_files(self):
    names = map(lambda v: v[0], self.manifest_files())
    excluded_files = []
    for name in names:
      excluded_files.append("{}.manifest.json")
      excluded_files.append("{}.manifest.lock.json")

    excluded_files.append(".git")
    return excluded_files

  def backup(self, config):
    pass

  def restore(self, config):
    pass

  def verify(self):
    status = VerificationStatus(self)

    self._verify_git_repo(status)

    for name, fn in self._manifest_files:
      self._verify_against_manifest_lock(status,
                                         manifest_lock_path=os.path.join(self.path, "{}.manifest.lock.json".format(name)),
                                         root_path=os.path.join(self.path, name),
                                         path_prefix="/{}".format(name),
                                         excludes=self.excluded_files())

    return status
