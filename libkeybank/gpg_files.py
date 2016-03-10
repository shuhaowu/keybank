
import os


class GPGFiles(object):
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
