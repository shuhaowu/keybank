from __future__ import absolute_import, print_function

import os
import unittest
import subprocess

import libkeybank.utils

_original_execute = libkeybank.utils.execute


class CommandExecutorWithStdinSupport(object):
  def __init__(self):
    self.clear()

  def register_command(self, command, stdin):
    self.registered_commands[command] = stdin

  def _execute(self, command, logger=None):
    self.logs.append(command)

    if command in self.registered_commands:
      p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
      stdout_data, stderr_data = p.communicate(input=self.registered_commands[command].encode("utf-8"))

      if p.returncode != 0:
        print(command)
        print("STDOUT:", stdout_data)
        print("STDERR:", stderr_data)
        raise RuntimeError("{} failed with {}".format(command, p.returncode))

      return

    _original_execute(command, logger)

  def clear(self):
    self.logs = []
    self.registered_commands = {}


# Not happy with this global variable approach, but you do what you do..
command_executor = CommandExecutorWithStdinSupport()
libkeybank.utils.execute = command_executor._execute

# We need to surpress the lint error because we need to import after the monkey
# patch
from libkeybank.fs import KeybankFS  # NOQA


class KeybankInfo(object):
  BASE_KEYBANK_DIRECTORY = "/keybanks"

  _cleanup = []

  @classmethod
  def add_to_cleanup(cls, kbi):
    cls._cleanup.append(kbi)

  @classmethod
  def cleanup(cls):
    for kbi in cls._cleanup:
      kbi.destroy()

  @classmethod
  def get(cls):
    return cls("kb{}".format(len(cls._cleanup)))

  def __init__(self, name):
    self.name = name
    self.filepath = os.path.join(self.BASE_KEYBANK_DIRECTORY, self.name)
    self.mapper_path = os.path.join("/dev", "mapper", self.name)
    self.mnt_path = os.path.join("/mnt", "keybank-" + self.name)
    self.password = "password"
    self.size = 10 * 1024 * 1024
    self.__class__._cleanup.append(self)

  def create(self):
    luks_format_cmd = "cryptsetup luksFormat {}".format(self.filepath)
    command_executor.register_command(luks_format_cmd, self.password)

    luks_open_command = "cryptsetup luksOpen {} {}".format(self.filepath, self.name)
    command_executor.register_command(luks_open_command, self.password)
    return KeybankFS.create(self.filepath, self.size)

  def destroy(self):
    if os.path.exists(self.mnt_path):
      os.system("umount {}".format(self.mnt_path))
      os.rmdir(self.mnt_path)

    if os.path.exists(self.mapper_path):
      os.system("cryptsetup luksClose {}".format(self.name))

    if os.path.exists(self.filepath):
      os.remove(self.filepath)


class KeybankTestCase(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    if not os.path.exists(KeybankInfo.BASE_KEYBANK_DIRECTORY):
      os.mkdir(KeybankInfo.BASE_KEYBANK_DIRECTORY)

  def setUp(self):
    self.kbs = []

  def tearDown(self):
    KeybankInfo.cleanup()
    command_executor.clear()
