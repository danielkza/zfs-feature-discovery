import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml
from pytest import MonkeyPatch, TempPathFactory
from pytest_mock import MockerFixture

from zfs_feature_discovery.cli import main, run
from zfs_feature_discovery.config import Config
from zfs_feature_discovery.features import FeatureManager


@pytest.mark.usefixtures("mock_default_config")
def test_cli_config_load_path_from_env(
    tmp_path_factory: TempPathFactory,
    monkeypatch: MonkeyPatch,
    mocker: MockerFixture,
    mock_feature_manager: MagicMock,
    config_defaults: dict[str, Any],
) -> None:
    config_data = config_defaults.copy()
    config_data.update({"zfs_command": "/hello-world"})

    tmp_dir = tmp_path_factory.mktemp("cli-")
    config_path = tmp_dir / "config.yaml"
    config_path.write_text(yaml.dump(config_data))

    monkeypatch.setenv("ZFS_FEATURE_DISCOVERY_CONFIG_PATH", str(config_path))

    def from_config(config: Config) -> Any:
        assert str(config.zfs_command) == "/hello-world"
        return mock_feature_manager

    mocker.patch.object(FeatureManager, "from_config", side_effect=from_config)
    main(["--oneshot"])

    mock_feature_manager.refresh.assert_called_once()


@pytest.mark.usefixtures("mock_default_config")
@pytest.mark.asyncio
async def test_cli_sleep_interval(mock_feature_manager: MagicMock) -> None:
    try:
        async with asyncio.timeout(0.25):
            await run(sleep_interval=0.1)
    except asyncio.TimeoutError:
        pass

    assert mock_feature_manager.refresh.call_count == 3


@pytest.mark.usefixtures("mock_default_config")
@pytest.mark.asyncio
async def test_cli_oneshot(mock_feature_manager: MagicMock) -> None:
    async with asyncio.timeout(0.1):
        await run(oneshot=True)

    assert mock_feature_manager.refresh.call_count == 1
