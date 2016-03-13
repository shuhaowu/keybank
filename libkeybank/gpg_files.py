from __future__ import absolute_import

from contextlib import contextmanager
import logging
import os


class GPGFiles(object):
  @staticmethod
  def initialize_directory_structure(keybank_partition_path):
    os.mkdir(os.path.join(keybank_partition_path, "gpg"))

  def __init__(self, path):
    self.logger = logging.getLogger("gpg")
    self.path = path
    self.export_path = os.path.join(self.path, "_export")

  def scan(self):
    pass

  def verify(self):
    pass

  def _export_subkeys(self, name):
    pass

  def _restore_subkeys(self, name, path):
    pass

  @contextmanager
  def _attention_banner(self):
    self.logger.warning("")
    self.logger.warning("=========")
    self.logger.warning("ATTENTION")
    self.logger.warning("=========")
    self.logger.warning("")
    yield
    self.logger.warning("")
    self.logger.warning("=========")
    self.logger.warning("ATTENTION")
    self.logger.warning("=========")
    self.logger.warning("")

  def backup(self, from_directory, dry_run):
    with self._attention_banner():
      self.logger.warning("gpg backend does not support backups... skipping")

  def restore(self, to_directory, dry_run):
    with self._attention_banner():
      self.logger.warning("gpg backend does not support restore to your machine.")
      self.logger.warning("it will restore inside the keybank, under the gpg/_export directory.")
      self.logger.warning("you will need to copy it manually for now.")
