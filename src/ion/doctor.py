from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ion.config import AppConfig, resolve_credential, resolve_profile


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: str
    detail: str


class Doctor:
    def run(self, config: AppConfig, profile_name: str, mode: Literal["product", "evaluation"] = "product") -> list[DiagnosticCheck]:
        profile = resolve_profile(config, profile_name, mode)
        credential, key_name = resolve_credential(profile, mode)
        return [
            DiagnosticCheck("configuration", "passed", "TOML profile validated"),
            DiagnosticCheck("credential", "passed" if credential else "failed", f"{key_name} is set" if credential else f"Set {key_name} in your terminal"),
            DiagnosticCheck("model", "passed", f"{profile.provider}: {profile.model_id}"),
            DiagnosticCheck("limits", "passed", f"{profile.context_window} context; {profile.max_output_tokens} output"),
            DiagnosticCheck("network", "skipped", "Use /models for live model discovery"),
        ]
