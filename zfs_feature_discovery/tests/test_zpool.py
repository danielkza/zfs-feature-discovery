import pytest
from pytest_mock import MockerFixture

from zfs_feature_discovery.tests.conftest import ZfsCommandMocker
from zfs_feature_discovery.zpool import ZpoolManager


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
async def test_zpool_get_properties(zpool: ZpoolManager) -> None:
    props = await zpool.get_properties()
    assert props != {}


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zfs_dataset_properties")
async def test_zfs_dataset_get_properties(zpool: ZpoolManager) -> None:
    ds_props = {ds: props async for ds, props in zpool.dataset_properties()}
    for ds in zpool.full_datasets:
        assert ds_props[ds] != {}


@pytest.mark.asyncio
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_zfs_no_dataset_get_properties(
    mocker: MockerFixture, zpool: ZpoolManager, zfs_command_mocker: ZfsCommandMocker
) -> None:
    """
    If we call zfs with no datasets, we will get all datasets,
    so make sure we don't call it at all
    """

    ds_props = {ds: props async for ds, props in zpool.dataset_properties()}
    assert ds_props == {}

    zfs_command_mocker.mock(zpool._zfs_cmd, mocker.ANY, exit_code=1)
    zfs_command_mocker.check_not_called()
