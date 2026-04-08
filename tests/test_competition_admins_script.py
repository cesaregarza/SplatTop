from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess


def _load_competition_admins_module():
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "competition_admins.py"
    )
    spec = importlib.util.spec_from_file_location(
        "competition_admins_script", script_path
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_admin_entries_text_deduplicates_and_keeps_notes():
    module = _load_competition_admins_module()

    entries = module.parse_admin_entries_text(
        "123|Owner;456|Ops\n123|Updated owner\n# comment\n789"
    )

    assert entries == [
        {"discord_id": "123", "note": "Updated owner"},
        {"discord_id": "456", "note": "Ops"},
        {"discord_id": "789"},
    ]


def test_write_source_secret_file_invokes_sops(tmp_path, monkeypatch):
    module = _load_competition_admins_module()
    output_file = tmp_path / "comp-auth-secrets.enc.yaml"
    captured = {}

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("encrypted-source")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    module.write_source_secret_file(
        output_file,
        [{"discord_id": "123", "note": "Owner"}],
    )

    assert output_file.read_text() == "encrypted-source"
    assert captured["cmd"][0] == "sops"
    assert "--config" in captured["cmd"]
    assert "/dev/null" in captured["cmd"]
    assert "--age" in captured["cmd"]
    assert module.SOPS_AGE_RECIPIENT in captured["cmd"]


def test_write_source_secret_file_preserves_existing_oauth_values(
    tmp_path, monkeypatch
):
    module = _load_competition_admins_module()
    output_file = tmp_path / "comp-auth-secrets.enc.yaml"
    output_file.write_text("existing-encrypted")
    captured = {}

    monkeypatch.setattr(
        module,
        "read_secret_string_data",
        lambda path: {
            module.COMP_DISCORD_CLIENT_ID_ENV_NAME: "cid",
            module.COMP_DISCORD_CLIENT_SECRET_ENV_NAME: "csecret",
            module.COMP_DISCORD_REDIRECT_URI_ENV_NAME: "https://comp.splat.top/api/comp-auth/discord/callback",
            module.COMP_AUTH_SESSION_SECRET_ENV_NAME: "session-secret",
        },
    )

    def _fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        plaintext_path = Path(cmd[-1])
        captured["plaintext"] = plaintext_path.read_text()
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text("encrypted-source")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    module.write_source_secret_file(output_file, [{"discord_id": "123"}])
    payload = module.YAML_RW.load(captured["plaintext"])
    string_data = payload["stringData"]

    assert output_file.read_text() == "encrypted-source"
    assert string_data[module.ADMIN_ENV_NAME] == "123"
    assert string_data[module.COMP_DISCORD_CLIENT_ID_ENV_NAME] == "cid"
    assert (
        string_data[module.COMP_AUTH_SESSION_SECRET_ENV_NAME]
        == "session-secret"
    )


def test_sync_config_repo_adds_secret_wiring(tmp_path):
    module = _load_competition_admins_module()

    source_secret_file = tmp_path / "comp-auth-secrets.enc.yaml"
    source_secret_file.write_text("encrypted-secret-content")

    config_repo_dir = tmp_path / "config-repo"
    values_file = config_repo_dir / module.CONFIG_VALUES_FILE
    template_file = config_repo_dir / module.CONFIG_FASTAPI_TEMPLATE_FILE
    values_file.parent.mkdir(parents=True, exist_ok=True)
    template_file.parent.mkdir(parents=True, exist_ok=True)
    values_file.write_text(
        "fastapi:\n"
        "  enabled: true\n"
        "  secretKeys:\n"
        "    - DB_HOST\n"
        "  env: {}\n"
    )
    template_file.write_text(
        "{{- if .Values.fastapi.enabled }}\n"
        "          env:\n"
        "            {{- range $key := .Values.fastapi.secretKeys }}\n"
        "            - name: {{ $key }}\n"
        "            {{- end }}\n"
        "            {{- range $key, $value := .Values.fastapi.env }}\n"
        "            - name: {{ $key }}\n"
        "              value: {{ $value | quote }}\n"
        "            {{- end }}\n"
        "{{- end }}\n"
    )

    changed = module.sync_config_repo(source_secret_file, config_repo_dir)

    assert module.CONFIG_ARGO_APP_FILE in [
        p.relative_to(config_repo_dir) for p in changed
    ]

    values_content = values_file.read_text()
    assert "extraSecretEnv" in values_content
    for env_name in module.COMP_AUTH_SECRET_ENV_NAMES:
        assert env_name in values_content
    assert module.ADMIN_SECRET_NAME in values_content

    sops_content = (config_repo_dir / module.CONFIG_SOPS_FILE).read_text()
    assert module.CONFIG_SECRET_PATH_REGEX in sops_content
    assert module.SOPS_AGE_RECIPIENT in sops_content

    template_content = template_file.read_text()
    assert ".Values.fastapi.extraSecretEnv" in template_content

    secret_content = (config_repo_dir / module.CONFIG_SECRET_FILE).read_text()
    assert secret_content == "encrypted-secret-content"


def test_merge_local_comp_auth_into_source_secret_overrides_redirect_and_session(
    tmp_path, monkeypatch
):
    module = _load_competition_admins_module()
    output_file = tmp_path / "comp-auth-secrets.enc.yaml"
    local_secret_file = tmp_path / "secrets.dev.enc.yaml"
    output_file.write_text("existing-encrypted")
    local_secret_file.write_text("local-encrypted")
    captured = {}

    def _fake_read(path):
        if path == output_file:
            return {module.ADMIN_ENV_NAME: "111"}
        if path == local_secret_file:
            return {
                module.COMP_DISCORD_CLIENT_ID_ENV_NAME: "cid",
                module.COMP_DISCORD_CLIENT_SECRET_ENV_NAME: "csecret",
                module.COMP_DISCORD_REDIRECT_URI_ENV_NAME: "http://comp.localhost:8080/api/comp-auth/discord/callback",
                module.COMP_AUTH_SESSION_SECRET_ENV_NAME: "dev-session-secret",
            }
        raise AssertionError(f"unexpected path: {path}")

    def _fake_run(cmd, **kwargs):
        plaintext_path = Path(cmd[-1])
        captured["plaintext"] = plaintext_path.read_text()
        output_path = Path(cmd[cmd.index("--output") + 1])
        output_path.write_text("encrypted-source")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(module, "read_secret_string_data", _fake_read)
    monkeypatch.setattr(module.subprocess, "run", _fake_run)

    module.merge_local_comp_auth_into_source_secret(
        output_file,
        local_secret_file,
        redirect_uri="https://comp.splat.top/api/comp-auth/discord/callback",
        session_secret="fresh-session-secret",
    )
    payload = module.YAML_RW.load(captured["plaintext"])
    string_data = payload["stringData"]

    assert output_file.read_text() == "encrypted-source"
    assert string_data[module.ADMIN_ENV_NAME] == "111"
    assert string_data[module.COMP_DISCORD_CLIENT_ID_ENV_NAME] == "cid"
    assert (
        string_data[module.COMP_DISCORD_REDIRECT_URI_ENV_NAME]
        == "https://comp.splat.top/api/comp-auth/discord/callback"
    )
    assert (
        string_data[module.COMP_AUTH_SESSION_SECRET_ENV_NAME]
        == "fresh-session-secret"
    )
