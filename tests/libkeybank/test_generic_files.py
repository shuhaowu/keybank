from __future__ import absolute_import, print_function

import json
import hashlib
import os
import shutil

from ..helpers import KeybankTestCase, KeybankInfo

from libkeybank.generic_files import GenericFiles
from libkeybank.utils import mkdir_p


class TestGenericFiles(KeybankTestCase):
  def setUp(self):
    KeybankTestCase.setUp(self)
    self.kbi = KeybankInfo.get()
    self.kb = self.kbi.create()
    self.manifest_path = os.path.join(self.kbi.mnt_path, "generic", "manifest.json")
    self.locked_manifest_path = os.path.join(self.kbi.mnt_path, "generic", "manifest.json.lock")

    mkdir_p("/tmp/keybank-test")

    self.files = {
      "/tmp/keybank-test/secretfile1": "secretfile1content",
      "/tmp/keybank-test/secretfile2": "secretfile2content",
      "/tmp/keybank-test/mehfile1":    "mehfile1content",
    }

    self.expected_manifest = [
      {
        "path": "/tmp/keybank-test/secret*",
        "amount": 2
      },
      {
        "path": "/tmp/keybank-test/mehfile1",
        "amount": 1
      }
    ]

    self.expected_locked_manifest = {}

    for fn, content in self.files.items():
      with open(fn, "w") as f:
        f.write(content)

      # We always run test as root
      self.expected_locked_manifest[fn] = {
        "owner": "root",
        "group": "root",
        "hash": hashlib.sha256(content.encode("utf-8")).hexdigest()
      }

    with open(self.manifest_path, "w") as f:
      json.dump(self.expected_manifest, f)

  def test_backup_dry_run(self):
    files = GenericFiles(os.path.join(self.kbi.mnt_path, "generic"))
    files.backup("/", dry_run=True)
    for fn in self.files:
      self.assertFalse(os.path.exists(os.path.join(self.kbi.mnt_path, "generic", fn.lstrip("/"))))

  def test_real_backup_and_restore(self):
    files = GenericFiles(os.path.join(self.kbi.mnt_path, "generic"))
    files.backup("/", dry_run=False)
    for fn, expected_content in self.files.items():
      path = os.path.join(self.kbi.mnt_path, "generic", fn.lstrip("/"))
      self.assertTrue(os.path.exists(path), msg="{} does not exist".format(path))
      with open(path) as f:
        content = f.read()

      self.assertEqual(expected_content, content)
      os.remove(fn)

    with open(self.locked_manifest_path) as f:
      locked_manifest = json.load(f)

    self.assertEqual(self.expected_locked_manifest, locked_manifest)

    files.scan()
    # Do a dry run files
    files.restore("/", dry_run=True)
    for fn in self.files:
      self.assertFalse(os.path.exists(fn), msg="{} exists but should not".format(fn))

    files.scan()
    files.restore("/", dry_run=False)
    for fn, expected_content in self.files.items():
      self.assertTrue(os.path.exists(fn), msg="{} does not exist but should".format(fn))
      with open(fn) as f:
        content = f.read()

      self.assertEqual(expected_content, content)

  def test_verify(self):
    files = GenericFiles(os.path.join(self.kbi.mnt_path, "generic"))
    # We should return a truthy value to indicate there are differences.
    # Right now the files has not been backed up so there is no locked
    # manifest
    self.assertTrue(files.verify())

    files.backup("/", dry_run=False)
    files.scan()

    self.assertEqual({}, files.verify())

    path_to_modify = "/tmp/keybank-test/secretfile1"
    content = "corrupted".encode("utf-8")
    modified_sha = hashlib.sha256(content).hexdigest()

    with open(os.path.join(files.path, path_to_modify.lstrip("/")), "w") as f:
      f.write("corrupted")

    differences = files.verify()
    self.assertEqual(1, len(differences))
    self.assertEqual(self.expected_locked_manifest[path_to_modify]["hash"], differences[path_to_modify].expected)
    self.assertEqual(modified_sha, differences[path_to_modify].actual)

  def tearDown(self):
    KeybankTestCase.tearDown(self)
    shutil.rmtree("/tmp/keybank-test")
