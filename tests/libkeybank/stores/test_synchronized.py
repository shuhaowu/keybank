from __future__ import absolute_import, print_function

import getpass
import hashlib
import json
import os.path
import shutil
import tempfile

from libkeybank.stores.synchronized import SynchronizedStore
from libkeybank.utils import mkdir_p

from .helpers import StoreTestCase


class TestSynchronizedStore(StoreTestCase):
  store_cls = SynchronizedStore

  def setUp(self):
    super(TestSynchronizedStore, self).setUp()
    self.host_path = tempfile.mkdtemp(prefix="{}-host".format(self.__class__.__name__))
    self.file_list = [
      "/file1",
      "/.dir1/file1",
      "/.dir1/file2",
      "/dir2/file1"
      "/dir2/dir3/file1",
      "/machine1/file1",
      "/machine2/file1",
    ]
    self.expected_manifest = {}

    for path in self.file_list:
      abs_path = path
      path = path.lstrip("/")
      path = os.path.join(self.host_path, path)
      mkdir_p(os.path.dirname(path))
      with open(path, "w") as f:
        f.write(path)
        h = hashlib.sha256()
        h.update(path.encode("utf-8"))
        self.expected_manifest[abs_path] = h.hexdigest()

    # add an extra file
    self.extra_path = os.path.join(self.host_path, "machine1/do_not_backup")
    with open(self.extra_path, "w") as f:
      f.write("do_not_backup")

    self.common_manifest = {
      "files": [
        {
          "entry": "/file1",
          "amount": 1,
        },
        {
          "entry": "/.dir1/*",
          "amount": 2,
        },
        {
          "entry": "/.dir2/**/*",
          "amount": 2,
        },
      ],
      "from_directory": self.host_path,
      "user": getpass.getuser(),
      "group": getpass.getuser(),  # Maybe a bad assumption but whatever
    }

    self.machine1_manifest = {
      "files": [
        {
          "entry": "/machine1/file1",
          "amount": 1,
        },
      ],
      "from_directory": self.host_path,
      "user": getpass.getuser(),
      "group": getpass.getuser(),
    }

    self.machine2_manifest = {
      "files": [
        {
          "entry": "/machine2/file1",
          "amount": 1,
        },
      ],
      "from_directory": self.host_path,
      "user": getpass.getuser(),
      "group": getpass.getuser(),
    }

    with open(os.path.join(self.base_path, "_common.manifest.json"), "w") as f:
      json.dump(self.common_manifest, f)

    with open(os.path.join(self.base_path, "machine1.manifest.json"), "w") as f:
      json.dump(self.machine1_manifest, f)

    with open(os.path.join(self.base_path, "machine2.manifest.json"), "w") as f:
      json.dump(self.machine2_manifest, f)

  def tearDown(self):
    super(TestSynchronizedStore, self).tearDown()
    shutil.rmtree(self.host_path)

  def test_backup_verify_restore_common(self):
    pass

  def test_backup_verify_restore_machine1(self):
    pass

  def test_backup_verify_restore_machine2(self):
    pass

  def test_commit_commits_all_machines(self):
    pass
