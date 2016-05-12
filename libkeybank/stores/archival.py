from __future__ import absolute_import, print_function

import json

from .base import BaseStore


class ArchivalStore(BaseStore):
  DIRECTORY_NAME = "archival"

  EXCLUDED_FILES = {".git", "/manifest.lock.json"}

  @classmethod
  def create_initial_files(cls):
    with open("manifest.lock.json", "w") as f:
      f.write("{}")

  def verify(self):
    return self.verify_against_locked_manifest(self.EXCLUDED_FILES)

  def commit(self, dry_run=False):
    return self.lock_and_gitcommit(self.EXCLUDED_FILES, dry_run=dry_run)

