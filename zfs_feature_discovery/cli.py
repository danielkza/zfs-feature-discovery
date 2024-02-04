import asyncio
import logging
from functools import wraps
from pathlib import Path
from typing import (
    Any,
    Callable,
    Coroutine,
    Literal,
    Optional,
    ParamSpec,
    Type,
    TypeVar,
)

import aiofiles
import yaml
from argdantic import ArgParser  # type: ignore
from pydantic_settings import BaseSettings

from zfs_feature_discovery.config import Config, SettingsSource
from zfs_feature_discovery.features import FeatureManager
from zfs_feature_discovery.zpool import ZpoolManager

main = ArgParser()

T = TypeVar("T")
P = ParamSpec("P")


def async_cmd(func: Callable[P, Coroutine[Any, Any, T]]) -> Callable[P, T]:
    @wraps(func)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> T:
        return asyncio.run(func(*args, **kwargs))

    return wrapped


def default_config() -> Config:
    return Config()


async def load_config(config_path: Path | None) -> Config:
    if not config_path:
        return default_config()

    async with aiofiles.open(config_path) as f:
        content = await f.read()

    data = yaml.safe_load(content)
    return Config.model_validate(data)


def settings_source(cls: Type[BaseSettings], **kwargs: Any) -> SettingsSource:
    return SettingsSource(
        cls, env_prefix="ZFS_FEATURE_DISCOVERY_", env_nested_delimiter="_", **kwargs
    )


async def run(
    oneshot: bool = False,
    interval: float = 60,
    config_path: Path | None = None,
    log_level: Optional[Literal["ERROR", "WARNING", "INFO", "DEBUG", "TRACE"]] = None,
) -> None:
    logging.basicConfig(level=log_level)

    config = await load_config(config_path=config_path)
    logging.debug(f"Config: {config}")

    async with FeatureManager.from_config(config) as fm:
        for pool, datasets in config.zpools.items():
            logging.info(
                f"Monitoring zpool {pool} with datasets: {", ".join(datasets)}"
            )
            zpool = ZpoolManager(
                pool_name=pool,
                datasets=datasets,
                zpool_command=config.zpool_command,
                zfs_command=config.zfs_command,
            )
            fm.register_zpool(zpool)

        if oneshot:
            await fm.refresh()
        else:
            while True:
                await asyncio.gather(fm.refresh(), asyncio.sleep(interval))


main.command(sources=[settings_source])(async_cmd(run))

if __name__ == "__main__":
    main()
