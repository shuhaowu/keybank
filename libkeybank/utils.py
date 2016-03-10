from __future__ import print_function

from contextlib import contextmanager
import errno
import hashlib
import logging
import os
import subprocess
import sys


class SystemExecuteError(RuntimeError):
  pass


def fatal(message):
  print("error: {}".format(message), file=sys.stderr)
  sys.exit(1)


def execute(command, logger=None):
  logger = logger or logging.getLogger()
  logger.info("EXECUTING: {}".format(command))
  status = os.system(command)
  if status != 0:
    raise SystemExecuteError("exeucting `{}` failed with status {}".format(command, status))


def quiet_call(command):
  return subprocess.call(command, shell=True, stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, "wb"))


@contextmanager
def chdir(path):
  old_cwd = os.getcwd()
  try:
    os.chdir(path)
    yield
  finally:
    os.chdir(old_cwd)


def mkdir_p(path):
  try:
    os.makedirs(path)
  except OSError as e:
    if e.errno == errno.EEXIST and os.path.isdir(path):
      pass
    else:
      raise


def hash_file(path, chunk_size=2**20):
  h = hashlib.sha256()
  with open(path) as f:
    while True:
      buf = f.read(chunk_size)
      if not buf:
        break
      h.update(buf.encode("utf-8"))

  return h.hexdigest()
