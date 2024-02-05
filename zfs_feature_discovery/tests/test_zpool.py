from pathlib import Path
from typing import List

import pytest
from pytest import TempPathFactory

from zfs_feature_discovery.features import FeatureManager
from zfs_feature_discovery.zpool import ZpoolManager

from .conftest import ZfsCommandMocker, read_all_labels

TEST_DATA_DIR = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture
def zpool_get_output() -> bytes:
    with open(TEST_DATA_DIR / "zpool_get_output.txt", "rb") as f:
        return f.read()


@pytest.fixture
def zfs_get_output() -> bytes:
    fixtures = [
        "zfs_get_dataset_test1_output.txt",
        "zfs_get_zvol_zvol1_output.txt",
        "zfs_get_dataset_test2_output.txt",
    ]

    data = b""
    for fixture in fixtures:
        with open(TEST_DATA_DIR / fixture, "rb") as f:
            data += f.read()

    return data


@pytest.fixture
def zpool_datasets() -> List[str]:
    return ["test1", "zvol1", "test2"]


@pytest.fixture
def zpool(zpool_datasets: List[str]) -> ZpoolManager:
    return ZpoolManager(
        pool_name="rpool",
        zpool_command=Path("/zpool_test"),
        zfs_command=Path("/zfs_test"),
        datasets=zpool_datasets,
    )


@pytest.fixture
def mock_zpool_properties(
    zpool: ZpoolManager, zfs_command_mocker: ZfsCommandMocker, zpool_get_output: bytes
) -> None:
    zfs_command_mocker.mock(
        zpool._zpool_cmd,
        cmd=["/zpool_test", "get", "-Hp", "all", zpool.pool_name],
        stdout=zpool_get_output,
        stderr=b"hello",
        exit_code=0,
    )


@pytest.fixture
def mock_zfs_dataset_properties(
    zpool: ZpoolManager, zfs_command_mocker: ZfsCommandMocker, zfs_get_output: bytes
) -> ZpoolManager:
    zfs_command_mocker.mock(
        zpool._zfs_cmd,
        cmd=["/zfs_test", "get", "-Hp", "all", *zpool.full_datasets],
        stdout=zfs_get_output,
        stderr=b"hello",
        exit_code=0,
    )

    return zpool


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
async def test_zpool_get_properties(zpool: ZpoolManager) -> None:
    props = await zpool.get_properties()
    assert props != {}


# Random sprinkling of different types of values
ZPOOL_TEST_PROPS = frozenset(
    ["readonly", "size", "health", "guid", "feature@async_destroy"]
)
ZFS_DATASET_TEST_PROPS = frozenset(
    ["type", "guid", "readonly", "recordsize", "volsize", "volblocksize"]
)


@pytest.fixture(scope="function")
def feature_manager(tmp_path_factory: TempPathFactory) -> FeatureManager:
    fm = FeatureManager(
        feature_dir=tmp_path_factory.mktemp("features-"),
        zpool_props=ZPOOL_TEST_PROPS,
        zfs_dataset_props=ZFS_DATASET_TEST_PROPS,
        label_namespace="me.danielkza.io/test",
        zpool_label_format="zpool/{pool_name}.{property_name}",
        zfs_dataset_label_format="zfs-dataset/{pool_name}/{dataset_name}.{property_name}",
    )
    return fm


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
async def test_zpool_write_features(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    async with feature_manager:
        feature_manager.register_zpool(zpool)

        await feature_manager.refresh_all_zpools()

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/test/zpool/rpool.readonly": "off",
        "me.danielkza.io/test/zpool/rpool.size": "944892805120",
        "me.danielkza.io/test/zpool/rpool.health": "ONLINE",
        "me.danielkza.io/test/zpool/rpool.guid": "2706753758230323468",
        "me.danielkza.io/test/zpool/rpool.feature@async_destroy": "enabled",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zfs_dataset_properties")
async def test_zfs_dataset_get_properties(zpool: ZpoolManager) -> None:
    ds_props = {ds: props async for ds, props in zpool.dataset_properties()}
    for ds in zpool.full_datasets:
        assert ds_props[ds] != {}


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zfs_dataset_properties")
async def test_zfs_dataset_write_features(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    async with feature_manager:
        feature_manager.register_zpool(zpool)

        await feature_manager.refresh_zpool_datasets(zpool)

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/test/zfs-dataset/rpool/test1.readonly": "off",
        "me.danielkza.io/test/zfs-dataset/rpool/test1.volsize": "",
        "me.danielkza.io/test/zfs-dataset/rpool/test1.volblocksize": "",
        "me.danielkza.io/test/zfs-dataset/rpool/test1.recordsize": "131072",
        "me.danielkza.io/test/zfs-dataset/rpool/test1.type": "filesystem",
        "me.danielkza.io/test/zfs-dataset/rpool/test1.guid": "2574342567579829017",
        "me.danielkza.io/test/zfs-dataset/rpool/zvol1.readonly": "off",
        "me.danielkza.io/test/zfs-dataset/rpool/zvol1.volsize": "10737418240",
        "me.danielkza.io/test/zfs-dataset/rpool/zvol1.volblocksize": "16384",
        "me.danielkza.io/test/zfs-dataset/rpool/zvol1.recordsize": "",
        "me.danielkza.io/test/zfs-dataset/rpool/zvol1.type": "volume",
        "me.danielkza.io/test/zfs-dataset/rpool/zvol1.guid": "2814323311404247512",
        "me.danielkza.io/test/zfs-dataset/rpool/test2.readonly": "off",
        "me.danielkza.io/test/zfs-dataset/rpool/test2.volsize": "",
        "me.danielkza.io/test/zfs-dataset/rpool/test2.volblocksize": "",
        "me.danielkza.io/test/zfs-dataset/rpool/test2.recordsize": "131072",
        "me.danielkza.io/test/zfs-dataset/rpool/test2.type": "filesystem",
        "me.danielkza.io/test/zfs-dataset/rpool/test2.guid": "2574342567579829017",
    }


@pytest.mark.asyncio
@pytest.mark.usefixtures("mock_zpool_properties")
@pytest.mark.parametrize("zpool_datasets", [[]])
async def test_zpool_no_datasets_write_features(
    feature_manager: FeatureManager, zpool: ZpoolManager
) -> None:
    async with feature_manager:
        feature_manager.register_zpool(zpool)

        await feature_manager.refresh_all_zpools()

    all_labels = await read_all_labels(feature_manager.feature_dir)
    assert all_labels == {
        "me.danielkza.io/test/zpool/rpool.readonly": "off",
        "me.danielkza.io/test/zpool/rpool.size": "944892805120",
        "me.danielkza.io/test/zpool/rpool.health": "ONLINE",
        "me.danielkza.io/test/zpool/rpool.guid": "2706753758230323468",
        "me.danielkza.io/test/zpool/rpool.feature@async_destroy": "enabled",
    }
