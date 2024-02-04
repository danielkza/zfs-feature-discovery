import asyncio
import asyncio.subprocess as subprocess
from asyncio.subprocess import Process
from pathlib import Path
from typing import Generator, Sequence
import aiofiles

from aiofiles.threadpool.binary import AsyncBufferedIOBase
from aiofiles.tempfile import NamedTemporaryFile

import pytest
from pytest_mock import MockerFixture

from zfs_feature_discovery.zfs_props import ZfsCommandHarness


async def run_mock_process(
    stdout: bytes, stderr: bytes, exit_code: int, delay: float = 0, *args, **kwargs
) -> subprocess.Process:
    async def write(f: AsyncBufferedIOBase, data: bytes) -> None:
        await f.write(data)
        await f.flush()
        await f.seek(0)

    async with NamedTemporaryFile() as stdout_tmp, NamedTemporaryFile() as stderr_tmp:
        await asyncio.gather(write(stdout_tmp, stdout), write(stderr_tmp, stderr))

        cmd = f"sleep {delay} & cat /dev/fd/{stdout_tmp.fileno()} & cat /dev/fd/{stderr_tmp.fileno()} >&2 & wait; exit {exit_code}"
        proc = await subprocess.create_subprocess_shell(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            *args,
            **kwargs,
            executable="/bin/bash",
            pass_fds=(stdout_tmp.fileno(), stderr_tmp.fileno()),
        )
        return proc


class ZfsCommandMocker:
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

    def check(self):
        assert self._mock
        self._mock.assert_called_once()


@pytest.fixture
def zfs_command_mocker(
    mocker: MockerFixture,
) -> Generator[ZfsCommandMocker, None, None]:
    m = ZfsCommandMocker(mocker)
    yield m
    m.check()


async def read_labels_file(path: Path):
    async with aiofiles.open(path) as f:
        for line in await f.readlines():
            if line.startswith("#"):
                continue
            line = line.strip()
            if not line:
                continue

            key, value = line.split("=", 1)
            yield key, value


async def read_all_labels(path: Path):
    async def gen():
        for feature_file in path.glob("*"):
            if not feature_file.is_file():
                continue

            async for label in read_labels_file(feature_file):
                yield label

    return {k: v async for k, v in gen()}
