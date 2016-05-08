from __future__ import absolute_import, print_function

import json

from .base import BaseStore, VerificationStatus
from ..utils import chdir


class ArchivalStore(BaseStore):
  DIRECTORY_NAME = "archival"

  EXCLUDED_FILES = {".git", "manifest.lock.json"}

  @classmethod
  def create_initial_files(cls):
    with open("manifest.lock.json", "w") as f:
      f.write("{}")

  def verify(self):
    status = VerificationStatus(self)

    status.uncommited_changes = self.has_uncommited_changes()
    if status.uncommited_changes:
      return status

    status.git_repo_status, status.git_repo_error_messages = self.repo.fsck()

    with chdir(self.path):
      with open("manifest.lock.json") as f:
        previous_manifest = json.load(f)

    current_manifest = self.compute_file_hashes(excludes=self.EXCLUDED_FILES)
    status.files_overall_status = current_manifest == previous_manifest
    if not status.files_overall_status:
      previous_set, current_set = set(previous_manifest.keys()), set(current_manifest.keys())
      common_set = current_set.intersection(previous_set)

      added = current_set - common_set
      removed = previous_set - common_set
      changed = [p for p in common_set if previous_manifest[p] != current_manifest[p]]

      for path in added:
        status.files_errors[path] = "added"

      for path in removed:
        status.files_errors[path] = "removed"

      for path in changed:
        status.files_errors[path] = "changed"

    status.other_status = True
    return status

  def commit(self, dry_run=False):
    files_changed = self.detect_file_changes()
    if dry_run:
      return files_changed

    current_manifest = self.compute_file_hashes(excludes=self.EXCLUDED_FILES)
    with chdir(self.path):
      with open("manifest.lock.json", "w") as f:
        json.dump(current_manifest, f)

    self._gitcommit()

    return files_changed
