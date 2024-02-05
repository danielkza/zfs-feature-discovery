import pytest
from pytest_mock import MockerFixture

from zfs_feature_discovery.tests.conftest import CommandMocker
from zfs_feature_discovery.zpool import ZpoolManager


@pytest.mark.asyncio
async def test_zpool_get_properties(
    zpool: ZpoolManager, command_mocker: CommandMocker, zpool_get_output: bytes
) -> None:
    command_mocker.mock(
        zpool._zpool_cmd,
        cmd=["/zpool_test", "get", "-Hp", "all", zpool.pool_name],
        stdout=zpool_get_output,
        stderr=b"",
        exit_code=0,
    )

    props = await zpool.get_properties()
    assert props != {}


@pytest.mark.asyncio
async def test_zfs_dataset_get_properties(
    zpool: ZpoolManager, command_mocker: CommandMocker, zfs_get_output: bytes
) -> None:
    command_mocker.mock(
        zpool._zfs_cmd,
        cmd=["/zfs_test", "get", "-Hp", "all", *zpool.full_datasets],
        stdout=zfs_get_output,
        stderr=b"",
        exit_code=0,
    )

    ds_props = await zpool.dataset_properties()
    for ds in zpool.full_datasets:
        assert ds_props[ds] != {}


@pytest.mark.asyncio
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_zfs_no_dataset_get_properties(
    mocker: MockerFixture, zpool: ZpoolManager, command_mocker: CommandMocker
) -> None:
    """
    If we call zfs with no datasets, we will get all datasets,
    so make sure we don't call it at all
    """

    ds_props = await zpool.dataset_properties()
    assert ds_props == {}

    command_mocker.mock(zpool._zfs_cmd, mocker.ANY, exit_code=1)
    command_mocker.check_not_called()
