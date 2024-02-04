from __future__ import annotations

import os
import re
from pathlib import Path
from typing import (
    Annotated,
    Any,
    Collection,
    FrozenSet,
    NewType,
    Sequence,
    Tuple,
    Type,
    cast,
)

from pydantic import BeforeValidator, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


ZPOOL_DEFAULT_PROPS = frozenset(
    [
        "altroot",
        "ashift",
        "capacity",
        "comment",
        "compatibility",
        "guid",
        "health",
        "readonly",
        "size",
        "version",
    ]
)


ZFS_DATASET_DEFAULT_PROPS = frozenset(
    [
        "checksum",
        "compression",
        "dedup",
        "encryption",
        "guid",
        "mounted",
        "origin",
        "readonly",
        "recordsize",
        "reservation",
        "sharenfs",
        "sharesmb",
        "type",
        "version",
        "volsize",
        "xattr",
    ]
)


def check_absolute(path: Path) -> Path:
    if not path.is_absolute():
        raise ValueError(f"Path must be absolute: {path}")

    return path


def check_executable(path: Path) -> Path:
    if not os.access(str(path), os.X_OK):
        raise ValueError(f"Path must be executable: {path}")

    return path


def parse_props_list(value: Any) -> Collection[str]:
    if isinstance(value, str):
        value = value.split(",")

    return frozenset(value)


PropsSet = NewType(
    "PropsSet", Annotated[FrozenSet[str], BeforeValidator(parse_props_list)]
)


def prepare_props_list(
    defaults: FrozenSet[str], value: FrozenSet[str]
) -> FrozenSet[str]:
    if "-all" in value:
        props = set()
    else:
        props = set(defaults)

    for user_prop in value:
        remove_prop = user_prop.lstrip("-")
        if remove_prop != user_prop:
            # Already handled earlier
            if remove_prop == "all":
                continue
            props.remove(remove_prop)
        else:
            props.add(user_prop)

    return frozenset(props)


class SettingsSource(EnvSettingsSource):
    def decode_complex_value(
        self, field_name: str, field: FieldInfo, value: Any
    ) -> Any:
        import pdb

        pdb.set_trace()
        if field.metadata != PropsSet:
            return super().decode_complex_value(field_name, field, value)

        return parse_props_list(value)


class Config(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ZFS_FEATURE_DISCOVERY_")

    zfs_binary: Path = Path("/usr/sbin/zfs")
    zpool_binary: Path = Path("/usr/sbin/zpool")
    zpool_filters: Sequence[re.Pattern] = (re.compile(r".+"),)

    zpool_props: PropsSet = PropsSet(frozenset())
    zfs_dataset_props: PropsSet = PropsSet(frozenset())

    feature_dir: Path = Path("/etc/kubernetes/node-feature-discovery/features.d/")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        env_settings = cast(EnvSettingsSource, env_settings)
        custom_source = SettingsSource(
            settings_cls,
            case_sensitive=env_settings.case_sensitive,
            env_prefix=env_settings.env_prefix,
            env_nested_delimiter=env_settings.env_nested_delimiter,
        )
        return (
            init_settings,
            custom_source,
        )

    @field_validator("zpool_props")
    @classmethod
    def validate_zpool_props(cls, value: FrozenSet[str]) -> FrozenSet[str]:
        return prepare_props_list(ZPOOL_DEFAULT_PROPS, value)

    @field_validator("zfs_dataset_props")
    @classmethod
    def validate_zfs_dataset_props(cls, value: FrozenSet[str]) -> FrozenSet[str]:
        return prepare_props_list(ZFS_DATASET_DEFAULT_PROPS, value)
