from __future__ import absolute_import, print_function

import os
import logging
import json
import glob
import shutil
from pwd import getpwnam
from grp import getgrnam

from .base import BaseStore
from ..utils import mkdir_p


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
    self.logger.info("backing up {}".format(self.machine_name))

    # Sanity check if all the paths are correct before backing up
    errored = False

    # Also build all the paths
    all_paths = []
    for entry in self.manifest["files"]:
      paths = self._expand_path(entry["path"], self.manifest["from_directory"])
      if len(paths) != entry["amount"]:
        self.logger.error("expected {} files for {} but got {} files: {}".format(entry["amount"], entry["path"], len(paths), paths))
        errored = True

      all_paths.extend(paths)

    if errored:
      raise RuntimeError("cannot backup {} as sanity check failed. see error logs for details".format(self.machine_name))

    for from_path in all_paths:
      relative_absolute_path = self._get_relative_absolute_path(from_path, self.manifest["from_directory"])
      to_path = relative_absolute_path.lstrip("/")
      to_path = os.path.join(self.path, to_path)

      self.logger.info("copying from {} to {}".format(from_path, to_path))
      mkdir_p(os.path.dirname(to_path))
      shutil.copy2(from_path, to_path)
      # Don't need to set permission as we should be running under umask and root.

  def restore(self, config):
    self.logger.info("restoring {}".format(self.machine_name))

    owner, group = self.manifest["owner"], self.manifest["group"]
    owner_id = getpwnam(owner).pw_uid
    group_id = getgrnam(group).gr_gid

    for root, dirs, files in os.walk(self.path):
      for d in dirs[:]:
        relative_absolute_path = self._get_relative_absolute_path(os.path.join(root, d), self.path)
        if relative_absolute_path == "/.git":
          dirs.remove(d)

      for fn in files:
        # TODO: refactor this kind of madness into something in the base class or pathlib
        from_path = os.path.join(root, fn)
        relative_absolute_path = self._get_relative_absolute_path(from_path, self.path)
        if relative_absolute_path in {"/manifest.json", "/manifest.lock.json"}:
          continue
        to_path = relative_absolute_path.lstrip("/")
        to_path = os.path.join(self.manifest["from_directory"])

        self.logger.info("restoring from {} to {}".format(from_path, to_path))
        mkdir_p(os.path.dirname(from_path))
        shutil.copy2(from_path, to_path)
        os.chown(to_path, owner_id, group_id)
        st = os.stat(to_path)
        os.chmod(to_path, st.st_mode & 0o700) # Should drop all non-owner permissions


class SynchronizedStore(BaseStore):
  GIT_ENABLED = False
  DIRECTORY_NAME = "synchronized"

  @classmethod
  def create_initial_files(cls):
    MachineSynchronizedStore.initialize_directory_structure(os.getcwd(), "_common")

  def _detect_substores(self):
    self.substores = {}
    names = os.listdir(self.path)
    for name in names:
      path = os.path.join(self.path, name)
      if os.path.isdir(path):
        self.substores[name] = MachineSynchronizedStore(path)

  def commit(self, config):
    self._detect_substores()
    for name, substore in self.substores.items():
      substore.commit(config)

  def backup(self, config):
    self._detect_substores()
    machine = config.get("machine")
    if machine:
      substore = self.substores.get(machine)
      if not substore:
        raise ValueError("{} is not a valid substore".format(machine))

      self.substores[machine].backup(config)

    self.substores["_common"].backup(config)

  def restore(self, config):
    self._detect_substores()
    machine = config.get("machine")
    if machine:
      substore = self.substores.get(machine)
      if not substore:
        raise ValueError("{} is not a valid substore".format(machine))

      self.substores[machine].restore(config)

    self.substores["_common"].restore(config)

  def verify(self):
    self._detect_substores()
    for substore in self.substores.values():
      status = substore.verify()
