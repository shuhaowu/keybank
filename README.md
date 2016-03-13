Keybank
=======

[![Build Status](https://travis-ci.org/shuhaowu/keybank.svg?branch=master)](https://travis-ci.org/shuhaowu/keybank)

A set of tools and scripts that lives on an USB drive to manage keys
stored on this device.

The motivation of this tool is to have a standardized way to *backup*
encryption keys, GPG keys, SSL keys, password files, and any other files that
are sensitive to some external media. Keybank provides a system to keep track
of what files is what, how the files changed, and verification systems to
verify if the files are corrupt.

Keybank also provides some helper tools to restore GPG keys by exporting only
the subkeys. It does not do automatic backups, however, as it is assumed that
you would manage your GPG keys directly in the keybank mounted path using 
`GNUPGHOME` rather than copying it from your home folder to the keybank.

Tain tools are available:

1. Creating a new keybank.
2. Syncing a files to the keybank.
3. Verifying the keybank.
4. Exporting GPG home directory without the master key for usage.

Current Status: not really ready, things missing below

- [x] tests (travis CI)
- [ ] GPG restorer
- [ ] use git to verify files as well as history
- [ ] investigate into seeing if the verification is sufficient (currently hash them and compare against recorded version)
- [ ] make the system more modular so we can have more backends 


How does it work?
-----------------

A keybank file is simply a file that is formatted by cryptsetup and ext4. This
file can be safely stored on an USB drive. The encrypted ext4 partition
contains a directory of sensitive files (ssh keys, otr keys, etc). These files
are specified by a manifest file which allows keybank to automatically find
the files on your machine and copy the encrypted partition. Once copied onto
the system, it allows you to examine changes and history by using git.

Furthermore, Keybank includes a module that allows you to restore your GPG
keys stored on the encrypted partition such that the master key never leaves
the encrypted partition and only the subkeys are restored.

Need other use cases? Keybank is relatively modular. Feel free to contribute.

Install
-------

You will need the following:

- Linux distribution with LUKS and cryptsetup
- git
- bash (or equivalent)
- python3 (python2 should work)

You can simply install via:

    $ python setup.py install

Alternatively, you can use this without installing by calling `./keybank`
instead of `keybank`. This is handy if you want to include this software
directly on your USB drive.

Basic workflow (Tutorial)
-------------------------

First, we need to use a root shell. This is to add a thin layer of
protection. (also, keybank will need things like `mount`). We also
want to set umask to be 077 as we want files/directories created by us
to be only accessible by root. Note: Keybank on startup will set this
by itself, but it will not extend to your shell session. This is why
we are doing it.

```console
$ sudo -s
# umask 077
```

### Initializing a Keybank File ###

Now we can create a keybank file called `kb1` at `/`.  This will ask you to
create it with a password, it may ask you for the password another time to
unlock it as it unlocks and mounts the partition. To do this:

```console
# keybank create /kb1
```

You will get something like the following when the creation completes:

```
[2016-03-10 02:20:37][INFO] ==========================
[2016-03-10 02:20:37][INFO] KEYBANK BOOTSTRAP COMPLETE
[2016-03-10 02:20:37][INFO] ==========================
[2016-03-10 02:20:37][INFO] 
[2016-03-10 02:20:37][INFO] Done creating keybank. It should be mounted at /mnt/keybank-kb1
[2016-03-10 02:20:37][INFO] To go into it, you need to be root.
[2016-03-10 02:20:37][INFO] 
[2016-03-10 02:20:37][INFO] To unmount, do:
[2016-03-10 02:20:37][INFO] # keybank detach kb1
```

At this point, a keybank file has been created and mounted at `/mnt/keybank-kb1`. This file is 128MB, which will be the maximum amount of data you can store. Inside this path, it looks like this:

```console
# cd /mnt/keybank-kb1
# ls -l
total 14
drwx------ 3 root root  1024 Mar 10 02:20 generic
drwx------ 2 root root  1024 Mar 10 02:20 gpg
drwx------ 2 root root 12288 Mar 10 02:20 lost+found
```

*(For now, we are going to ignore the `gpg` directory.)*

The `generic` directory is where you keep sensitive files. The directory structure in here mirrors your machine directory structure. Example: `/home/johnsmith/.ssh/id_rsa` will be under `generic/home/johnsmith/.ssh/id_rsa`. 

### Getting Ready To Backup ###

There is a special file in `generic` named `manifest.json`. This should already be created by keybank during the initialization.

`generic/manifest.json` a JSON file specifying what to backup. We need to edit this file with an editor. If we want to backup our SSH keys and OTR keys, we'd fill the content of this file to be in the format of the following:

```json
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
```

As you can see, the manifest file is a list of objects. Each object have two required fields:

- `path`: the path to backup. This can be a glob like `/home/johnsmith/.ssh/id_rsa*`. This can be anything that python's [`glob.glob`](https://docs.python.org/3/library/glob.html#glob.glob) can handle.
- `amount`: since the path is a glob, we want to ensure that a correct number of files is backed up. This field is an integer that equals the number of paths the `path` glob expands to. In the example above, 4 indicates that there are 4 files that starts with `/home/johnsmith/.ssh/id_rsa*`.

The `comment` field is mainly for yourself. This field may also be used in the future for keybank. However it will remain optional.`

Save this file in `generic/manifest.json`.

### Backup ###

Now that we are ready to backup:

```console
# keybank backup kb1
```

We gave the argument `kb1` as the name of our keybank file is kb1. This becomes an unique identifier when the keybank file is attached (mounted).

If you want to just observe what would happen and not actually run a real backup, you can use the dry run functionality. It will print the log but will not actually change any files:

```console
# keybank backup kb1 --dry-run
[2016-03-10 02:37:54][INFO] scanning keybank
[2016-03-10 02:37:54][INFO] backing up generic files
[2016-03-10 02:37:54][INFO] copy ...
.....
.....
```

After you backup, it is recommended for you to examine the changes and commit it into git. A local git repository (no remotes) is setup for you during the initialization.

While backing up, keybank will automatically note the owner, group, and the
hash of the file. The owner and the group is used for restoring to set the
permission correctly. The hash is used later to verify the backup content, in
case where a drive fails. All this information is stored a new file inside the `generic` folder called `manifest.json.lock`. If you open the file, you will be presented with a hash of this information for each file. All globs are expanded out for now.

You also should commit the `manifest.json.lock` file into the git repository for tracking.

### Detaching (Removing the USB) ###

Before remove the USB, you must unmount the partition and close it in LUKS. Keybank calls this "detach" and it provides you with a simple way to do this:

```console
# keybank detach kb1
[2016-03-10 02:39:55][INFO] EXECUTING: umount /mnt/keybank-kb1
[2016-03-10 02:39:55][INFO] EXECUTING: cryptsetup luksClose kb1
[2016-03-10 02:39:55][INFO] keybank detached!
```

Now if you try to go to `/mnt/keybank-kb1`, you will realize it has been removed. You can safely remove your USB now.

### Attaching (Unlock the files) ###

After you detach, if you want to reattach, it is as simple as:

```console
# keybank attach /kb1
[2016-03-10 02:46:51][INFO] EXECUTING: cryptsetup luksOpen /kb1 kb1
Enter passphrase for /kb1: 
[2016-03-10 02:46:56][INFO] EXECUTING: mount /dev/mapper/kb1 /mnt/keybank-kb1
[2016-03-10 02:46:56][INFO] keybank 'kb1' attached and mounted at /mnt/keybank-kb1
```

You can change the path from `/kb1` to the correct location of course. The name of the keybank after attachment is always going to just be the filename.

### Verifying ###

To verify the backup, you can simply run:

```console
# keybank verify kb1
[2016-03-10 02:49:40][INFO] scanning keybank
[2016-03-10 02:49:40][INFO] verifying files
....
```

This verification will use the information from `manifest.json.lock`

### Restore ###

To restore, simply run

```console
# keybank restore kb1
```

This will restore all files specified in `manifest.json.lock`, set the owner and group information and set all files to be mode 0600.

If you want to see a dry run of this:

```console
# keybank restore kb1 --dry-run
```

### Recommended Setup ###

I recommend that you setup a keybank file on a secure machine at a location like `/kb`. 

After backing up your files to the keybank. I recommend that you go and get several USB drives, format them to ext4, copy /kb to each USB drive. 

I recommend you verify the USB drives every year and ensure they are kept in a safe location. Formulate a plan to replace your USB drives as you don't want them to die of old age.

GPG Tutorial
------------

Not yet available

Usage
-----

Run `keybank --help` or `keybank <subcommand> --help` to see.
