from typing import Any

import pytest
from pydantic import ValidationError
from pytest import MonkeyPatch

from zfs_feature_discovery.config import (
    ZFS_DATASET_DEFAULT_PROPS,
    ZPOOL_DEFAULT_PROPS,
    Config,
    LabelConfig,
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
def test_config_zpool_props(
    monkeypatch: MonkeyPatch,
    config_defaults: dict[str, Any],
    env_value: str,
    result: list[str],
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
    monkeypatch: MonkeyPatch,
    config_defaults: dict[str, Any],
    env_value: str,
    result: list[str],
) -> None:
    if env_value is not None:
        monkeypatch.setenv("ZFS_FEATURE_DISCOVERY_ZFS_DATASET_PROPS", env_value)

    config = Config.model_validate(config_defaults)
    assert set(config.zfs_dataset_props) == set(result)


@pytest.mark.parametrize("namespace", ["test.danielkza.io"])
def test_config_validate_label_namespace_accept(namespace: str) -> None:
    LabelConfig(namespace=namespace)


@pytest.mark.parametrize(
    "namespace",
    [
        "a/b",
        "",
        "/b",
        "a.b.",
    ],
)
def test_config_validate_label_namespace_reject(namespace: str) -> None:
    with pytest.raises(ValidationError):
        LabelConfig(namespace=namespace)


@pytest.mark.parametrize(
    "fmt",
    [
        "zpool.{pool_name}.{property_name}",
        "zpool_{pool_name}_{property_name}",
        "{pool_name}_{property_name}",
    ],
)
def test_config_validate_label_zpool_format_accept(fmt: str) -> None:
    LabelConfig(zpool_format=fmt)


@pytest.mark.parametrize(
    "fmt",
    [
        "zpool/{pool_name}/{property_name}",  # no slashes
        "",  # non-empty
        "zpool.{unknown_placeholder}",  # valid placeholders only
    ],
)
def test_config_validate_label_zpool_format_reject(fmt: str) -> None:
    with pytest.raises(ValidationError):
        LabelConfig(zpool_format=fmt)


@pytest.mark.parametrize(
    "fmt",
    [
        "zfs.{pool_name}.{dataset_name}.{property_name}",
        "zfs_{pool_name}_{dataset_name}_{property_name}",
        "{pool_name}_{dataset_name}_{property_name}",
    ],
)
def test_config_validate_label_zfs_dataset_format_accept(fmt: str) -> None:
    LabelConfig(zfs_dataset_format=fmt)


@pytest.mark.parametrize(
    "fmt",
    [
        "zfs/{pool_name}/{dataset_name}/{property_name}",  # no slashes
        "",  # non-empty
        "zfs.{unknown_placeholder}",  # valid placeholders only
    ],
)
def test_config_validate_label_zfs_dataset_format_reject(fmt: str) -> None:
    with pytest.raises(ValidationError):
        LabelConfig(zfs_dataset_format=fmt)
