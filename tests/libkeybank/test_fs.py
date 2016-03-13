from __future__ import absolute_import, print_function

import os

from ..helpers import KeybankTestCase, command_executor, KeybankInfo

from libkeybank.fs import KeybankFS


class TestKeybankFS(KeybankTestCase):
  def test_create_detach_attach_scan(self):
    kbi = KeybankInfo.get()
    kbi.create()

    self.assertTrue(os.path.isfile(kbi.filepath))
    self.assertTrue(os.path.exists(kbi.mapper_path))

    kbstat = os.stat(kbi.filepath)
    self.assertEqual(kbi.size, kbstat.st_size)

    self.assertTrue(os.path.isdir(kbi.mnt_path))
    self.assertTrue(os.path.isdir(os.path.join(kbi.mnt_path, "generic")), msg="generic not found, found: {}".format(os.listdir(kbi.mnt_path)))
    self.assertTrue(os.path.isdir(os.path.join(kbi.mnt_path, "gpg")), msg="gpg not found, found: {}".format(os.listdir(kbi.mnt_path)))

    manifest_path = os.path.join(kbi.mnt_path, "generic", "manifest.json")
    self.assertTrue(os.path.isfile(manifest_path), msg="manifest.json not found, found: {}".format(os.listdir(os.path.dirname(manifest_path))))

    with open(manifest_path) as f:
      data = f.read().strip()

    self.assertEqual("[]", data)

    self.assertTrue(os.path.isdir(os.path.join(kbi.mnt_path, "generic", ".git")))

    KeybankFS.detach(kbi.name)

    self.assertFalse(os.path.exists(kbi.mnt_path))
    self.assertFalse(os.path.exists(kbi.mapper_path))
    self.assertTrue(os.path.exists(kbi.filepath))

    kb = KeybankFS.attach(kbi.filepath)

    self.assertTrue(os.path.exists(kbi.mnt_path))
    self.assertTrue(os.path.exists(kbi.mapper_path))
    self.assertTrue(os.path.exists(kbi.filepath))
    self.assertTrue(os.path.isdir(os.path.join(kbi.mnt_path, "generic")), msg="generic not found, found: {}".format(os.listdir(kbi.mnt_path)))
    self.assertTrue(os.path.isdir(os.path.join(kbi.mnt_path, "gpg")), msg="gpg not found, found: {}".format(os.listdir(kbi.mnt_path)))

    kb.scan()

    self.assertEqual(2, len(kb.files))
    for files in kb.files.values():
      files.verify  # should exist..
