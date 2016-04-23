.. _introduction:

============
Introduction
============

Keys such SSH keys, GPG keys, and OTR keys can be hard to manage. They are
extremely sensitive as any leaks could be disastrous. Files like this have
several requirements:

1. Easy and secure backup to cold storage.
2. Verify that backups are not corrupted on cold storage.
3. Easily restore the backups for disaster recovery or just when transferring computers (not necessarily all files).
4. Keep track of changes to your keys as time move forward.

Keybank is a tool that helps you manage the backups of your key and complete the
objective above by storing your files on a LUKS encrypted ext4 partition. This
partition is just a file and can be loop mounted. These encrypted partition files
(hereby known as Keybank files) can then be transfered on to an USB drive for safe
keeping. Occasionally, one can pull out these USB drives and verify the content
by invoking the verification capabilities provided by Keybank.

General Workflow
================

To be written...

Stores
======

A central concept of Keybank is a **store**. Physically, a store is a directory
on the encrypted partition. Different stores are suited to keep different kind
of sensitive data due to different requirements. For example, the GPG master key
should not be on anything but cold storage. SSH keys, on the other hand, should
exist on both the cold storage as well as your devices.

Keybank provides the following stores out of the box. It is possible to add more
types when situation arises.

- **Synchronized Store**: Files stored in this store will be synchronized with the files on your computer. You can backup the state of your machine to it or restore it to your machine.
- **GPG Store**: It is desired to have your GPG master key stored on an offline storage and then export subkeys for each device. This store is designed to be your ``GNUPGHOME`` directory with the master key in it. You cannot backup the state of your machine to it. Restoring from this store to your machine consists of exporting the appropriate subkeys.
- **Archival (Cold) Store**: Files stored here are NOT synchronized with the files on your computer. You can backup to it by simply dragging files into it. There is no restore operations defined here.

Actions
=======

Keybank defines actions for stores. Each store implements these actions
differently. However, they should all conceptually perform the same operation
as described below:

- **Verify**: verify the integrity of the files in the store. This action is **mandatory to implement** for all stores.
- **Commit**: Commits the state of the store and produce a way for verification to work. This action is **mandatory to implement** for all stores.
- **Backup**: backup the state of your machine to the store. This action is optional for stores.
- **Restore**: restores the state of the store to your machine. This action is optional for stores.

Additionally, there are actions defined on the keybank file itself:

- **Attach**: unlock and mount the keybank file so you can access the content.
- **Detach**: Unmount the encrypted partition.
