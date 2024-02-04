from __future__ import annotations

import asyncio
import logging
from functools import wraps
from pathlib import Path

import aiofiles
import yaml
from argdantic import ArgParser
from pydantic import FilePath

from zfs_feature_discovery.config import Config, SettingsSource
from zfs_feature_discovery.features import FeatureManager
from zfs_feature_discovery.zpool import ZpoolManager

main = ArgParser()


def async_cmd(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        logging.basicConfig(level=logging.DEBUG)
        return asyncio.run(func(*args, **kwargs))

    return wrapped


async def load_config(config_path: Path | None) -> Config:
    if not config_path:
        return Config()

    async with aiofiles.open(config_path) as f:
        content = await f.read()

    data = yaml.safe_load(content)
    return Config.model_validate(data)


def settings_source(*args, **kwargs) -> SettingsSource:
    return SettingsSource(
        *args, env_prefix="ZFS_FEATURE_DISCOVERY_", env_nested_delimiter="_", **kwargs
    )


@main.command(sources=[settings_source])  # type: ignore
@async_cmd
async def run(
    oneshot: bool = False, interval: int = 60, config_path: FilePath | None = None
) -> None:
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
            await fm.refresh_zpools()
        else:
            while True:
                await asyncio.gather(fm.refresh_zpools(), asyncio.sleep(interval))


if __name__ == "__main__":
    main()
