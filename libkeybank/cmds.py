from __future__ import print_function, absolute_import

import argparse
import os
import sys
import logging

from .fs import KeybankFS
from .utils import fatal, quiet_call


def sanity_check_git():
  git_exists_code = quiet_call("git --version")
  if git_exists_code:
    fatal("git not installed. please install git before running this")

  email_code = quiet_call("git config --global --get user.email")
  name_code = quiet_call("git config --global --get user.name")
  if name_code or email_code:
    fatal("git username and email not configured.\n\nConfigure with `git config --global user.email 'you@example.com'` and `git config --global user.name 'Your Name'` before proceeding.")


def sanity_check():
  if os.geteuid() != 0:
    fatal("keybank must be run as root, preferably in xterm")

  os.umask(int("077", 8))

  sanity_check_git()


def validate_file_or_exit(path):
  if not os.path.isfile(path):
    fatal("{0} is not a valid file".format(path))


def validate_dir_or_exit(path):
  if not os.path.isdir(path):
    fatal("{0} is not a valid directory".format(path))


def validate_exists_or_exit(path):
  if not os.path.exists(path):
    fatal("{0} does not exist".format(path))


def validate_keybank_not_attached_or_exit(name):
  if KeybankFS.attached(name):
    fatal("keybank '{}' already attached. use a different name for your keybank or detach via `keybank detach`".format(name))


def validate_keybank_attached_or_exit(name):
  if not KeybankFS.attached(name):
    fatal("keybank '{}' is not attached. use `keybank attach` to attach".format(name))


class Attach(object):
  description = "attach to a keybank file"

  def __init__(self, parser):
    parser.add_argument("path", help="the path to the keybank file")
    self.parser = parser

  def validate_args(self, args):
    validate_file_or_exit(args.path)
    validate_keybank_not_attached_or_exit(os.path.basename(args.path))

  def run(self, args):
    logger = logging.getLogger()
    kb = KeybankFS.attach(args.path)
    logger.info("keybank '{}' attached and mounted at {}".format(kb.name, kb.mnt_path))


class Detach(object):
  description = "detach from a keybank"

  def __init__(self, parser):
    parser.add_argument("name", help="the name of the keybank (just the filename of your keybank file)")

  def validate_args(self, args):
    validate_keybank_attached_or_exit(args.name)

  def run(self, args):
    logger = logging.getLogger()
    KeybankFS.detach(args.name)
    logger.info("keybank detached!")


class Create(object):
  description = "create a new keybank"

  def __init__(self, parser):
    parser.add_argument(
      "-s", "--size", nargs="?",
      default=128*1024*1024,  # 128MB
      type=int,
      help="the size of the keybank in bytes (defaults to 128MB)"
    )

    parser.add_argument(
      "path",
      help="the path to the keybank file to be created. ensure the parent of this path is owned by root"
    )

  def validate_args(self, args):
    if os.path.exists(args.path):
      fatal("{0} already exists".format(args.path))

    validate_keybank_not_attached_or_exit(os.path.basename(args.path))

    parent_dir = os.path.dirname(os.path.abspath(args.path))
    if not os.path.isdir(parent_dir):
      fatal("{0} is not a directory".format(parent_dir))

    parent_stat = os.stat(parent_dir)
    if parent_stat.st_uid != 0 or parent_stat.st_gid != 0:
      fatal("{} must be owned by root".format(parent_dir))

  def run(self, args):
    kb = KeybankFS.create(args.path, args.size)

    logger = logging.getLogger()
    logger.info("")
    logger.info("==========================")
    logger.info("KEYBANK BOOTSTRAP COMPLETE")
    logger.info("==========================")
    logger.info("")
    logger.info("Done creating keybank. It should be mounted at {}".format(kb.mnt_path))
    logger.info("To go into it, you need to be root.")
    logger.info("")
    logger.info("To unmount, do:")
    logger.info("# keybank detach {}".format(kb.name))


class BackupRestore(object):
  def __init__(self, parser):
    parser.add_argument(
      "--dry-run",
      action="store_true",
      help="if enabled, messages of what happens will be printed but nothing actually happens"
    )

    parser.add_argument(
      "--include-gpg",
      action="store_true",
      help="if enabled, this will attempt to backup/restore gpg files"
    )

    parser.add_argument(
      "name",
      help="the name of the keybank (just the filename of your keybank file). this must already be attached."
    )

    parser.add_argument(
      "directory_on_machine",
      nargs="?",
      default="/",
      help="the directory where the keys are stored. default: /"
    )

  def validate_args(self, args):
    validate_dir_or_exit(args.directory_on_machine)
    validate_keybank_attached_or_exit(args.name)

  def run(self, args):
    kb = KeybankFS(args.name)
    kb.scan()
    for ttype, files in kb.files.items():
      if ttype == "gpg" and not args.include_gpg:
        continue

      method = getattr(files, self.method)
      method(args.directory_on_machine, args.dry_run)


class Backup(BackupRestore):
  description = "backs up to an attached keybank"
  method = "backup"

  def run(self, args):
    BackupRestore.run(self, args)
    logger = logging.getLogger()
    if not args.dry_run:
      logger.info("backup complete")
      logger.info("remember to do `git commit` after you examine the changes")


class Restore(BackupRestore):
  description = "restores from an attached keybank"
  method = "restore"

  def run(self, args):
    BackupRestore.run(self, args)
    logger = logging.getLogger()
    if not args.dry_run:
      logger.info("restore complete")


class Verify(object):
  description = "verifies a keybank"

  def __init__(self, parser):
    parser.add_argument("name", help="the name of the keybank (just the filename of your keybank file)")

  def validate_args(self, args):
    validate_keybank_attached_or_exit(args.name)

  def run(self, args):
    logger = logging.getLogger()

    kb = KeybankFS(args.name)
    kb.scan()
    for ttype, files in kb.files.items():
      if files.verify():
        fatal("verification failed, see messages above for details")

    logger.info("verification successful")


commands = [
  Attach,
  Detach,
  Create,
  Backup,
  Restore,
  Verify
]


DESCRIPTION = """
A utility to backup, restore, and verify backups for secret keys such as SSH,
OTR, GPG keys.
""".strip()


def main():
  sanity_check()

  parser = argparse.ArgumentParser(description=DESCRIPTION)
  subparsers = parser.add_subparsers()
  for command_cls in commands:
    name = command_cls.__name__.lower()
    subparser = subparsers.add_parser(name, help=command_cls.description)
    command = command_cls(subparser)
    subparser.set_defaults(cmd=command, which=name)

  args = parser.parse_args()

  if len(vars(args)) == 0:
    # If you call this with no arguments, it will break like this:
    # https://bugs.python.org/issue16308
    parser.print_usage()
    print("{}: error: too few arguments".format(parser.prog), file=sys.stderr)
    sys.exit(1)

  logging.basicConfig(format="[%(asctime)s][%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S", level=logging.DEBUG)

  args.cmd.validate_args(args)
  args.cmd.run(args)
