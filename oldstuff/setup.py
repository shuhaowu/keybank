#!/usr/bin/env python3

from distutils.core import setup

setup(
  name="keybank",
  version="0.1",
  description="utility for managing backups for keys a SSH drive",
  author="Shuhao Wu",
  url="https://github.com/shuhaowu/keybank",
  packages=["libkeybank"],
  scripts=["keybank"]
)
