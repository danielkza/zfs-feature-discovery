import stat
from datetime import UTC, datetime
from typing import AsyncIterator

import aiofiles
import aiofiles.os
import pytest
import pytest_asyncio
from pytest import TempPathFactory

from zfs_feature_discovery.features import FeatureManager
from zfs_feature_discovery.zfs_globals import ZfsGlobals
from zfs_feature_discovery.zpool import ZpoolManager

from .conftest import CommandMocker, read_all_labels


@pytest.fixture
def reference_time() -> datetime:
    return datetime(2024, 2, 7, 10, 42, 8, 52969, tzinfo=UTC)


@pytest.fixture
def expiry_time() -> datetime:
    return datetime(2024, 2, 7, 11, 42, 8, 52969, tzinfo=UTC)


@pytest.fixture
def expiry_time_s() -> str:
    return "2024-02-07T11:42:08.052969Z"


@pytest_asyncio.fixture
async def feature_manager(
    tmp_path_factory: TempPathFactory,
    zpool_test_props: frozenset[str],
    zfs_dataset_test_props: frozenset[str],
    zfs_globals: ZfsGlobals,
    reference_time: datetime,
) -> AsyncIterator[FeatureManager]:
    fm = FeatureManager(
        feature_dir=tmp_path_factory.mktemp("features-"),
        zpool_props=zpool_test_props,
        zfs_dataset_props=zfs_dataset_test_props,
        label_namespace="me.danielkza.io",
        zpool_label_format="zpool.{pool_name}.{property_name}",
        zfs_dataset_label_format="zfs.{pool_name}.{dataset_name}.{property_name}",
        global_label_format="zfs-global.{property_name}",
        zfs_globals=zfs_globals,
    )
    async with fm:
        async with fm.with_reference_time(reference_time):
            yield fm


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
async def test_zpool_write_features(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    feature_manager.register_zpool(zpool)
    await feature_manager.refresh_all_zpools()

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/zpool.rpool.readonly": "off",
        "me.danielkza.io/zpool.rpool.size": "944892805120",
        "me.danielkza.io/zpool.rpool.health": "ONLINE",
        "me.danielkza.io/zpool.rpool.guid": "2706753758230323468",
        "me.danielkza.io/zpool.rpool.feature_async_destroy": "enabled",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zfs_dataset_properties")
async def test_zfs_dataset_write_features(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    feature_manager.register_zpool(zpool)
    await feature_manager.refresh_zpool_datasets(zpool)

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/zfs.rpool.test1.readonly": "off",
        "me.danielkza.io/zfs.rpool.test1.volsize": "",
        "me.danielkza.io/zfs.rpool.test1.volblocksize": "",
        "me.danielkza.io/zfs.rpool.test1.recordsize": "131072",
        "me.danielkza.io/zfs.rpool.test1.type": "filesystem",
        "me.danielkza.io/zfs.rpool.test1.guid": "2574342567579829017",
        "me.danielkza.io/zfs.rpool.zvol1.readonly": "off",
        "me.danielkza.io/zfs.rpool.zvol1.volsize": "10737418240",
        "me.danielkza.io/zfs.rpool.zvol1.volblocksize": "16384",
        "me.danielkza.io/zfs.rpool.zvol1.recordsize": "",
        "me.danielkza.io/zfs.rpool.zvol1.type": "volume",
        "me.danielkza.io/zfs.rpool.zvol1.guid": "2814323311404247512",
        "me.danielkza.io/zfs.rpool.test_test2.readonly": "off",
        "me.danielkza.io/zfs.rpool.test_test2.volsize": "",
        "me.danielkza.io/zfs.rpool.test_test2.volblocksize": "",
        "me.danielkza.io/zfs.rpool.test_test2.recordsize": "131072",
        "me.danielkza.io/zfs.rpool.test_test2.type": "filesystem",
        "me.danielkza.io/zfs.rpool.test_test2.guid": "2574342567579829017",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_zpool_no_datasets_write_features(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    feature_manager.register_zpool(zpool)
    await feature_manager.refresh_all_zpools()

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/zpool.rpool.readonly": "off",
        "me.danielkza.io/zpool.rpool.size": "944892805120",
        "me.danielkza.io/zpool.rpool.health": "ONLINE",
        "me.danielkza.io/zpool.rpool.guid": "2706753758230323468",
        "me.danielkza.io/zpool.rpool.feature_async_destroy": "enabled",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
@pytest.mark.usefixtures("mock_zfs_global_properties")
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_features_cleanup(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    # write an extra file in the feature dir, check that it will get erased

    feature_file = feature_manager.feature_dir / "zfs-rubbish"
    async with aiofiles.open(feature_file, "w") as f:
        await f.write(
            """
# Generated by zfs-feature-discovery
rubbish=rubbish
"""
        )

    # This just makes sure we actually wrote correctly, otherwise the next
    # assertion is meaningless
    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {"rubbish": "rubbish"}

    feature_manager.register_zpool(zpool)
    await feature_manager.refresh()

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/zpool.rpool.readonly": "off",
        "me.danielkza.io/zpool.rpool.size": "944892805120",
        "me.danielkza.io/zpool.rpool.health": "ONLINE",
        "me.danielkza.io/zpool.rpool.guid": "2706753758230323468",
        "me.danielkza.io/zpool.rpool.feature_async_destroy": "enabled",
        "me.danielkza.io/zfs-global.ver": "2.2.2-1",
        "me.danielkza.io/zfs-global.kver": "2.2.2-1",
        "me.danielkza.io/zfs-global.hostid": "00fac711",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
@pytest.mark.usefixtures("mock_zfs_global_properties")
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_features_file_mode(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    feature_manager.register_zpool(zpool)
    await feature_manager.refresh()

    found = False
    for entry in await aiofiles.os.scandir(feature_manager.feature_dir):
        found = True

        file_stat = await aiofiles.os.stat(entry)
        file_mode = stat.S_IMODE(file_stat.st_mode)
        assert file_mode == 0o0644, f"File {entry.path} should have mode 0644"

    assert found, "FeatureManager should generate files"


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
@pytest.mark.usefixtures("mock_zfs_global_properties")
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_features_expiry(
    feature_manager: FeatureManager,
    zpool: ZpoolManager,
    expiry_time_s: str,
) -> None:
    feature_manager.register_zpool(zpool)
    await feature_manager.refresh()

    found = False
    for entry in await aiofiles.os.scandir(feature_manager.feature_dir):
        found = True

        async with aiofiles.open(entry) as f:
            lines = await f.readlines()

        assert f"# +expiry-time={expiry_time_s}\n" in lines

    assert found, "FeatureManager should generate files"


@pytest.mark.asyncio
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_zfs_missing(
    feature_manager: FeatureManager,
    command_mocker: CommandMocker,
    zfs_globals: ZfsGlobals,
    zpool: ZpoolManager,
) -> None:
    command_mocker.mock(
        zfs_globals._zfs_version_cmd,
        stderr="zfs: command not found\n".encode(),
        exit_code=127,
    )

    command_mocker.mock(
        zfs_globals._hostid_cmd,
        stdout="hostid: command not found\n".encode(),
        exit_code=127,
    )

    feature_manager.register_zpool(zpool)
    await feature_manager.refresh()

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/zpool.rpool.readonly": "",
        "me.danielkza.io/zpool.rpool.size": "",
        "me.danielkza.io/zpool.rpool.health": "",
        "me.danielkza.io/zpool.rpool.guid": "",
        "me.danielkza.io/zpool.rpool.feature_async_destroy": "",
        "me.danielkza.io/zfs-global.ver": "",
        "me.danielkza.io/zfs-global.kver": "",
        "me.danielkza.io/zfs-global.hostid": "",
    }


@pytest.mark.asyncio
async def test_get_expiry_reference_time(
    feature_manager: FeatureManager,
    expiry_time: datetime,
) -> None:
    assert feature_manager.get_expiry() == expiry_time


def test_format_expiry(
    feature_manager: FeatureManager, expiry_time: datetime, expiry_time_s: str
) -> None:
    assert feature_manager.format_expiry(expiry_time) == expiry_time_s
