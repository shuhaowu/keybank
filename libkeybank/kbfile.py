from __future__ import absolute_import, print_function

import logging
import os
import os.path

from .utils import execute, chdir, mkdir_p


class KeybankFile(object):
  def __init__(self, name, path=None):
    self.logger = logging.getLogger("keybank-{}".format(name))
    self.name = name
    self.path = path

    self.mapper_path = os.path.join("/dev", "mapper", self.name)
    self.mnt_path = os.path.join("/mnt", "keybank-{}".format(self.name))

    self.stores = {}

  def _create_sparse_file(self, path, size):
    with open(path, "w") as f:
      f.seek(size - 1)
      f.write('\0')

  def _setup_luks_and_fs(self):
    self.logger.info("setting up LUKS on keybank file")
    execute("cryptsetup luksFormat {}".format(self.path))
    execute("cryptsetup luksOpen {} {}".format(self.path, self.name))
    execute("mkfs.ext4 {}".format(self.mapper_path))
    mkdir_p(self.mnt_path)
    execute("mount {} {}".format(self.mapper_path, self.mnt_path))

    # TODO: shouldn't umask from main work here? Apparently it doesn't on my
    # system? Needs investigation... Shouldn't have to do this.
    execute("chmod 0700 {}".format(self.mnt_path))

  def _initialize_stores(self):
    pass

  def create(self, size):
    self._create_sparse_file(self.path, size)
    self._setup_luks_and_fs()
    self._initialize_stores()

  def attach(self):
    execute("cryptsetup luksOpen {} {}".format(self.path, self.name))
    mkdir_p(self.mnt_path)
    execute("mount {} {}".format(self.mapper_path, self.mnt_path))

  def detact(self):
    execute("umount {}".format(self.mnt_path))
    os.rmdir(self.mnt_path)
    execute("cryptsetup luksClose {}".format(self.name))

  def destroy(self):
    pass