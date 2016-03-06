Keybank
=======

A set of tools and scripts that lives on an USB drive to manage keys
stored on this device.

The motivation of this tool is to have a standardized way to *backup* 
encryption keys, GPG keys, SSL keys, password files, and any other files
that are sensitive. Keybank provides a system to keep track of what files is
what, how the files changed, and verification systems to verify if the files
are corrupt.

Three main tools are available:

1. Creating a new keybank.
2. Syncing a keybank to an encrypted USB disk.
3. Verifying a keybank on the USB disk.

A keybank can be one of two things: on the local machine it is simply a file
mounted as a loopback device which is LUKS encrypted. On a USB drive it could
be a file that can be mounted as loopback or unpacked.

Host Dependency
---------------

- Linux distribution with LUKS and dm-crypt
- git
- bash (or equivalent)
- python2

Usage
-----


