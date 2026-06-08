"""Account store for Chatly MCP.

Each account is a Playwright ``storage_state`` JSON file (saved after a
CloakBrowser login) that contains the ``token`` / ``refreshToken`` /
``organization-id`` cookies used to call the Vyro API.

A small ``accounts.json`` registry maps a friendly account name to its state
file plus a cached label/email.
"""
from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from . import config


def _jwt_claims(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return json.loads(base64.urlsafe_b64decode(payload))
    except Exception:
        return {}


@dataclass
class Account:
    name: str
    state_path: Path
    label: str = ""

    # ----- cookie / token helpers -------------------------------------------------
    def _cookies(self) -> dict:
        data = json.loads(self.state_path.read_text())
        return {c["name"]: c["value"] for c in data.get("cookies", [])}

    @property
    def token(self) -> Optional[str]:
        return self._cookies().get("token")

    @property
    def refresh_token(self) -> Optional[str]:
        return self._cookies().get("refreshToken")

    @property
    def org_id(self) -> Optional[str]:
        ck = self._cookies()
        return ck.get("organization-id") or _jwt_claims(ck.get("token", "")).get("sub")

    def expires_at(self) -> int:
        return int(_jwt_claims(self.token or "").get("exp", 0))

    def seconds_left(self) -> int:
        exp = self.expires_at()
        return max(0, exp - int(time.time())) if exp else 0

    def is_expired(self, skew: int = 60) -> bool:
        exp = self.expires_at()
        if not exp:
            return True
        return time.time() > (exp - skew)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "label": self.label,
            "org_id": self.org_id,
            "expires_in_sec": self.seconds_left(),
            "expired": self.is_expired(),
        }


class AccountStore:
    def __init__(self) -> None:
        self.registry_path = config.ACCOUNTS_FILE
        self._round_robin = 0

    # ----- registry I/O -----------------------------------------------------------
    def _load_registry(self) -> dict:
        if self.registry_path.exists():
            return json.loads(self.registry_path.read_text())
        return {}

    def _save_registry(self, reg: dict) -> None:
        self.registry_path.write_text(json.dumps(reg, indent=2))

    def register(self, name: str, state_path: Path, label: str = "") -> Account:
        reg = self._load_registry()
        reg[name] = {"state_path": str(state_path), "label": label}
        self._save_registry(reg)
        return Account(name=name, state_path=Path(state_path), label=label)

    # ----- lookups ----------------------------------------------------------------
    def list(self) -> list[Account]:
        reg = self._load_registry()
        out: list[Account] = []
        for name, meta in reg.items():
            sp = Path(meta["state_path"])
            if sp.exists():
                out.append(Account(name=name, state_path=sp, label=meta.get("label", "")))
        # Also auto-discover bare *_state.json files not yet registered.
        for sp in config.PROFILES_DIR.glob("*_state.json"):
            nm = sp.name[: -len("_state.json")]
            if nm not in reg:
                out.append(Account(name=nm, state_path=sp))
        return out

    def get(self, name: Optional[str]) -> Account:
        accounts = self.list()
        if not accounts:
            raise RuntimeError(
                "No ChatlyAI accounts found. Run a login first "
                "(chatly_login tool or chatly_mcp.login)."
            )
        if name:
            for a in accounts:
                if a.name == name:
                    return a
            raise RuntimeError(f"Account '{name}' not found. Have: {[a.name for a in accounts]}")
        return accounts[0]

    def pick(self, strategy: str = "round_robin") -> Account:
        """Pick an account for a job. Prefers non-expired ones."""
        accounts = [a for a in self.list() if not a.is_expired()] or self.list()
        if not accounts:
            raise RuntimeError("No accounts available.")
        if strategy == "round_robin":
            a = accounts[self._round_robin % len(accounts)]
            self._round_robin += 1
            return a
        return accounts[0]
