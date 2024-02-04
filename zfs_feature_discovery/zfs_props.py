from __future__ import annotations

import asyncio
import asyncio.subprocess as subprocess
import logging
from asyncio import StreamReader
from typing import AsyncIterable, AsyncIterator, Literal, NamedTuple, Sequence


log = logging.getLogger(__name__)

Source = Literal["default", "local", "inherited", "temporary", "received"]


class ZfsProperty(NamedTuple):
    dataset: str
    name: str
    value: str
    source: Source | None

    @classmethod
    def parse(cls, value: str) -> ZfsProperty:
        ds, name, prop_value, source = value.split("\t")

        if source in ("default", "local", "inherited", "temporary", "received"):
            prop_source = source
        else:
            prop_source = None

        return cls(dataset=ds, name=name, value=prop_value, source=prop_source)


class ZfsCommandHarness:
    def __init__(self, command: str, *args: str) -> None:
        self.command = [command, *args]

    @classmethod
    async def stream_properties(
        cls, stream: StreamReader
    ) -> AsyncIterator[ZfsProperty]:
        while True:
            line = await stream.readline()
            if not line:
                break

            try:
                prop = ZfsProperty.parse(line.decode().rstrip())
            except ValueError:
                log.warning(f"Failed to parse zpool line, ignoring: {line}")
                continue

            yield prop

    async def handle_stderr(self, proc: subprocess.Process) -> int:
        cmd_name = self.command[0]

        assert proc.stderr
        while True:
            line = await proc.stderr.readline()
            if not line:
                break

            log.warning(f"{cmd_name}: {line.decode()}")

        exit_code = await proc.wait()
        log.info(f"{cmd_name}: finished with exit code {exit_code}")

        return exit_code

    async def _run(self, cmd: Sequence[str]) -> subprocess.Process:
        return await subprocess.create_subprocess_exec(
            *cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

    async def get_properties(
        self, *args: str
    ) -> tuple[AsyncIterable[ZfsProperty], asyncio.Future[int]]:
        cmd = [*self.command, *args]
        proc = await self._run(cmd)

        assert proc.stdout
        props = self.stream_properties(proc.stdout)
        fut = asyncio.create_task(self.handle_stderr(proc))

        return props, fut