import asyncio
import asyncio.subprocess as subprocess
from asyncio.subprocess import Process
from pathlib import Path
from typing import Any, AsyncIterable, Generator, Optional, Sequence, cast
from unittest.mock import MagicMock, Mock

import aiofiles
import pytest
from aiofiles.tempfile import NamedTemporaryFile
from aiofiles.threadpool.binary import AsyncBufferedIOBase
from pytest_mock import MockerFixture

from zfs_feature_discovery.config import Config
from zfs_feature_discovery.features import FeatureManager
from zfs_feature_discovery.zfs_props import ZfsCommandHarness


async def run_mock_process(
    stdout: bytes,
    stderr: bytes,
    exit_code: int,
    delay: float = 0,
    **kwargs: Any,
) -> subprocess.Process:
    async def write(f: AsyncBufferedIOBase, data: bytes) -> None:
        await f.write(data)
        await f.flush()
        await f.seek(0)

    async with NamedTemporaryFile() as stdout_tmp, NamedTemporaryFile() as stderr_tmp:
        await asyncio.gather(write(stdout_tmp, stdout), write(stderr_tmp, stderr))

        cmd = (
            f"sleep {delay} & cat /dev/fd/{stdout_tmp.fileno()} & "
            f"cat /dev/fd/{stderr_tmp.fileno()} >&2 & wait; exit {exit_code}"
        )
        proc = await subprocess.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **kwargs,
            executable="/bin/bash",
            pass_fds=(stdout_tmp.fileno(), stderr_tmp.fileno()),
        )
        return proc


class ZfsCommandMocker:
    _mock: Optional[Mock]

    def __init__(self, mocker: MockerFixture) -> None:
        self._mocker = mocker
        self._mock = None

    def mock(
        self,
        obj: ZfsCommandHarness,
        cmd: Sequence[str],
        stdout: bytes,
        stderr: bytes,
        exit_code: int,
        delay: float = 0,
    ) -> None:
        cmd_expected = cmd

        async def _run(cmd: Sequence[str]) -> Process:
            assert cmd == cmd_expected
            return await run_mock_process(stdout, stderr, exit_code, delay)

        self._mock = self._mocker.patch.object(obj, "_run", side_effect=_run)

    def check(self) -> None:
        assert self._mock
        self._mock.assert_called_once()


@pytest.fixture
def zfs_command_mocker(
    mocker: MockerFixture,
) -> Generator[ZfsCommandMocker, None, None]:
    m = ZfsCommandMocker(mocker)
    yield m
    m.check()


async def read_labels_file(path: Path) -> AsyncIterable[tuple[str, str]]:
    async with aiofiles.open(path) as f:
        for line in await f.readlines():
            if line.startswith("#"):
                continue
            line = line.strip()
            if not line:
                continue

            key, value = line.split("=", 1)
            yield key, value


async def read_all_labels(path: Path) -> dict[str, str]:
    async def gen() -> AsyncIterable[tuple[str, str]]:
        for feature_file in path.glob("*"):
            if not feature_file.is_file():
                continue

            async for label in read_labels_file(feature_file):
                yield label

    return {k: v async for k, v in gen()}


@pytest.fixture
def config_defaults() -> dict[str, Any]:
    return {
        "zpools": {
            "pool1": [],
            "pool2": ["vol1"],
        }
    }


@pytest.fixture
def mock_default_config(mocker: MockerFixture, config_defaults: dict[str, Any]) -> None:
    config = Config.model_validate(config_defaults)
    mocker.patch("zfs_feature_discovery.cli.default_config", return_value=config)


@pytest.fixture
def mock_feature_manager(mocker: MockerFixture) -> MagicMock:
    fm_mock = cast(MagicMock, mocker.MagicMock())
    fm_mock.__aenter__ = mocker.AsyncMock(return_value=fm_mock)
    fm_mock.refresh = mocker.AsyncMock()

    def from_config(config: Config) -> Any:
        return fm_mock

    mocker.patch.object(FeatureManager, "from_config", side_effect=from_config)
    return fm_mock
