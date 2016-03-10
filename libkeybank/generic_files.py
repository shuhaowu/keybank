from __future__ import absolute_import

from collections import namedtuple
import glob
import logging
import json
import os.path
import shutil
from pwd import getpwuid
from grp import getgruid

from .utils import hash_file, mkdir_p


FailedHashExpectation = namedtuple("FailedHashExpectation", ["expected", "actual"])


class GenericFiles(object):
  def __init__(self, path):
    self.logger = logging.getLogger()
    self.path = path
    self.manifest_path = os.path.join(self.path, "manifest.json")
    self.manifest_lock_path = os.path.join(self.path, "manifest.json.lock")

    self.manifest = []
    self.locked_manifest = {}

    self.scan()

  def scan(self):
    with open(self.manifest_path) as f:
      self.manifest = json.load(f)

    if not isinstance(self.manifest, list):
      raise TypeError("manifest.json must contain a list, not a {}".format(type(self.manifest)))

    if os.path.exists(self.manifest_lock_path):
      with open(self.manifest_lock_path) as f:
        self.locked_manifest = json.load(f)

    if not isinstance(self.locked_manifest, dict):
      raise TypeError("manifest.json.lock must contain a dict, not a {}".format(type(self.manifest)))

  def hash_all_files(self, base, excludes={".git", "/manifest.json", "/manifest.json.lock"}):
    hashes = {}
    for root, dirs, files in os.walk(base):
      # Inefficient but sufficient for now
      for d in dirs[:]:
        if d in excludes:
          dirs.remove(d)

      for fn in files:
        path = os.path.join(root, fn)
        relative_absolute_path = self.get_relative_absolute_path(path, base)

        if relative_absolute_path in excludes:
          continue
        else:
          hashes[relative_absolute_path] = hash_file(path)

    return hashes

  def verify(self):
    if not self.locked_manifest:
      self.logger.warn("empty or no manifest.json.lock file found, skipping generic files verification")
      self.logger.warn("this could be because the backup was not initialize or nothing is in the backup")
      return True

    all_file_hashes = self.hash_all_files(self.path)
    expected_hashes = {fn: data["hash"] for fn, data in self.locked_manifest.items()}

    different_hashes = {}
    for fn, actual_hash in all_file_hashes.items():
      expected_hash = expected_hashes.pop(fn, None)
      if actual_hash != expected_hash:
        if expected_hash is None:
          self.logger.warn("detected file not by tracked manifest: {}".format(fn))
        else:  # impossible right now for actual_hash to be None
          different_hashes[fn] = FailedHashExpectation(expected=expected_hash, actual=actual_hash)
          self.logger.error("difference detected for {}: {} (expected) != {} (actual)".format(fn, expected_hash, actual_hash))

    # Anything left over are files that we are supposed to have checked but
    # is no longer on the disk
    for fn, expected_hash in expected_hashes:
      different_hashes[fn] = FailedHashExpectation(expected=expected_hash, actual=None)
      self.logger.error("file tracked by manifest but no longer on disk: {}".format(fn))

    return different_hashes

  def backup(self, from_directory, dry_run):
    locked_manifest = {}

    for entry in self.manifest:
      paths = self.expand_path(entry["path"], base=from_directory)
      if len(paths) != entry["amount"]:
        raise RuntimeError("expected {} files for {} but got {}: {}".format(entry["amount"], entry["path"], len(paths), paths))

      for from_path in paths:
        relative_absolute_path = self.get_relative_absolute_path(from_path, from_directory)
        stat = os.stat(from_path)
        locked_manifest[relative_absolute_path] = {
          "hash": self.hash_file(from_path),
          "owner": getpwuid(stat.st_uid).pw_name,
          "group": getgruid(stat.st_gid).gr_name,
        }
        to_path = relative_absolute_path.lstrip("/")
        to_path = os.path.join(self.path, to_path)
        self.logger.info("copy {} to {} with hash {}".format(from_path, to_path, locked_manifest[relative_absolute_path]["hash"]))

        if not dry_run:
          dirname = os.path.dirname(to_path)
          mkdir_p(dirname)
          shutil.copy2(from_path, to_path)
          os.chown(to_path, 0, 0)
          os.chmod(to_path, int("0600", 8))

    locked_manifest_str = json.dumps(locked_manifest, sort_keys=True, indent=4, separators=(",", ": "))
    self.logger.info("dump locked manifest as follows:")
    for line in locked_manifest_str.split("\n"):
      self.logger.info(line)

    if not dry_run:
      with open(self.manifest_lock_path, "w") as f:
        f.write(locked_manifest_str)

    actual_file_hashes = self.hash_all_files(self.path)
    for fn in actual_file_hashes:
      if fn not in locked_manifest:
        self.logger.info("{} is on file system but not tracked by manifest, deleting...".format(fn))
        if not dry_run:
          os.remove(self.path.join(fn.lstrip("/")))

  def restore(self, to_directory, dry_run):
    pass

  def get_relative_absolute_path(self, path, root):
    path = path[len(root):]
    path = path.lstrip("/")
    path = "/" + path
    return path

  def expand_path(self, path, base="/"):
    path = path.lstrip("/")
    path = os.path.join(base, path)
    return glob.glob(os.path.expanduser(path))
