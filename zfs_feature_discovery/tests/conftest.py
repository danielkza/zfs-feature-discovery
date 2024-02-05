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
from zfs_feature_discovery.zpool import ZpoolManager

TEST_DATA_DIR = Path(__file__).resolve().parent / "fixtures"


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
        stdout: bytes = b"",
        stderr: bytes = b"",
        exit_code: int = 0,
        delay: float = 0,
    ) -> None:
        cmd_expected = cmd

        async def _run(cmd: Sequence[str]) -> Process:
            assert cmd == cmd_expected
            return await run_mock_process(stdout, stderr, exit_code, delay)

        self._mock = self._mocker.patch.object(obj, "_run", side_effect=_run)

    def check_called(self) -> None:
        assert self._mock
        self._mock.assert_called_once()

    def check_not_called(self) -> None:
        assert self._mock
        self._mock.assert_not_called()


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


# Random sprinkling of different types of values
@pytest.fixture
def zpool_test_props() -> frozenset[str]:
    return frozenset(["readonly", "size", "health", "guid", "feature@async_destroy"])


@pytest.fixture
def zfs_dataset_test_props() -> frozenset[str]:
    return frozenset(
        ["type", "guid", "readonly", "recordsize", "volsize", "volblocksize"]
    )


@pytest.fixture
def zpool_get_output() -> bytes:
    with open(TEST_DATA_DIR / "zpool_get_output.txt", "rb") as f:
        return f.read()


@pytest.fixture
def zfs_get_output() -> bytes:
    fixtures = [
        "zfs_get_dataset_test1_output.txt",
        "zfs_get_zvol_zvol1_output.txt",
        "zfs_get_dataset_test2_output.txt",
    ]

    data = b""
    for fixture in fixtures:
        with open(TEST_DATA_DIR / fixture, "rb") as f:
            data += f.read()

    return data


@pytest.fixture
def mock_zpool_properties(
    zpool: ZpoolManager, zfs_command_mocker: ZfsCommandMocker, zpool_get_output: bytes
) -> None:
    zfs_command_mocker.mock(
        zpool._zpool_cmd,
        cmd=["/zpool_test", "get", "-Hp", "all", zpool.pool_name],
        stdout=zpool_get_output,
        stderr=b"hello",
        exit_code=0,
    )


@pytest.fixture
def mock_zfs_dataset_properties(
    zpool: ZpoolManager, zfs_command_mocker: ZfsCommandMocker, zfs_get_output: bytes
) -> Generator[ZpoolManager, None, None]:
    zfs_command_mocker.mock(
        zpool._zfs_cmd,
        cmd=["/zfs_test", "get", "-Hp", "all", *zpool.full_datasets],
        stdout=zfs_get_output,
        stderr=b"hello",
        exit_code=0,
    )
    yield zpool
    zfs_command_mocker.check_called()


@pytest.fixture
def zfs_command_mocker(
    mocker: MockerFixture,
) -> Generator[ZfsCommandMocker, None, None]:
    m = ZfsCommandMocker(mocker)
    yield m


@pytest.fixture
def zpool_datasets() -> list[str]:
    return ["test1", "zvol1", "test2"]


@pytest.fixture
def zpool(zpool_datasets: list[str]) -> ZpoolManager:
    return ZpoolManager(
        pool_name="rpool",
        zpool_command=Path("/zpool_test"),
        zfs_command=Path("/zfs_test"),
        datasets=zpool_datasets,
    )


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
