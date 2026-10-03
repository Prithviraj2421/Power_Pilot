from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, Optional

TABULAR_DLL = "Microsoft.PowerBI.Tabular.dll"
ADOMD_DLL = "Microsoft.PowerBI.AdomdClient.dll"
REQUIRED = (TABULAR_DLL, ADOMD_DLL, "Microsoft.PowerBI.Tabular.Json.dll")


class DllNotFoundError(Exception):
    """The Analysis Services client libraries could not be located; the message lists where we looked."""


def _registry_install_dirs() -> list[Path]:
    """Install locations Power BI Desktop's installer records, newest layout first."""
    try:
        import winreg
    except ImportError:  # not Windows
        return []

    found: list[Path] = []
    for hive, key in (
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Microsoft Power BI Desktop"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Microsoft Power BI Desktop"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Microsoft Power BI Desktop"),
    ):
        try:
            with winreg.OpenKey(hive, key) as handle:
                value, _ = winreg.QueryValueEx(handle, "InstallLocation")
        except OSError:
            continue
        found.append(Path(value) / "bin")
    return found


def _default_dirs() -> list[Path]:
    roots = [os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA")]
    return [Path(r) / "Microsoft Power BI Desktop" / "bin" for r in roots if r]


def candidate_dirs(explicit: Optional[str] = None) -> list[Path]:
    """Where to look, in priority order: an explicit folder, then Desktop's own install."""
    explicit_dirs = [Path(explicit)] if explicit and explicit.strip() else []
    return [*explicit_dirs, *_registry_install_dirs(), *_default_dirs()]


def find_dll_dir(explicit: Optional[str] = None, candidates: Optional[Iterable[Path]] = None) -> Path:
    """The folder containing the TOM and ADOMD libraries.

    These ship with Power BI Desktop itself, so a tool launched from Desktop always has them and
    nothing needs downloading. They are the same build as the engine they talk to. Set
    ``POWERPILOT_TOM_DLL_DIR`` to point at a different copy (for example the NuGet packages
    ``Microsoft.AnalysisServices.retail.amd64`` and ``Microsoft.AnalysisServices.AdomdClient.retail.amd64``).
    """
    searched = list(candidates) if candidates is not None else candidate_dirs(explicit)
    for folder in searched:
        if all((folder / name).is_file() for name in REQUIRED):
            return folder

    where = "\n  ".join(str(p) for p in searched) or "(no locations)"
    raise DllNotFoundError(
        "Could not find the Analysis Services client libraries "
        f"({', '.join(REQUIRED)}). Looked in:\n  {where}\n"
        "Install Power BI Desktop, or set POWERPILOT_TOM_DLL_DIR to a folder containing them."
    )
