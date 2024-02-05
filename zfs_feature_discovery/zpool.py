import logging
from pathlib import Path
from typing import Collection, Mapping, Optional

from aioitertools.itertools import groupby

from zfs_feature_discovery.zfs_props import (
    ZfsCommandHarness,
    ZfsProperty,
)

log = logging.getLogger(__name__)


class ZpoolManager:
    def __init__(
        self,
        pool_name: str,
        *,
        datasets: Collection[str],
        zpool_command: Path,
        zfs_command: Path,
    ) -> None:
        self.pool_name = pool_name
        self.datasets = frozenset(datasets)

        self._zpool_cmd = ZfsCommandHarness(
            str(zpool_command), "get", "-Hp", "all", pool_name
        )

        self._zfs_cmd = ZfsCommandHarness(
            str(zfs_command),
            "get",
            "-Hp",
            "all",
        )

    @property
    def full_datasets(self) -> frozenset[str]:
        return frozenset([f"{self.pool_name}/{ds}" for ds in self.datasets])

    async def get_properties(self) -> Optional[Mapping[str, ZfsProperty]]:
        try:
            props, exit_fut = await self._zpool_cmd.get_properties()
        except OSError:
            log.warning("Failed to run zpool")
            return None

        prop_map = {prop.name: prop async for prop in props}

        exit_code = await exit_fut
        if exit_code != 0:
            return None

        return prop_map

    async def dataset_properties(
        self,
    ) -> Mapping[str, Mapping[str, ZfsProperty]]:
        if not self.datasets:
            return {}

        try:
            all_props, exit_fut = await self._zfs_cmd.get_properties(
                *self.full_datasets
            )
        except OSError:
            log.warning("Failed to run zfs")
            return {ds: {} for ds in self.full_datasets}

        prefix = f"{self.pool_name}/"
        result: dict[str, Mapping[str, ZfsProperty]] = {}
        async for dataset, props in groupby(all_props, lambda prop: prop.dataset):
            relative_dataset = dataset.removeprefix(prefix)
            if relative_dataset == dataset:
                log.warning(
                    f"Received unexpected dataset {dataset} outside of {prefix}, "
                    f"skipping"
                )
                continue

            prop_map = {prop.name: prop for prop in props}
            result[dataset] = prop_map

        exit_code = await exit_fut
        if exit_code != 0:
            log.warning("Failed to run zfs")
            return {ds: {} for ds in self.full_datasets}

        return result
