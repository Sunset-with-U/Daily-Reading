"""用户目录定位与环境注入。

必须在任何 `import pipeline` 之前调用 init_env()——pipeline.util 的路径
常量（及 dedupe/batches 的模块级文件常量）在 import 时求值。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "Daily-Reading"


def user_base_dir() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    # Linux/CI 开发环境走 XDG 约定
    xdg = os.environ.get("XDG_DATA_HOME", "")
    return (Path(xdg) if xdg else Path.home() / ".local" / "share") / APP_NAME


def bundled_root() -> Path:
    """出厂资源根：app 包与 pipeline/site/config 同级（仓库或 Briefcase 包内均成立）。"""
    return Path(__file__).resolve().parent.parent


def init_env() -> dict[str, Path]:
    """建用户目录并注入 DAILY_READING_* 环境变量（setdefault，可被外部覆盖）。幂等。"""
    base = user_base_dir()
    paths = {
        "data": base / "data",
        "user_config": base / "config",
        "logs": base / "logs",
        "site": bundled_root() / "site",
        "config": bundled_root() / "config",
    }
    for key in ("data", "user_config", "logs"):
        paths[key].mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("DAILY_READING_DATA_DIR", str(paths["data"]))
    os.environ.setdefault("DAILY_READING_USER_CONFIG_DIR", str(paths["user_config"]))
    os.environ.setdefault("DAILY_READING_CONFIG_DIR", str(paths["config"]))
    return paths
