from __future__ import print_function

import argparse
import copy
import errno
import hashlib
import json
import os.path
import shutil
import sys
import pwd
import grp
import glob

EXCLUDED_FILES = {"/README", "/manifest.json", "/manifest.json.lock"}


def validate_file_or_exit(path):
  if not os.path.isfile(path):
    print("ERROR: {0} is not a valid file".format(path), file=sys.stderr)
    sys.exit(1)


def validate_dir_or_exit(path):
  if not os.path.isdir(path):
    print("ERROR: {0} is not a valid directory".format(path), file=sys.stderr)
    sys.exit(1)


def validate_exists_or_exit(path):
  if not os.path.exists(path):
    print("ERROR: {0} does not exist".format(path), file=sys.stderr)
    sys.exit(1)


def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise


def get_keybank_from_commandline(description):
  if os.geteuid() != 0:
    print("must be root to run this.", file=sys.stderr)
    sys.exit(1)

  os.umask(077)

  parser = argparse.ArgumentParser(description=description)

  parser.add_argument(
    "--dry-run",
    action="store_true",
    help="if enabled, messages of what happens will be printed but nothing actually happens"
  )

  parser.add_argument(
    "directory_on_usb",
    help="this is where manifest.json is found and where the keys are stored"
  )

  parser.add_argument(
    "directory_on_machine",
    nargs="?",
    default="/",
    help="the directory where the keys are stored. default: /"
  )

  args = parser.parse_args()
  validate_dir_or_exit(args.directory_on_machine)
  validate_dir_or_exit(args.directory_on_usb)
  validate_file_or_exit(os.path.join(args.directory_on_usb, "manifest.json"))

  return Keybank(args.directory_on_usb), args


class Keybank(object):

  # Wow this code really needs to be refactored..
  # MVP dragging on to long means shit code. >_>

  def __init__(self, base_directory):
    self.base_directory = base_directory
    self.reload()

  def reload(self):
    self.manifest_path = os.path.join(self.base_directory, "manifest.json")
    with open(self.manifest_path) as f:
      self.manifest = json.load(f)

    self.manifest_lock_path = os.path.join(self.base_directory, "manifest.json.lock")
    if os.path.exists(self.manifest_lock_path):
      with open(self.manifest_lock_path) as f:
        self.manifest_lock = json.load(f)
    else:
      self.manifest_lock = {}

    if not isinstance(self.manifest, list):
      raise TypeError("manifest must be a list, not a {}".format(type(self.manifest)))

  def verify_files(self):
    if not self.manifest_lock:
      raise RuntimeError("no manifest.json.lock file found, cannot verify. this could mean you didn't initialize the backup or it is corrupt.")

    different_hashes = {}
    hashes = self.hash_all_files()
    manifest_lock = copy.copy(self.manifest_lock)
    for fn, h in hashes.items():
      expected_hash = manifest_lock.pop(fn, None)
      if h != expected_hash:
        different_hashes[fn] = {"expected": expected_hash, "actual": h}
        print("WARNING: difference detected for {} => expected: {} actual: {}".format(fn, expected_hash, h))

    for fn, h in manifest_lock.items():
      different_hashes[fn] = {"expected": h, "actual": None}
      print("WARNING: difference detected for {} => expected: {} actual: {}".format(fn, h, None))

    return different_hashes

  def backup_files(self, base="/", dry_run=False):
    # First pass just to verify it because we don't want to do a half assed
    # backup

    manifest = {}

    for entry in self.manifest:
      paths = self.expand_path(entry["path"], base=base)
      if len(paths) != entry["amount"]:
        raise RuntimeError("expected {} files for {} but got {}: {}".format(entry["amount"], entry["path"], len(paths), paths))
      manifest[entry["path"]] = paths

    locked_manifest = {}
    for p, paths in manifest.items():
      for path in paths:
        locked_manifest[path] = self.hash_file(path)
        target_path = path.lstrip("/")
        target_path = os.path.join(self.base_directory, target_path)
        print("copy {} to {} and record hash {}".format(path, target_path, locked_manifest[path]))
        if not dry_run:
          dirname = os.path.dirname(target_path)
          mkdir_p(dirname)
          shutil.copy2(path, target_path)
          os.chmod(target_path, 0600)

    if not dry_run:
      with open(self.manifest_lock_path, "w") as f:
        print("dumping locked manifest")
        json.dump(locked_manifest, f, sort_keys=True, indent=4, separators=(",", ": "))

      self.manifest_lock = locked_manifest

      difference = self.verify_files()
      for fn in difference.keys():
        hashes = difference[fn]
        if hashes["expected"] is None:
          print("removing {}".format(fn))

          os.remove(os.path.join(self.base_directory, fn.lstrip("/")))

        del difference[fn]

      if difference:
        raise RuntimeError("difference already detected immediately after backup")

    return locked_manifest

  def restore_files(self, chown, base="/", dry_run=False):
    try:
      uid = pwd.getpwnam(chown).pw_uid
    except KeyError:
      raise LookupError("cannot find user {}".format(chown))

    try:
      gid = grp.getgrnam(chown).gr_gid
    except KeyError:
      raise LookupError("cannot find group {}".format(chown))

    for target_path, h in self.locked_manifest.items():
      path = target_path.lstrip("/")
      src_path = os.path.join(self.base_directory, path)
      target_path = os.path.join(base, target_path)

      print("copy {} to {}".format(src_path, target_path))
      if not dry_run:
        shutil.copy2(src_path, target_path)
        os.chown(target_path, uid, gid)

  def hash_file(self, path, chunk_size=2**20):
    h = hashlib.sha256()
    with open(path) as f:
      while True:
        buf = f.read(chunk_size)
        if not buf:
          break
        h.update(buf)

    return h.hexdigest()

  def hash_all_files(self):
    # really just force a read.
    hashes = {}
    for root, dirs, files in os.walk(self.base_directory):
      if ".git" in dirs:
        dirs.remove(".git")

      for fn in files:
        # path is the real path, rpath is the relative path to the key directory, but starting with a /
        path = os.path.join(root, fn)
        rpath = path[len(self.base_directory):]
        if rpath in EXCLUDED_FILES:
          continue
        hashes[rpath] = self.hash_file(path)

    return hashes

  def expand_path(self, path, base="/"):
    path = path.lstrip("/")
    path = os.path.join(base, path)
    return glob.glob(os.path.expanduser(path))
