from __future__ import absolute_import, print_function

import logging
import os
import os.path

from .utils import execute, chdir, mkdir_p
from .generic_files import GenericFiles
from .gpg_files import GPGFiles


def create_sparse_file(path, size):
  with open(path, "w") as f:
    f.seek(size-1)
    f.write('\0')


class KeybankFS(object):
  @staticmethod
  def attached(name):
    return os.path.exists("/dev/mapper/{}".format(name)) or os.path.exists("/mnt/keybank-{}".format(name))

  @classmethod
  def create(cls, path, size):
    kfs = cls(os.path.basename(path), path)
    kfs._create(size)
    return kfs

  @classmethod
  def attach(cls, path):
    kfs = cls(os.path.basename(path), path)
    kfs._attach()
    return kfs

  @classmethod
  def detach(cls, name):
    kfs = cls(name)
    return kfs._detach()

  def __init__(self, name, path=None):
    self.logger = logging.getLogger()
    self.name = name
    self.path = path

    self.mapper_path = os.path.join("/dev", "mapper", self.name)
    self.mnt_path = os.path.join("/mnt", "keybank-{}".format(self.name))

    self.files = {}

  def sanity_check(self):
    if not os.path.isfile(self.manifest_path):
      raise RuntimeError("cannot find manifest.json in the generic folder")

  def scan(self):
    self.logger.info("scanning keybank")
    self.files["generic"] = GenericFiles(os.path.join(self.mnt_path, "generic"))
    self.files["gpg"] = GPGFiles(os.path.join(self.mnt_path, "gpg"))

  def _setup_luks_and_fs(self):
    self.logger.info("setting up LUKS on keybank file")
    execute("cryptsetup -y luksFormat {}".format(self.path))
    execute("cryptsetup luksOpen {} {}".format(self.path, self.name))
    execute("mkfs.ext4 {}".format(self.mapper_path))
    mkdir_p(self.mnt_path)
    execute("mount {} {}".format(self.mapper_path, self.mnt_path))

    # TODO: shouldn't umask from main work here? Apparently it doesn't on my
    # system? Needs investigation... Shouldn't have to do this.
    execute("chmod 0700 {}".format(self.mnt_path))

  def _initialize_directory_structure(self):
    self.logger.info("initializing keybank directory structure")
    with chdir(self.mnt_path):
      os.mkdir("generic")
      os.mkdir("gpg")
      os.chdir(os.path.join(self.mnt_path, "generic"))
      execute("git init")
      with open("manifest.json", "w") as f:
        f.write("[]")

      execute("git add .")
      execute("git commit -am 'Initializing keybank generic'")

  def _create(self, size):
    create_sparse_file(self.path, size)
    self._setup_luks_and_fs()
    self._initialize_directory_structure()

  def _attach(self):
    execute("cryptsetup luksOpen {} {}".format(self.path, self.name))
    mkdir_p(self.mnt_path)
    execute("mount {} {}".format(self.mapper_path, self.mnt_path))

  def _detach(self):
    execute("umount {}".format(self.mnt_path))
    os.rmdir(self.mnt_path)
    execute("cryptsetup luksClose {}".format(self.name))
