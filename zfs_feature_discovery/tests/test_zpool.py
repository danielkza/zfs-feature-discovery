import pytest

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
