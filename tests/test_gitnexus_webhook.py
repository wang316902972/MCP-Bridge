import importlib
import json
import subprocess
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import mcp_bridge.config as bridge_config
from mcp_bridge.config.final import GitNexusConfig, GitNexusWebhookConfig
from mcp_bridge.gitnexus_webhook.router import router

webhook_router = importlib.import_module("mcp_bridge.gitnexus_webhook.router")

pytestmark = pytest.mark.unit


def _client(monkeypatch, webhook_config: GitNexusWebhookConfig) -> TestClient:
    test_config = SimpleNamespace(gitnexus=GitNexusConfig(webhook=webhook_config))
    monkeypatch.setattr(bridge_config, "config", test_config)
    monkeypatch.setattr(webhook_router.bridge_config, "config", test_config)

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _push_payload(branch: str = "master") -> dict:
    return {
        "ref": f"refs/heads/{branch}",
        "project": {
            "name": "api",
            "path_with_namespace": "bigdata/api",
            "git_ssh_url": "ssh://git@git.nd.com.cn:10022/bigdata/api.git",
        },
        "repository": {
            "name": "api",
            "url": "ssh://git@git.nd.com.cn:10022/bigdata/api.git",
        },
    }


def test_gitlab_push_hook_queues_gitnexus_analyze_for_master(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    calls: list[str] = []

    monkeypatch.setattr(
        webhook_router,
        "run_gitnexus_analyze",
        lambda path, settings: calls.append(str(path)),
    )

    client = _client(
        monkeypatch,
        GitNexusWebhookConfig(
            enabled=True,
            secret_token="secret",
            repo_paths={"bigdata/api": str(repo_path)},
        ),
    )

    response = client.post(
        "/gitnexus/webhooks/gitlab",
        json=_push_payload("master"),
        headers={"X-Gitlab-Token": "secret", "X-Gitlab-Event": "Push Hook"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "status": "queued",
        "branch": "master",
        "repo_path": str(repo_path.resolve()),
    }
    assert calls == [str(repo_path.resolve())]


def test_gitlab_push_hook_ignores_non_main_branch(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    calls: list[str] = []
    monkeypatch.setattr(
        webhook_router,
        "run_gitnexus_analyze",
        lambda path, settings: calls.append(str(path)),
    )

    client = _client(
        monkeypatch,
        GitNexusWebhookConfig(
            enabled=True,
            secret_token="secret",
            repo_paths={"bigdata/api": str(repo_path)},
        ),
    )

    response = client.post(
        "/gitnexus/webhooks/gitlab",
        json=_push_payload("feature/test"),
        headers={"X-Gitlab-Token": "secret", "X-Gitlab-Event": "Push Hook"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ignored",
        "branch": "feature/test",
        "reason": "branch_not_allowed",
    }
    assert calls == []


def test_gitlab_push_hook_rejects_invalid_secret(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    calls: list[str] = []
    monkeypatch.setattr(
        webhook_router,
        "run_gitnexus_analyze",
        lambda path, settings: calls.append(str(path)),
    )

    client = _client(
        monkeypatch,
        GitNexusWebhookConfig(
            enabled=True,
            secret_token="secret",
            repo_paths={"bigdata/api": str(repo_path)},
        ),
    )

    response = client.post(
        "/gitnexus/webhooks/gitlab",
        json=_push_payload("master"),
        headers={"X-Gitlab-Token": "wrong", "X-Gitlab-Event": "Push Hook"},
    )

    assert response.status_code == 401
    assert calls == []


def test_gitlab_push_hook_accepts_project_specific_secret(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    calls: list[str] = []
    monkeypatch.setattr(
        webhook_router,
        "run_gitnexus_analyze",
        lambda path, settings: calls.append(str(path)),
    )

    client = _client(
        monkeypatch,
        GitNexusWebhookConfig(
            enabled=True,
            project_tokens={"bigdata/api": "api-secret"},
            repo_paths={"bigdata/api": str(repo_path)},
        ),
    )

    response = client.post(
        "/gitnexus/webhooks/gitlab",
        json=_push_payload("master"),
        headers={"X-Gitlab-Token": "api-secret", "X-Gitlab-Event": "Push Hook"},
    )

    assert response.status_code == 202
    assert calls == [str(repo_path.resolve())]


def test_gitlab_push_hook_rejects_token_for_different_project(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    calls: list[str] = []
    monkeypatch.setattr(
        webhook_router,
        "run_gitnexus_analyze",
        lambda path, settings: calls.append(str(path)),
    )

    client = _client(
        monkeypatch,
        GitNexusWebhookConfig(
            enabled=True,
            project_tokens={
                "bigdata/api": "api-secret",
                "bigdata/other": "other-secret",
            },
            repo_paths={"bigdata/api": str(repo_path)},
        ),
    )

    response = client.post(
        "/gitnexus/webhooks/gitlab",
        json=_push_payload("master"),
        headers={"X-Gitlab-Token": "other-secret", "X-Gitlab-Event": "Push Hook"},
    )

    assert response.status_code == 401
    assert calls == []


def test_gitlab_push_hook_resolves_repo_from_gitnexus_registry(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(
            [
                {
                    "name": "api",
                    "path": str(repo_path),
                    "remoteUrl": "ssh://git@git.nd.com.cn:10022/bigdata/api",
                }
            ]
        ),
        encoding="utf-8",
    )
    calls: list[str] = []
    monkeypatch.setattr(
        webhook_router,
        "run_gitnexus_analyze",
        lambda path, settings: calls.append(str(path)),
    )

    client = _client(
        monkeypatch,
        GitNexusWebhookConfig(
            enabled=True,
            secret_token="secret",
            registry_file=str(registry_file),
        ),
    )

    response = client.post(
        "/gitnexus/webhooks/gitlab",
        json=_push_payload("main"),
        headers={"X-Gitlab-Token": "secret", "X-Gitlab-Event": "Push Hook"},
    )

    assert response.status_code == 202
    assert response.json()["repo_path"] == str(repo_path.resolve())
    assert calls == [str(repo_path.resolve())]


def test_analyze_task_updates_local_repo_before_indexing(monkeypatch, tmp_path):
    repo_path = tmp_path / "api"
    repo_path.mkdir()
    commands: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        commands.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(webhook_router.subprocess, "run", fake_run)

    webhook_router.run_gitnexus_analyze(
        repo_path,
        GitNexusWebhookConfig(
            command="gitnexus",
            extra_args=["--skip-agents-md"],
            sync_before_analyze=True,
        ),
    )

    assert commands == [
        ["git", "-C", str(repo_path), "fetch", "--prune"],
        ["git", "-C", str(repo_path), "pull", "--ff-only"],
        ["gitnexus", "analyze", "--skip-agents-md", str(repo_path)],
    ]
