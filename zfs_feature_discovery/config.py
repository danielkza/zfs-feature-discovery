import os
import re
from pathlib import Path
from string import Formatter
from typing import (
    Annotated,
    Any,
    Collection,
    Dict,
    FrozenSet,
    NewType,
    Tuple,
    Type,
    cast,
)

from pydantic import BaseModel, BeforeValidator, Field, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)
from typing_extensions import get_args, get_origin

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
        origin = get_origin(field.annotation)
        if origin and issubclass(origin, Collection):
            args = get_args(field.annotation)
            if args == (str,):
                return parse_props_list(value)

        return super().decode_complex_value(field_name, field, value)


# not a real DNS label match, but good enough
LABEL_NAMESPACE_PATTERN = re.compile(r"^(?:[A-Za-z0-9]+\.)+[A-Za-z0-9]+$")
LABEL_PATH_PATTERN = re.compile(r"^[A-Za-z0-9-_.]*$")

_formatter = Formatter()


def validate_label_format(format: str, placeholders: set[str]) -> str:
    if not format:
        raise ValueError("Must not be empty")

    for literal, field_name, _, _ in _formatter.parse(format):
        if field_name and field_name not in placeholders:
            raise ValueError(f"Invalid placeholder: {field_name}")
        if not LABEL_PATH_PATTERN.match(literal):
            raise ValueError(
                "Must only contain alphanumeric characters, dash, underscore or dots"
            )

    return format


class LabelConfig(BaseModel):
    namespace: str = Field(
        default="feature.node.kubernetes.io", pattern=LABEL_NAMESPACE_PATTERN.pattern
    )
    zpool_format: str = Field(default="zpool.{pool_name}.{property_name}")
    zfs_dataset_format: str = Field(
        default="zfs.{pool_name}.{dataset_name}.{property_name}"
    )
    global_format: str = Field(default="zfs-global.{property_name}")

    @field_validator("zpool_format")
    @classmethod
    def validate_zpool_format(cls, value: str) -> str:
        return validate_label_format(value, {"pool_name", "property_name"})

    @field_validator("zfs_dataset_format")
    @classmethod
    def validate_zfs_dataset_props(cls, value: str) -> str:
        return validate_label_format(
            value, {"pool_name", "dataset_name", "property_name"}
        )

    @field_validator("global_format")
    @classmethod
    def validate_global_props(cls, value: str) -> str:
        return validate_label_format(value, {"property_name"})


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ZFS_FEATURE_DISCOVERY_", env_nested_delimiter="_"
    )

    zfs_command: Path = Path("/usr/sbin/zfs")
    zpool_command: Path = Path("/usr/sbin/zpool")
    hostid_command: Path = Path("/usr/bin/hostid")

    zpools: Dict[str, FrozenSet[str]] = Field(default_factory=dict, min_length=1)

    zpool_props: PropsSet = PropsSet(frozenset())
    zfs_dataset_props: PropsSet = PropsSet(frozenset())

    feature_dir: Path = Path("/etc/kubernetes/node-feature-discovery/features.d/")

    label: LabelConfig = Field(default_factory=LabelConfig)

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
