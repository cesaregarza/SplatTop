#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

YAML_RW = YAML()
YAML_RW.indent(mapping=2, sequence=4, offset=2)
YAML_RW.preserve_quotes = True

SOURCE_SECRET_FILE_DEFAULT = Path(
    "secrets/competition-admins/comp-auth-secrets.enc.yaml"
)
CONFIG_VALUES_FILE = Path("helm/splattop/values.yaml")
CONFIG_FASTAPI_TEMPLATE_FILE = Path(
    "helm/splattop/templates/fastapi-deployment.yaml"
)
CONFIG_SOPS_FILE = Path(".sops.yaml")
CONFIG_ARGO_APP_FILE = Path(
    "argocd/applications/splattop-prod-comp-auth-secrets.yaml"
)
CONFIG_SECRET_DIR = Path("secrets/splattop-prod-comp-auth")
CONFIG_SECRET_FILE = CONFIG_SECRET_DIR / "comp-auth-secrets.enc.yaml"
CONFIG_SECRET_KUSTOMIZATION_FILE = CONFIG_SECRET_DIR / "kustomization.yaml"
CONFIG_SECRET_KSOPS_FILE = CONFIG_SECRET_DIR / "ksops.yaml"
CONFIG_SECRET_README_FILE = CONFIG_SECRET_DIR / "README.md"
CONFIG_SECRET_PATH_REGEX = r"^secrets/splattop-prod-comp-auth/.*\.enc\.yaml$"

ADMIN_ENV_NAME = "COMP_AUTH_ADMIN_DISCORD_IDS"
ADMIN_SECRET_NAME = "splattop-comp-auth-secrets"
COMP_AUTH_SESSION_SECRET_ENV_NAME = "COMP_AUTH_SESSION_SECRET"
COMP_DISCORD_CLIENT_ID_ENV_NAME = "COMP_DISCORD_CLIENT_ID"
COMP_DISCORD_CLIENT_SECRET_ENV_NAME = "COMP_DISCORD_CLIENT_SECRET"
COMP_DISCORD_REDIRECT_URI_ENV_NAME = "COMP_DISCORD_REDIRECT_URI"
COMP_AUTH_EXTRA_ENV_NAMES = (
    COMP_DISCORD_CLIENT_ID_ENV_NAME,
    COMP_DISCORD_CLIENT_SECRET_ENV_NAME,
    COMP_DISCORD_REDIRECT_URI_ENV_NAME,
    COMP_AUTH_SESSION_SECRET_ENV_NAME,
)
COMP_AUTH_SECRET_ENV_NAMES = (ADMIN_ENV_NAME, *COMP_AUTH_EXTRA_ENV_NAMES)
LOCAL_SECRET_FILE_DEFAULT = Path("k8s/secrets.dev.enc.yaml")
SOPS_AGE_RECIPIENT = (
    "age16yxsawhpecdrhas2q3z246q3tjq8889m552lqhjcgf8jnt7naszqqgz8vt"
)

FASTAPI_EXTRA_SECRET_ENV_SNIPPET = """\
            {{- range $env := .Values.fastapi.extraSecretEnv }}
            - name: {{ $env.name }}
              valueFrom:
                secretKeyRef:
                  name: {{ $env.secretName }}
                  key: {{ $env.key }}
            {{- end }}
"""

CONFIG_ARGO_APP_CONTENT = """\
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: splattop-prod-comp-auth-secrets
  namespace: argocd
  finalizers:
    - resources-finalizer.argocd.argoproj.io
spec:
  project: splattop
  source:
    repoURL: https://github.com/cesaregarza/SplatTopConfig
    targetRevision: main
    path: secrets/splattop-prod-comp-auth
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated: null
    syncOptions:
      - CreateNamespace=false
      - ApplyOutOfSyncOnly=true
  revisionHistoryLimit: 5
"""

