from __future__ import absolute_import, print_function

import copy
import json
import os

from .base import BaseStore, VerificationStatus
from ..utils import chdir


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

    filenames = os.listdir(path)

    for fn in filenames:
      if fn.endswith(".manifest.json"):
        name = fn[:-14]
        with open(fn) as f:
          self.manifests[name] = json.load(f)

  def verify(self):
    raise NotImplementedError

  def commit(self, dry_run=False):
    raise NotImplementedError

  def backup(self, config, dry_run=False):
    self.logger.info("backing up common synchronized storage")
    self._backup_one_machine("_common", config, dry_run=dry_run)

    if config.get("machine"):
      self.logger.info("backing up %s synchronized storage", config["machine"])
      self._backup_one_machine(config["machine"], config, dry_run=dry_run)

  def _backup_one_machine(self, machine, config, dry_run=False):
    pass

  def restore(self, config, dry_run=False):
    self.logger.debug("no restore action is defined for this store.")
