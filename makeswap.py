#!/usr/bin/env python
#coding:utf-8

import os
import stat
import collections
import logging
from subprocess import check_call, check_output, CalledProcessError, PIPE, STDOUT


SWAP_DEVICES_ENV_VAR_NAME = "SWAP_DEVICES"

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("makeswap")

FSEntry = collections.namedtuple("FSEntry", ["fs", "dir", "type", "options", "dump", "pass_"])
SwapEntry = collections.namedtuple("SwapEntry", ["fname", "type", "size", "used", "priority"])


#TODO: How is this going to work if a partition is mouned as swap already?


def is_block_device(device_name):
    """
    Validate whether a device is a block device.
    """
    try:
       mode = os.stat(device_name).st_mode
    except OSError:
        logger.warning("Device %s does not exist", device_name)
        return False
    return stat.S_ISBLK(mode)

def list_swaps():
    """
    Parse the swapon summary output
    """
    entries = []
    swap_summary = check_output(["swapon", "--summary"])
    for line in filter(bool, swap_summary.split("\n"))[1:]:
        entries.append(SwapEntry(*filter(bool, line.replace("\t", " ").split(" "))))
    return entries

def is_swap(device_name):
    return device_name in [entry.fname for entry in list_swaps()]

def setup_swap(device_name):
    """
    Enable swap on a device (mkswap)
    """
    # Ensure the volume is available
    logger.debug("Ensure unmounted: %s", device_name)
    try:
        check_output(["umount", device_name], stderr=STDOUT)
    except CalledProcessError as e:
        if "not mounted" not in e.output:
            logger.warning("An error occured unmounting: %s", e.output)

    # Create a swap partition
    logger.debug("Creating swap partition on %s", device_name)
    check_call(["mkswap", "--force", device_name], stdout=PIPE, stderr=PIPE)

def make_fstab(existing_entries, swap_devices):
    """
    Create a new fstab list
    """
    new_entries = [entry for entry in existing_entries if entry.fs not in swap_devices]
    new_entries.extend([FSEntry(entry, "none", "swap", "defaults", "0", "0") for entry in swap_devices])
    return new_entries

def read_fstab(path):
    """
    Read an existing fstab
    """
    entries = []
    with open(path) as f:
        for i, line in enumerate(f):
            line = line.strip().replace("\t", " ")
            if line:
                args = filter(bool, map(lambda s: s.strip(), line.split(" ")))
                entries.append(FSEntry(*args))
            else:
                logger.warning("Empty line in fstab: %s", i+1)
    return entries

def update_fstab(path, swap_devices):
    """
    Update the fstab with swap entries
    """
    logger.info("Generating new fstab at %s", path)
    existing_entries = read_fstab(path)
    new_entries = make_fstab(existing_entries, swap_devices)
    with open(path, "w") as f:
        for entry in new_entries:
            logger.info("Adding %s as %s", entry.fs, entry.type)
            f.write("\t".join(entry))
            f.write("\n")

def mount_swap_devices():
    """
    Update our filesystem accoding to our fstab (make sure we unmount
    newly created swap first, then enable swap)
    """
    for cmd in [["mount", "--all"], ["swapon", "--all"]]:
        logger.debug("System: %s", " ".join(cmd))
        check_call(cmd, stdout=PIPE, stderr=PIPE)

def get_env_swap_list(env_var_name):
    """
    Retrieve the list of swap devices we were ask to set up via
    an environment variable
    """
    devices = os.environ.get(env_var_name, "")
    return filter(bool, map(lambda s: s.strip(), devices.split(",")))

def main(fstab, swap_devices_env_var):
    # List the devices passed to us in the environment
    swap_devices = get_env_swap_list(swap_devices_env_var)

    # Check the devices we're to mount as swap are block devices and not swap yet
    logger.info("Devices to be mounted as swap: %s", ", ".join(swap_devices))
    _swap_devices = filter(lambda d: not is_swap(d), swap_devices)
    for device in _swap_devices:
        if not is_block_device(device):
            logger.critical("Device %s is not a block device", device)
            return

    # Setup our swap devices
    update_fstab(fstab, _swap_devices)
    map(setup_swap, _swap_devices)
    mount_swap_devices()

    # Validate swap is enabled on the devices
    for device in swap_devices:
        if is_swap(device):
            logger.info("Swap enabled on: %s", device)


if __name__ == "__main__":
    main("/etc/fstab", SWAP_DEVICES_ENV_VAR_NAME)
