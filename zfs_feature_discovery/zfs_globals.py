import logging
import re
from dataclasses import dataclass
from pathlib import Path
from subprocess import CalledProcessError
from typing import Optional

from zfs_feature_discovery.zfs_props import CommandHarness

log = logging.getLogger(__name__)


@dataclass
class ZfsVersion:
    main: Optional[str]
    kernel: Optional[str]


class ZfsGlobals:
    def __init__(
        self,
        zfs_command: Path,
        hostid_command: Path,
    ) -> None:
        self._zfs_version_cmd = CommandHarness(str(zfs_command), "version")
        self._hostid_cmd = CommandHarness(str(hostid_command))

    async def zfs_version(self) -> ZfsVersion:
        try:
            output = await self._zfs_version_cmd.check_output()
        except CalledProcessError:
            log.warning("Failed to get ZFS version")
            return ZfsVersion(main=None, kernel=None)

        main_version: Optional[str] = None
        kernel_version: Optional[str] = None
        for line in output.split("\n"):
            if match := re.match(r"^zfs-(\d\S+)", line):
                main_version = match.group(1)
            elif match := re.match(r"^zfs-kmod-(\d\S+)", line):
                kernel_version = match.group(1)

        return ZfsVersion(main=main_version, kernel=kernel_version)

    async def hostid(self) -> Optional[str]:
        try:
            output = await self._hostid_cmd.check_output()
        except CalledProcessError:
            log.warning("Failed to get hostid")
            return None

        return output.rstrip()
