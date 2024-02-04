from typing import Any
import pytest
from pytest import MonkeyPatch

from zfs_feature_discovery.config import (
    ZFS_DATASET_DEFAULT_PROPS,
    ZPOOL_DEFAULT_PROPS,
    Config,
)


@pytest.fixture
def config_defaults() -> dict[str, Any]:
    return {
        "zpools": {
            "pool1": frozenset(),
            "pool2": frozenset(["vol1"]),
        }
    }


@pytest.mark.parametrize(
    "env_value,result",
    [
        ("-all", []),
        (None, ZPOOL_DEFAULT_PROPS),
        ("test", [*ZPOOL_DEFAULT_PROPS, "test"]),
        ("-all,test", ["test"]),
    ],
)
def test_config_zpool_props(
    monkeypatch: MonkeyPatch, config_defaults: dict[str, Any], env_value, result
) -> None:
    if env_value is not None:
        monkeypatch.setenv("ZFS_FEATURE_DISCOVERY_ZPOOL_PROPS", env_value)

    config = Config.model_validate(config_defaults)
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
def test_config_zfs_dataset_props(
    monkeypatch: MonkeyPatch, config_defaults: dict[str, Any], env_value, result
) -> None:
    if env_value is not None:
        monkeypatch.setenv("ZFS_FEATURE_DISCOVERY_ZFS_DATASET_PROPS", env_value)

    config = Config.model_validate(config_defaults)
    assert set(config.zfs_dataset_props) == set(result)