CONFIG_SECRET_KUSTOMIZATION_CONTENT = """\
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: default
generators:
  - ksops.yaml
"""

CONFIG_SECRET_KSOPS_CONTENT = """\
apiVersion: viaduct.ai/v1
kind: ksops
metadata:
  name: splattop-prod-comp-auth-secrets
files:
  - comp-auth-secrets.enc.yaml
"""

CONFIG_SECRET_README_CONTENT = """\
# SplatTop competition auth secrets (prod)

Secrets are encrypted with SOPS/age. Edit with:

```
SOPS_AGE_KEY_FILE=keys/age-private.txt sops secrets/splattop-prod-comp-auth/comp-auth-secrets.enc.yaml
```

Expected keys (stringData):
- `COMP_AUTH_ADMIN_DISCORD_IDS`
- `COMP_DISCORD_CLIENT_ID`
- `COMP_DISCORD_CLIENT_SECRET`
- `COMP_DISCORD_REDIRECT_URI`
- `COMP_AUTH_SESSION_SECRET`
"""


def _fail(message: str) -> None:
    raise SystemExit(message)


def _write_text_if_changed(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = path.read_text() if path.exists() else None
    if existing == content:
        return False
    path.write_text(content)
    return True


def _validate_discord_id(value: str) -> str:
    discord_id = str(value).strip()
    if not discord_id or not discord_id.isdigit():
        raise ValueError(f"Invalid Discord ID: {value!r}")
    return discord_id


def _run_sops_decrypt(path: Path) -> str:
    try:
        result = subprocess.run(
            ["sops", "--decrypt", str(path)],
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ),
        )
    except FileNotFoundError as exc:
        raise ValueError("sops binary is required to decrypt secrets") from exc

    return result.stdout


