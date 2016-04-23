from __future__ import absolute_import, print_function

import os

from ..helpers import KeybankTestCase, KeybankInfo


class TestGPGFiles(KeybankTestCase):
  def setUp(self):
    KeybankTestCase.setUp(self)
    self.kbi = KeybankInfo.get()
    self.kb = self.kbi.create()

    self.gpg_base_path = os.path.join(self.kbi.mnt_path, "gpg")
