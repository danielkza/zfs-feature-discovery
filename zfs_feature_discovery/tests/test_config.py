import pytest
from pytest import MonkeyPatch

from zfs_feature_discovery.config import (
    ZFS_DATASET_DEFAULT_PROPS,
    ZPOOL_DEFAULT_PROPS,
    Config,
)


@pytest.mark.parametrize(
    "env_value,result",
    [
        ("-all", []),
        (None, ZPOOL_DEFAULT_PROPS),
        ("test", [*ZPOOL_DEFAULT_PROPS, "test"]),
        ("-all,test", ["test"]),
    ],
)
def test_config_zpool_props(monkeypatch: MonkeyPatch, env_value, result):
    if env_value is not None:
        monkeypatch.setenv("ZFS_FEATURE_DISCOVERY_ZPOOL_PROPS", env_value)

    config = Config()
    assert set(config.zpool_props) == set(result)


@pytest.mark.parametrize(
    "env_value,result",
    [
        ("-all", []),
        (None, ZFS_DATASET_DEFAULT_PROPS),
        ("test", [*ZFS_DATASET_DEFAULT_PROPS, "test"]),
        ("-all,test", ["test"]),
    ],
)
def test_config_zfs_dataset_props(monkeypatch: MonkeyPatch, env_value, result):
    if env_value is not None:
        monkeypatch.setenv("ZFS_FEATURE_DISCOVERY_ZFS_DATASET_PROPS", env_value)

    config = Config()
    assert set(config.zfs_dataset_props) == set(result)
