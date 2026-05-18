import json
import secrets
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from loguru import logger

import mcp_bridge.config as bridge_config
from mcp_bridge.config.final import GitNexusWebhookConfig
from mcp_bridge.openapi_tags import Tag

router = APIRouter(prefix="/gitnexus", tags=[Tag.gitnexus])


def _branch_from_ref(ref: str | None) -> str:
    prefix = "refs/heads/"
    if not ref:
        return ""
    if ref.startswith(prefix):
        return ref[len(prefix) :]
    return ref


def _normalize_remote_url(url: str | None) -> str:
    if not url:
        return ""

    normalized = url.strip()
    if normalized.endswith(".git"):
        normalized = normalized[:-4]

    parsed = urlparse(normalized)
    if parsed.scheme and parsed.netloc:
        path = parsed.path.strip("/")
        return f"{parsed.netloc}/{path}".lower()

    if ":" in normalized and "@" in normalized:
        _, tail = normalized.split("@", 1)
        host, path = tail.split(":", 1)
        return f"{host}/{path.strip('/')}".lower()

    return normalized.strip("/").lower()


def _payload_keys(payload: dict) -> set[str]:
    project = payload.get("project") or {}
    repository = payload.get("repository") or {}
    keys = {
        project.get("path_with_namespace"),
        project.get("name"),
        repository.get("name"),
    }

    for url in (
        project.get("git_ssh_url"),
        project.get("git_http_url"),
        project.get("web_url"),
        repository.get("url"),
        repository.get("git_ssh_url"),
        repository.get("git_http_url"),
    ):
        normalized = _normalize_remote_url(url)
        if normalized:
            keys.add(normalized)
        if url:
            keys.add(str(url).removesuffix(".git"))

    return {str(key).strip() for key in keys if key}


def _resolve_from_registry(keys: set[str], registry_file: str) -> Path | None:
    path = Path(registry_file).expanduser()
    if not path.exists():
        return None

    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning(f"Unable to read GitNexus registry {path}: {exc}")
        return None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_keys = {
            str(entry.get("name") or "").strip(),
            _normalize_remote_url(entry.get("remoteUrl")),
            str(entry.get("remoteUrl") or "").removesuffix(".git"),
        }
        if keys.intersection({key for key in entry_keys if key}):
            repo_path = entry.get("path")
            if repo_path:
                return Path(repo_path).expanduser().resolve()

    return None


def resolve_repo_path(payload: dict, settings: GitNexusWebhookConfig) -> Path | None:
    keys = _payload_keys(payload)
    configured_paths = settings.repo_paths

    for key in keys:
        configured_path = configured_paths.get(key)
        if configured_path:
            return Path(configured_path).expanduser().resolve()

    normalized_configured_paths = {
        _normalize_remote_url(key): value for key, value in configured_paths.items()
    }
    for key in keys:
        configured_path = normalized_configured_paths.get(_normalize_remote_url(key))
        if configured_path:
            return Path(configured_path).expanduser().resolve()

    return _resolve_from_registry(keys, settings.registry_file)


def run_gitnexus_analyze(repo_path: Path, settings: GitNexusWebhookConfig) -> None:
    if settings.sync_before_analyze:
        for cmd in (
            ["git", "-C", str(repo_path), "fetch", "--prune"],
            ["git", "-C", str(repo_path), "pull", "--ff-only"],
        ):
            try:
                subprocess.run(
                    cmd,
                    check=True,
                    timeout=settings.timeout_seconds,
                    text=True,
                    capture_output=True,
                )
            except subprocess.CalledProcessError as exc:
                logger.error(
                    "Git sync failed for {}: {}{}",
                    repo_path,
                    exc.stderr or "",
                    exc.stdout or "",
                )
                return
            except subprocess.TimeoutExpired:
                logger.error(f"Git sync timed out for {repo_path}")
                return

    cmd = [
        settings.command,
        "analyze",
        *settings.extra_args,
        str(repo_path),
    ]
    logger.info(f"Running GitNexus analyze for {repo_path}")
    try:
        subprocess.run(
            cmd,
            check=True,
            timeout=settings.timeout_seconds,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.error(
            "GitNexus analyze failed for {}: {}{}",
            repo_path,
            exc.stderr or "",
            exc.stdout or "",
        )
    except subprocess.TimeoutExpired:
        logger.error(f"GitNexus analyze timed out for {repo_path}")


@router.post("/webhooks/gitlab", status_code=status.HTTP_202_ACCEPTED)
async def gitlab_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    response: Response,
    x_gitlab_token: str | None = Header(default=None),
    x_gitlab_event: str | None = Header(default=None),
):
    settings = bridge_config.config.gitnexus.webhook
    if not settings.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitNexus webhook is disabled",
        )

    if not settings.secret_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitNexus webhook secret token is not configured",
        )

    if not x_gitlab_token or not secrets.compare_digest(
        settings.secret_token, x_gitlab_token
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitLab webhook token",
        )

    if x_gitlab_event and x_gitlab_event != "Push Hook":
        response.status_code = status.HTTP_200_OK
        return {"status": "ignored", "reason": "event_not_supported"}

    payload = await request.json()
    branch = _branch_from_ref(payload.get("ref"))
    if branch not in settings.branches:
        response.status_code = status.HTTP_200_OK
        return {
            "status": "ignored",
            "branch": branch,
            "reason": "branch_not_allowed",
        }

    repo_path = resolve_repo_path(payload, settings)
    if repo_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository is not mapped to a local GitNexus path",
        )

    background_tasks.add_task(run_gitnexus_analyze, repo_path, settings)
    return {"status": "queued", "branch": branch, "repo_path": str(repo_path)}
