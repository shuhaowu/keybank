.. _design:

======
Design
======

Keybank File
============

The keybank file is a file that is LUKS encrypted with ext4. You will choose a
passphrase to encrypt it with when it is created. Inside, the directory
structure is as follows:

.. code::

    synchronized/
    gpg/
    archival/
    hooks/

When a keybank file is created, a sha256sum file will exist as well. This file
will be updated everytime the keybank is commited. Both the keybank file and the
sha256sum file should be copied to the USB drive.

All files are owned by root and only readable by root. It is preferred to

Verification
------------

Verification in Keybank is designed to be very defensive. To verify a keybank:

1. We check if the sha256 checksum agrees with the keybank file itself.
2. We check the git repositories for each store to make sure they are not corrupt.
3. We invoke store specific verification methods, which may check for checksums
   for individual files, or something else.

Synchronized Store
==================

Files in this store is to be synchronized with your machine. Since it is
possible to have multiple machines where you want to have a generic set of
files that restores to all machines and specific files that are stored to certain
machines, this ability is provided by this store.

Directory Structure
-------------------

.. code::

    synchronized/ # This lives under the root of the keybank partition
      all/
        home/user/.ssh/id_rsa
        ...
      machine1
        home/user/.config/sensitive_file_for_machine_1
      machine2
        home/user/.config/sensitive_file_for_machine_2
      _common.manifest.json
      machine1.manifest.json
      machine2.manifest.json
      manifest.lock.json

Actions Definition
------------------

Backup is defined per machine. Each time backup is invoked, the generic files
for all machines will be copied from the machine where the backup is called to
the store. The machine specific files will also be copied. Files for other
machines will not be touched.

Restore is also defined per machine. Each time restore is called, the generic
files will be copied to your machine. Files for this machine will also be copied
while files for other machines will not be.

Verify is defined for the store. Each time verify is called, the checksum is
verified against the manifest.lock.json file to detect inconsistencies if any.

Commit is defined per machine. Each time commit is called, the checksums for
each file in all and for that machine will be calculated and updated in
manifest.lock.json. Deleted files will be removed from the manifest.lock.json
file. Files for other machines will not be updated.

Manifest format
---------------

.. code:: json

    [
      {
        "path":    "/home/johnsmith/.ssh/id_rsa*",
        "comment": "ssh keys",
        "amount":  4
      },
      {
        "path":    "/home/johnsmith/.purple/otr.private_key",
        "comment": "otr key",
        "amount":  1
      }
    ]

GPG Store
=========

The GPG store serves as GNUPGHOME directories for GPG to operate in. You should
create your master key here. You should also do your key signing parties from
here.

Directory Structure
-------------------

.. code::

    gpg/ # This lives under the root of the keybank partition
      one/
        secring.gpg
        pubring.gpg
        ...
      two/
        ...
      machine1.manifest.json
      machine2.manifest.json

Each subdirectory within the store is another GNUPGHOME directory for a
different master key.

Actions Definition
------------------

TODO: To be written.

Manifest file
-------------

The manifest files for each machine is defined to let keybank know how to
restore to that machine. For example, you can make it such that you only
restore certain subkeys. You also have to pick from which GNUPGHOME directory
you wish to export from.


.. code:: json

    {
      "target": "/home/johnsmith/.gnupg",
      "keyids": ["id1", "id2"],
      "encrypted": false
    }

Archival Store
==============

The archival store is mainly for cold storage. If you want to put a family
photo here, or maybe a readme file, or anything else that you don't want to
put on your computer or the cloud and want it in a secure cold storage location,
this is the place for you.

Directory Structure
-------------------

.. code::

    archival/
      file1
      file2
      manifest.lock.json

Put file in anyway you'd like here.

Actions Definition
------------------

TODO: To be written.

Action Hooks
============