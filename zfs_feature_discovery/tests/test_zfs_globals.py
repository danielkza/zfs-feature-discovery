import pytest

from zfs_feature_discovery.tests.conftest import CommandMocker
from zfs_feature_discovery.zfs_globals import ZfsGlobals, ZfsVersion


@pytest.mark.asyncio
async def test_zfs_version(
    command_mocker: CommandMocker,
    zfs_globals: ZfsGlobals,
    zfs_version_output: bytes,
) -> None:
    command_mocker.mock(
        zfs_globals._zfs_version_cmd,
        ["/zfs_test", "version"],
        stdout=zfs_version_output,
    )
    version = await zfs_globals.zfs_version()
    assert version == ZfsVersion(
        main="2.2.2-1",
        kernel="2.2.2-1",
    )


@pytest.mark.asyncio
async def test_zfs_version_missing(
    command_mocker: CommandMocker,
    zfs_globals: ZfsGlobals,
) -> None:
    command_mocker.mock(
        zfs_globals._zfs_version_cmd,
        ["/zfs_test", "version"],
        exit_code=255,
    )
    version = await zfs_globals.zfs_version()
    assert version == ZfsVersion(main=None, kernel=None)


@pytest.mark.asyncio
async def test_hostid(
    command_mocker: CommandMocker, zfs_globals: ZfsGlobals, hostid_output: bytes
) -> None:
    command_mocker.mock(
        zfs_globals._hostid_cmd,
        ["/hostid_test"],
        stdout=hostid_output,
    )
    hostid = await zfs_globals.hostid()
    assert hostid == "00fac711"


@pytest.mark.asyncio
async def test_hostid_missing(
    command_mocker: CommandMocker, zfs_globals: ZfsGlobals
) -> None:
    command_mocker.mock(
        zfs_globals._hostid_cmd,
        ["/hostid_test"],
        exit_code=255,
    )
    hostid = await zfs_globals.hostid()
    assert hostid is None
