import asyncio
import logging
import os
import re
from itertools import chain
from pathlib import Path
from typing import Any, AsyncContextManager, AsyncIterable, Iterable, Mapping, cast

import aiofiles
import aiofiles.os
from aiofiles.tempfile import NamedTemporaryFile

from zfs_feature_discovery.config import Config
from zfs_feature_discovery.zfs_props import ZfsProperty
from zfs_feature_discovery.zpool import ZpoolManager

log = logging.getLogger(__name__)

_chmod = aiofiles.os.wrap(os.chmod)


def sanitize_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", name)


class FeatureManager(AsyncContextManager["FeatureManager"]):
    _zpools: dict[str, ZpoolManager]

    @classmethod
    def from_config(cls, config: Config) -> "FeatureManager":
        return cls(
            feature_dir=config.feature_dir,
            zpool_props=config.zpool_props,
            zfs_dataset_props=config.zfs_dataset_props,
            label_namespace=config.label.namespace,
            zfs_dataset_label_format=config.label.zfs_dataset_format,
            zpool_label_format=config.label.zpool_format,
        )

    def __init__(
        self,
        *,
        feature_dir: Path,
        zpool_props: frozenset[str],
        zfs_dataset_props: frozenset[str],
        label_namespace: str,
        zpool_label_format: str,
        zfs_dataset_label_format: str,
        feature_file_prefix: str = "zfs-",
    ) -> None:
        self.feature_dir = feature_dir
        self.feature_file_prefix = feature_file_prefix
        self.label_namespace = label_namespace
        self.zpool_props = zpool_props
        self.zfs_dataset_props = zfs_dataset_props
        self.zpool_label_format = zpool_label_format
        self.zfs_dataset_label_format = zfs_dataset_label_format

        self._zpools = {}

    def register_zpool(self, zpool: ZpoolManager) -> None:
        self._zpools[zpool.pool_name] = zpool

    async def write_feature_file(self, name: str, content: AsyncIterable[str]) -> Path:
        full_name = f"{self.feature_file_prefix}{name}"
        full_name = name.replace("/", "_")
        full_path = self.feature_dir / full_name

        # Make sure to use a name starting with dot and rename atomically, as documented
        # by node-feature-discovery
        async with NamedTemporaryFile(
            dir=full_path.parent,
            prefix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_fname = cast(str, tmp_file.name)
            log.debug(f"Temporary feature file {tmp_fname}")

            try:
                async for chunk in content:
                    await tmp_file.write(chunk.encode())
                await tmp_file.flush()

                await _chmod(tmp_file.name, 0o644)
                await aiofiles.os.rename(tmp_fname, full_path)
                log.info(f"Wrote feature file {full_path}")
            except Exception:
                log.exception(f"Failed writing feature file {full_path}")
            finally:
                try:
                    await aiofiles.os.unlink(tmp_fname)
                except OSError:
                    pass

        return full_path

    async def write_zpool_features(self, zpool: ZpoolManager) -> Path:
        # We always write all the features; better an empty value than missing label
        system_props = await zpool.get_properties()
        all_props = {k: system_props.get(k) for k in self.zpool_props}
        pool_name = sanitize_name(zpool.pool_name)

        async def gen_content() -> AsyncIterable[str]:
            yield "# Generated by zfs-feature-discovery\n"

            ns = self.label_namespace
            for prop_name, prop_value in all_props.items():
                label = self.zpool_label_format.format(
                    pool_name=pool_name,
                    property_name=sanitize_name(prop_name),
                )
                value = prop_value.value if prop_value else ""

                yield f"{ns}/{label}={value}\n"

        return await self.write_feature_file(f"zpool.{pool_name}", gen_content())

    def gen_zfs_dataset_features(
        self, zpool: ZpoolManager, dataset: str, props: Mapping[str, ZfsProperty]
    ) -> Iterable[str]:
        # We always write all the features; better an empty value than missing label
        system_props = props
        all_props = {k: system_props.get(k) for k in self.zfs_dataset_props}

        pool_name = zpool.pool_name
        dataset_name = dataset.removeprefix(f"{pool_name}/")
        assert dataset_name != dataset

        pool_name = sanitize_name(pool_name)
        dataset_name = sanitize_name(dataset_name)

        yield "# Generated by zfs-feature-discovery\n"

        ns = self.label_namespace
        for prop_name, prop_value in all_props.items():
            label = self.zfs_dataset_label_format.format(
                pool_name=pool_name,
                dataset_name=dataset_name,
                property_name=sanitize_name(prop_name),
            )
            value = prop_value.value if prop_value else ""

            yield f"{ns}/{label}={value}\n"

    async def refresh_zpool(self, zpool: ZpoolManager) -> Path:
        log.info(f"Refreshing features for zpool {zpool.pool_name}")
        return await self.write_zpool_features(zpool)

    async def refresh_all_zpools(self) -> list[Path]:
        # make a copy to avoid any concurrency surprises
        zpools = list(self._zpools.values())

        feature_files = await asyncio.gather(*(map(self.refresh_zpool, zpools)))
        return list(feature_files)

    async def refresh_zpool_datasets(self, zpool: ZpoolManager) -> Path:
        async def gen() -> AsyncIterable[str]:
            async for ds, props in zpool.dataset_properties():
                log.info(f"Refreshing features for dataset {ds}")
                try:
                    chunk = "".join(self.gen_zfs_dataset_features(zpool, ds, props))
                except Exception:
                    log.exception(f"Failed to refresh features for dataset {ds}")
                else:
                    yield chunk

        pool_name = sanitize_name(zpool.pool_name)
        return await self.write_feature_file(f"zfs.{pool_name}", gen())

    async def refresh_all_zpool_datasets(self) -> list[Path]:
        # make a copy to avoid any concurrency surprises
        zpools = list(self._zpools.values())

        paths = await asyncio.gather(*(map(self.refresh_zpool_datasets, zpools)))
        return paths

    async def cleanup(self, keep: list[Path]) -> None:
        keep_names = frozenset(path.name for path in keep)
        for entry in await aiofiles.os.scandir(self.feature_dir):
            if not entry.is_file():
                continue

            if not entry.name.startswith(self.feature_file_prefix):
                continue

            if entry.name in keep_names:
                continue

            log.debug(f"Deleting {entry.path}")
            await aiofiles.os.unlink(entry)

    async def refresh(self) -> None:
        results = await asyncio.gather(
            self.refresh_all_zpools(), self.refresh_all_zpool_datasets()
        )

        paths = list(chain(*results))
        await self.cleanup(keep=paths)

    async def __aenter__(self) -> "FeatureManager":
        return self

    async def __aexit__(self, *_: Any) -> bool:
        return False
