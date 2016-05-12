from __future__ import absolute_import, print_function

import os

from .utils import execute_without_interactive, chdir, execute_with_postprocessing


# From the Extracted Diagnostics section of the git-fsck man page.
FSCK_ERROR_MESSAGES = (
  "error",
  "lack of head",
  "missing sha",
  "unreachable",
  "missing",
  "dangling",
  "mismatch",
  "invalid",
)


class Repo(object):
  @classmethod
  def init(cls, path, logger=None):
    if not os.path.isdir(path):
      os.mkdir(path)

    with chdir(path):
      execute_without_interactive("git init", logger=logger)

    return cls(path, logger=logger)

  def __init__(self, path, logger=None):
    self.path = path
    self.logger = logger
    if not os.path.isdir(os.path.join(self.path, ".git")):
      raise RuntimeError("{} is not a valid git repository".format(self.path))

  def commit_all(self, message, author):
    with chdir(self.path):
      execute_without_interactive("git add .", logger=self.logger)
      execute_without_interactive("git commit -a -m '{}' --author='{}'".format(message, author), logger=self.logger)

  def fsck(self):
    """Checks the git repository for corruptness.

    Returns:
      good, messages
    """
    with chdir(self.path):
      with execute_with_postprocessing("git fsck", logger=self.logger) as p:
        messages = p.stdout.read().decode("utf-8")
        if p.returncode != 0:
          return False, messages

      search_messages = messages.lower()
      for badmsg in FSCK_ERROR_MESSAGES:
        if badmsg in search_messages:
          return False, messages

    return True, ""

  def status(self):
    with chdir(self.path):
      with execute_with_postprocessing("git status --porcelain", logger=self.logger) as p:
        return p.stdout.read().decode("utf-8").rstrip()
