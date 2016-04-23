from __future__ import absolute_import

from contextlib import contextmanager
import logging
import os
import subprocess

from .utils import execute, mkdir_p


class GPGFiles(object):
  @staticmethod
  def initialize_directory_structure(keybank_partition_path):
    os.mkdir(os.path.join(keybank_partition_path, "gpg"))

  def __init__(self, path):
    self.logger = logging.getLogger("gpg")
    self.path = path
    self.export_path = os.path.join(self.path, "_export")

    self.gpg_homes = []
    self.scan()

  def scan(self):
    for d in os.listdir(self.path):
      if d.startswith("_"):
        self.logger.debug("ignoring {} because of the prefixing _".format(d))
        continue

      path = os.path.join(self.path, d)
      if not os.path.isdir(path):
        continue

      self.gpg_homes.append(d)

  def verify(self):
    self.logger.info("verifying gpg files")
    corrupted = {}
    for name in self.gpg_homes:
      this_is_corrupted = self._verify_one(name)
      if this_is_corrupted:
        corrupted[name] = this_is_corrupted

    return corrupted

  def _gpg_cmd(self, path, args):
    return "gpg --homedir={} {}".format(path, args)

  def _verify_one(self, name):
    path = os.path.join(self.path, name)

    self.logger.info("verifying {}".format(name))
    statuscode = execute(self._gpg_cmd(path, "-k"), logger=self.logger, raises=False)
    if statuscode:
      self.logger.error("seems like the public keys are corrupt?")
      return "public"

    statuscode = execute(self._gpg_cmd(path, "-K"), logger=self.logger, raises=False)
    if statuscode:
      self.logger.error("seems like the private keys are corrupt?")
      return "private"

    self.logger.info("verifid {}".format(name))

    return None

  def _export_subkeys(self, name, export_base_path, dry_run):
    path = os.path.join(self.path, name)
    export_path = os.path.join(export_base_path, name)

    self.logger.info("exporting gpg keys for {}".format(name))
    # bad way to do this but..
    output = subprocess.check_output(self._gpg_cmd(path, "-k"), shell=True)
    master_keyid = None
    for line in output.decode("utf-8").split("\n"):
      self.logger.debug(line)
      line = line.strip()
      if line.startswith("pub"):
        line = line.split()
        master_keyid = line[1].split("/")[1]
        break

    if master_keyid is None:
      raise RuntimeError("could not find master key id")

    export_cmd = self._gpg_cmd(path, "--output {}/subkeys --export-options export-reset-subkey-passwd --export-secret-subkeys {}".format(export_path, master_keyid))
    import_cmd = self._gpg_cmd(export_path, "--import {}/subkeys".format(export_path))
    if not dry_run:
      mkdir_p(export_path)
      execute(export_cmd)
      execute(import_cmd)
      os.remove(os.path.join(export_path, "subkeys"))
    else:
      self.logger.info("export subkeys via `{}`".format(export_cmd))
      self.logger.info("import subkeys in new dir via `{}`".format(import_cmd))

    return export_path

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

    for name in self.gpg_homes:
      path = self._export_subkeys(name, self.export_path, dry_run)
      self.logger.info("the copy of gnupg home of {} without the master key is available here: {}".format(name, path))
