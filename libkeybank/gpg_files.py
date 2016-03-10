from __future__ import absolute_import

import os


class GPGFiles(object):
  @staticmethod
  def initialize_directory_structure(self, keybank_partition_path):
    os.mkdir("gpg")

  def __init__(self, path):
    self.path = path

  def scan(self):
    pass

  def verify(self):
    pass

  def backup(self, from_directory, dry_run):
    pass

  def restore(self, to_directory, dry_run):
    pass