def read_secret_string_data(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    payload = YAML_RW.load(_run_sops_decrypt(path))
    if not isinstance(payload, dict):
        raise ValueError(f"Unexpected YAML document in {path}")

    string_data = payload.get("stringData")
    if not isinstance(string_data, dict):
        return {}

    return {
        str(key): str(value)
        for key, value in string_data.items()
        if value is not None
    }


def parse_admin_entries_text(text: str) -> list[dict[str, str]]:
    chunks: list[str] = []
    for line in text.replace("\r", "\n").splitlines():
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            continue
        for part in stripped_line.split(";"):
            stripped_part = part.strip()
            if stripped_part:
                chunks.append(stripped_part)

    entries_by_id: dict[str, dict[str, str]] = {}
    order: list[str] = []
    for chunk in chunks:
        discord_raw, sep, note_raw = chunk.partition("|")
        discord_id = _validate_discord_id(discord_raw)
        note = note_raw.strip() if sep else ""
        entry = {"discord_id": discord_id}
        if note:
            entry["note"] = note
        if discord_id not in entries_by_id:
            order.append(discord_id)
        entries_by_id[discord_id] = entry

    return [entries_by_id[discord_id] for discord_id in order]


def build_admin_env_value(entries: list[dict[str, str]]) -> str:
    return ",".join(entry["discord_id"] for entry in entries)


def _fastapi_extra_secret_env_block() -> str:
    lines = ["  extraSecretEnv:"]
    for env_name in COMP_AUTH_SECRET_ENV_NAMES:
        lines.extend(
            [
                f"    - name: {env_name}",
                f"      secretName: {ADMIN_SECRET_NAME}",
                f"      key: {env_name}",
            ]
        )
    return "\n".join(lines) + "\n"


def ensure_fastapi_values_file(path: Path) -> bool:
    content = path.read_text()
    desired_block = _fastapi_extra_secret_env_block()
    existing_block_anchor = "  extraSecretEnv:\n"
    section_marker = "\n# React frontend configuration\n"

    if existing_block_anchor in content:
        start = content.index(existing_block_anchor)
        try:
            end = content.index(section_marker, start)
        except ValueError as exc:
            raise ValueError(
                f"Unable to find React section marker in {path}"
            ) from exc
        updated = content[:start] + desired_block + content[end:]
    else:
        anchors = (
            "  readinessProbe: {}\n",
            "  livenessProbe: {}\n",
            "  resources: {}\n",
            "  env: {}\n",
        )
        for anchor in anchors:
            if anchor in content:
                insert_at = content.index(anchor) + len(anchor)
                break
        else:
            raise ValueError(
                f"Unable to find fastapi insertion anchor in {path}"
            )
        updated = content[:insert_at] + desired_block + content[insert_at:]

    if updated == content:
        return False

    path.write_text(updated)
    return True


def ensure_fastapi_template_file(path: Path) -> bool:
    content = path.read_text()
    if FASTAPI_EXTRA_SECRET_ENV_SNIPPET in content:
        return False

    anchor = "            {{- range $key, $value := .Values.fastapi.env }}\n"
    if anchor not in content:
        raise ValueError(f"Unable to find fastapi env anchor in {path}")

    updated = content.replace(
        anchor,
        FASTAPI_EXTRA_SECRET_ENV_SNIPPET + anchor,
        1,
    )
    path.write_text(updated)
    return True


def ensure_config_sops_file(path: Path) -> bool:
    if path.exists():
        with path.open("r") as handle:
            document = YAML_RW.load(handle)
    else:
        document = CommentedMap()
        document["creation_rules"] = []

    if not isinstance(document, dict):
        raise ValueError(f"Unexpected YAML document in {path}")

    creation_rules = document.get("creation_rules")
    if not isinstance(creation_rules, list):
        creation_rules = []
        document["creation_rules"] = creation_rules

    desired = CommentedMap()
    desired["path_regex"] = CONFIG_SECRET_PATH_REGEX
    desired["encrypted_regex"] = "^(data|stringData)$"
    desired["age"] = SOPS_AGE_RECIPIENT

    for item in creation_rules:
        if isinstance(item, dict) and item.get("path_regex") == (
            CONFIG_SECRET_PATH_REGEX
        ):
            if dict(item) == dict(desired):
                return False
            item.clear()
            item.update(desired)
            with path.open("w") as handle:
                YAML_RW.dump(document, handle)
            return True

    creation_rules.append(desired)
    with path.open("w") as handle:
        YAML_RW.dump(document, handle)
    return True


def _secret_plaintext_yaml(secret_values: dict[str, str]) -> str:
    payload = CommentedMap()
    payload["apiVersion"] = "v1"
    payload["kind"] = "Secret"
    metadata = CommentedMap()
    metadata["name"] = ADMIN_SECRET_NAME
    payload["metadata"] = metadata
    payload["type"] = "Opaque"
    string_data = CommentedMap()
    for key in COMP_AUTH_SECRET_ENV_NAMES:
        value = secret_values.get(key)
        if value:
            string_data[key] = value
    payload["stringData"] = string_data

    with tempfile.NamedTemporaryFile("w+", suffix=".yaml", delete=False) as fh:
        YAML_RW.dump(payload, fh)
        tmp_path = Path(fh.name)
    content = tmp_path.read_text()
    tmp_path.unlink(missing_ok=True)
    return content


def write_source_secret_file(
    output_path: Path,
    entries: list[dict[str, str]],
) -> None:
    existing_values = read_secret_string_data(output_path)
    secret_values = {
        key: value
        for key, value in existing_values.items()
        if key in COMP_AUTH_EXTRA_ENV_NAMES and value
    }
    secret_values[ADMIN_ENV_NAME] = build_admin_env_value(entries)
    plaintext = _secret_plaintext_yaml(secret_values)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
        fh.write(plaintext)
        plaintext_path = Path(fh.name)

    try:
        subprocess.run(
            [
                "sops",
                "--config",
                "/dev/null",
                "--encrypt",
                "--input-type",
                "yaml",
                "--output-type",
                "yaml",
                "--age",
                SOPS_AGE_RECIPIENT,
                "--encrypted-regex",
                "^(data|stringData)$",
                "--output",
                str(output_path),
                str(plaintext_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ),
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "sops binary is required to write the source secret"
        ) from exc
    finally:
        plaintext_path.unlink(missing_ok=True)


def merge_local_comp_auth_into_source_secret(
    output_path: Path,
    local_secret_file: Path,
    *,
    redirect_uri: str | None = None,
    session_secret: str | None = None,
) -> None:
    existing_values = read_secret_string_data(output_path)
    local_values = read_secret_string_data(local_secret_file)

    secret_values = {
        key: value
        for key, value in existing_values.items()
        if key in COMP_AUTH_SECRET_ENV_NAMES and value
    }

    for key in COMP_AUTH_EXTRA_ENV_NAMES:
        value = local_values.get(key)
        if value:
            secret_values[key] = value

    if redirect_uri is not None:
        secret_values[COMP_DISCORD_REDIRECT_URI_ENV_NAME] = (
            redirect_uri.strip()
        )
    if session_secret is not None:
        secret_values[COMP_AUTH_SESSION_SECRET_ENV_NAME] = (
            session_secret.strip()
        )

    missing = [
        key
        for key in COMP_AUTH_EXTRA_ENV_NAMES
        if not str(secret_values.get(key) or "").strip()
    ]
    if missing:
        raise ValueError(
            "Missing competition auth secret values for: "
            + ", ".join(sorted(missing))
        )

    plaintext = _secret_plaintext_yaml(secret_values)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
        fh.write(plaintext)
        plaintext_path = Path(fh.name)

    try:
        subprocess.run(
            [
                "sops",
                "--config",
                "/dev/null",
                "--encrypt",
                "--input-type",
                "yaml",
                "--output-type",
                "yaml",
                "--age",
                SOPS_AGE_RECIPIENT,
                "--encrypted-regex",
                "^(data|stringData)$",
                "--output",
                str(output_path),
                str(plaintext_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=dict(os.environ),
        )
    except FileNotFoundError as exc:
        raise ValueError(
            "sops binary is required to write the source secret"
        ) from exc
    finally:
        plaintext_path.unlink(missing_ok=True)


def sync_config_repo(
    source_secret_file: Path,
    config_repo_dir: Path,
) -> list[Path]:
    changed_paths: list[Path] = []
    if not source_secret_file.exists():
        raise ValueError(f"Missing source secret file: {source_secret_file}")

    values_file = config_repo_dir / CONFIG_VALUES_FILE
    template_file = config_repo_dir / CONFIG_FASTAPI_TEMPLATE_FILE
    sops_file = config_repo_dir / CONFIG_SOPS_FILE
    argo_app_file = config_repo_dir / CONFIG_ARGO_APP_FILE
    secret_file = config_repo_dir / CONFIG_SECRET_FILE
    secret_kustomization = config_repo_dir / CONFIG_SECRET_KUSTOMIZATION_FILE
    secret_ksops = config_repo_dir / CONFIG_SECRET_KSOPS_FILE
    secret_readme = config_repo_dir / CONFIG_SECRET_README_FILE

    if ensure_fastapi_values_file(values_file):
        changed_paths.append(values_file)
    if ensure_fastapi_template_file(template_file):
        changed_paths.append(template_file)
    if ensure_config_sops_file(sops_file):
        changed_paths.append(sops_file)
    if _write_text_if_changed(argo_app_file, CONFIG_ARGO_APP_CONTENT):
        changed_paths.append(argo_app_file)
    if _write_text_if_changed(
        secret_kustomization, CONFIG_SECRET_KUSTOMIZATION_CONTENT
    ):
        changed_paths.append(secret_kustomization)
    if _write_text_if_changed(secret_ksops, CONFIG_SECRET_KSOPS_CONTENT):
        changed_paths.append(secret_ksops)
    if _write_text_if_changed(secret_readme, CONFIG_SECRET_README_CONTENT):
        changed_paths.append(secret_readme)
    if _write_text_if_changed(secret_file, source_secret_file.read_text()):
        changed_paths.append(secret_file)

    return changed_paths


def _read_entries_argument(args: argparse.Namespace) -> str:
    if args.entries:
        return args.entries
    if args.entries_env:
        return os.getenv(args.entries_env, "")
    if args.entries_file:
        return Path(args.entries_file).read_text()
    return ""


def _resolve_entries(args: argparse.Namespace) -> list[dict[str, str]]:
    entries_text = _read_entries_argument(args)
    if not entries_text.strip():
        raise ValueError("At least one admin entry is required")
    return parse_admin_entries_text(entries_text)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage competition admin allowlist automation."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_source_secret = subparsers.add_parser(
        "write-source-secret",
        help="Write the encrypted source secret stored in this repo.",
    )
    write_source_secret.add_argument(
        "--output-file",
        default=str(SOURCE_SECRET_FILE_DEFAULT),
        help="Path to the encrypted source secret file.",
    )
    source_group = write_source_secret.add_mutually_exclusive_group(
        required=True
    )
    source_group.add_argument(
        "--entries",
        help="Full admin list as 'discord_id|note;discord_id|note'.",
    )
    source_group.add_argument(
        "--entries-env",
        help="Environment variable containing the full admin list.",
    )
    source_group.add_argument(
        "--entries-file",
        help="File containing the full admin list.",
    )

    sync_config = subparsers.add_parser(
        "sync-config",
        help="Patch SplatTopConfig using the encrypted source secret.",
    )
    sync_config.add_argument(
        "--source-secret-file",
        default=str(SOURCE_SECRET_FILE_DEFAULT),
        help="Path to the encrypted source secret file.",
    )
    sync_config.add_argument(
        "--config-repo-dir",
        required=True,
        help="Checked-out SplatTopConfig repository path.",
    )

    merge_local = subparsers.add_parser(
        "merge-local-secrets",
        help="Merge local competition auth values into the encrypted source secret.",
    )
    merge_local.add_argument(
        "--output-file",
        default=str(SOURCE_SECRET_FILE_DEFAULT),
        help="Path to the encrypted source secret file.",
    )
    merge_local.add_argument(
        "--local-secret-file",
        default=str(LOCAL_SECRET_FILE_DEFAULT),
        help="Encrypted local secret file containing competition auth values.",
    )
    merge_local.add_argument(
        "--redirect-uri",
        help="Override COMP_DISCORD_REDIRECT_URI in the source secret.",
    )
    session_group = merge_local.add_mutually_exclusive_group()
    session_group.add_argument(
        "--session-secret",
        help="Override COMP_AUTH_SESSION_SECRET in the source secret.",
    )
    session_group.add_argument(
        "--generate-session-secret",
        action="store_true",
        help="Generate a fresh COMP_AUTH_SESSION_SECRET for the source secret.",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "write-source-secret":
            entries = _resolve_entries(args)
            write_source_secret_file(Path(args.output_file), entries)
            return 0

        if args.command == "sync-config":
            changed = sync_config_repo(
                Path(args.source_secret_file),
                Path(args.config_repo_dir),
            )
            for path in changed:
                print(path)
            return 0

        if args.command == "merge-local-secrets":
            session_secret = args.session_secret
            if args.generate_session_secret:
                session_secret = secrets.token_urlsafe(48)
            merge_local_comp_auth_into_source_secret(
                Path(args.output_file),
                Path(args.local_secret_file),
                redirect_uri=args.redirect_uri,
                session_secret=session_secret,
            )
            return 0
    except ValueError as exc:
        _fail(str(exc))

    _fail(f"Unsupported command: {args.command}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
