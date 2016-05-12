from __future__ import absolute_import, print_function

import glob
import json
import os
# from pwd import getpwuid, getpwnam
# from grp import getgrgid, getgrnam
import shutil

from .base import BaseStore, VerificationStatus
from ..utils import chdir, hash_file, mkdir_p


class SynchronizedStore(BaseStore):
  @classmethod
  def create_initial_files(cls):
    with open("_common.manifest.json", "w") as f:
      f.write("{}")

    with open("manifest.lock.json", "w") as f:
      f.write("{}")

  def __init__(self, path):
    super(self.__class__, self).__init__(path)
    self.manifests = {}

    for fn in self.manifest_files():
      name = fn[:-14]
      with open(fn) as f:
        self.manifests[name] = json.load(f)

  def manifest_files(self):
    filenames = os.listdir(path)
    for fn in filenames:
      if fn.endswith(".manifest.json"):
        yield fn

  def excluded_files(self):
    excluded_files = list(self.manifest_files())
    excluded_files.append(".git")
    return excluded_files

  def verify(self):
    return self.verify_against_locked_manifest(self.excluded_files())

  def commit(self, dry_run=False):
    return self.lock_and_gitcommit(self.excluded_files(), dry_run=dry_run)

  def backup(self, config, dry_run=False):
    self.logger.info("backing up common synchronized storage")

    files_backed_up = set()
    files_backed_up |= self._backup_one_machine("_common", config, dry_run=dry_run)

    if config.get("machine"):
      self.logger.info("backing up %s synchronized storage", config["machine"])
      files_backed_up |= self._backup_one_machine(config["machine"], config, dry_run=dry_run)

    locked_manifests = self.get_locked_manifest()
    for machine, locked_manifest in locked_manifests.items():
      for path in locked_manifests:
        if path not in files_backed_up:
          self.logger.info("{} is on file system but not tracked by manifest, deleting...".format(fn))
          if not dry_run:
            os.remove(os.path.join(self.path, path.lstrip("/")))

    # TODO: what should we return here?

  def restore(self, config, dry_run=False):
    self.logger.debug("no restore action is defined for this store.")

  def get_locked_manifest(self):
    with open("manifest.lock.json") as f:
      return json.load(f)

  def _backup_one_machine(self, machine, config, dry_run=False):
    files_backed_up = set()
    for entry in self.manifests[machine]:
      paths = self.expand_path(entry["path"], base=config["from_directory"])
      if len(paths) != entry["amount"]:
        raise RuntimeError("expected {} files for {} but got {}: {}".format(entry["amount"], entry["path"], len(paths), paths))

      for from_path in paths:
        relative_absolute_path = self.get_relative_absolute_path(from_path, config["from_directory"])
        files_backed_up.add(relative_absolute_path)
        to_path = relative_absolute_path.lstrip("/")
        to_path = os.path.join(self.path, to_path)
        self.logger.info("copying {} to {}".format(from_path, to_path))

        if not dry_run:
          dirname = os.path.dirname(to_path)
          mkdir_p(dirname)
          shutil.copy2(from_path, to_path)
          os.chown(to_path, 0, 0)
          os.chmod(to_path, int("0600", 8))

    return files_backed_up

  def expand_path(self, path, base="/"):
    path = path.lstrip("/")
    path = os.path.join(base, path)
    return glob.glob(os.path.expanduser(path))
