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


def execute_without_interactive(command, logger=None, raises=True, closes=True):
  logger = logger or logging.getLogger()
  logger.debug("EXECUTING: {}".format(command))
  p = subprocess.Popen(command, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  p.stdin.close()
  retcode = p.wait()
  if raises and retcode != 0:
    print(p.stdout.read().decode("utf-8"), file=sys.stderr)
    p.stdout.close()
    raise SystemExecuteError("exeucting `{}` failed with status {}".format(command, retcode))

  if closes:
    p.stdout.close()

  return p


@contextmanager
def execute_with_postprocessing(command, logger=None):
  p = execute_without_interactive(command, logger, raises=False, closes=False)
  try:
    yield p
  finally:
    p.stdout.close()


def execute_with_interactive(command, logger=None, raises=True):
  logger = logger or logging.getLogger()
  logger.debug("EXECUTING: {}".format(command))
  status = os.system(command)
  if raises and status != 0:
    raise SystemExecuteError("exeucting `{}` failed with status {}".format(command, status))
  else:
    return status


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
  with open(path, "rb") as f:
    while True:
      buf = f.read(chunk_size)
      if not buf:
        break
      h.update(buf)

  return h.hexdigest()
