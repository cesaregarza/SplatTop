import logging
import os
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, Iterable, Optional

import orjson
from kubernetes import client, config
from kubernetes.client import ApiException
from kubernetes.config.config_exception import ConfigException

logger = logging.getLogger(__name__)


class DeploymentConfigError(RuntimeError):
    """Raised when deployment target configuration is invalid."""


class KubernetesRolloutError(RuntimeError):
    """Raised when Kubernetes rollout operations fail."""


@dataclass(frozen=True)
class DeploymentTarget:
    slug: str
    namespace: str
    deployment: str
    container: Optional[str]
    image_prefixes: tuple[str, ...]

    def validate_image(self, image: Optional[str]) -> None:
        if not image or not self.image_prefixes:
            return
        if any(image.startswith(prefix) for prefix in self.image_prefixes):
            return
        allowed = ", ".join(self.image_prefixes)
        raise DeploymentConfigError(
            f"Image '{image}' is not allowed for target '{self.slug}'. "
            f"Expected to start with one of: {allowed}"
        )


def _normalize_prefixes(prefixes: Iterable[str]) -> tuple[str, ...]:
    cleaned = []
    for prefix in prefixes:
        if not isinstance(prefix, str):
            continue
        cleaned_prefix = prefix.strip()
        if cleaned_prefix:
            cleaned.append(cleaned_prefix)
    return tuple(cleaned)


def _coerce_target(slug: str, data: dict) -> DeploymentTarget:
    namespace = data.get("namespace")
    deployment = data.get("deployment")
    container = data.get("container")
    prefixes = data.get("image_prefixes") or data.get("imagePrefixes") or ()

    if not namespace or not deployment:
        raise DeploymentConfigError(
            f"Deployment target '{slug}' must define 'namespace' and "
            "'deployment'."
        )

    if container is not None and not isinstance(container, str):
        raise DeploymentConfigError(
            f"Deployment target '{slug}' has invalid 'container'; expected "
            "a string or null."
        )

    if isinstance(prefixes, str):
        prefixes = [prefixes]
    elif not isinstance(prefixes, Iterable):
        prefixes = []

    image_prefixes = _normalize_prefixes(prefixes)

    return DeploymentTarget(
        slug=slug,
        namespace=str(namespace),
        deployment=str(deployment),
        container=str(container) if container else None,
        image_prefixes=image_prefixes,
    )


@lru_cache(maxsize=1)
def deployment_targets() -> Dict[str, DeploymentTarget]:
    raw = os.getenv("DEPLOYMENT_WEBHOOK_TARGETS", "")
    if not raw.strip():
        return {}
    try:
        data = orjson.loads(raw)
    except orjson.JSONDecodeError as exc:
        msg = "DEPLOYMENT_WEBHOOK_TARGETS must be valid JSON"
        logger.error("%s: %s", msg, exc)
        raise DeploymentConfigError(msg) from exc

    if not isinstance(data, dict):
        raise DeploymentConfigError(
            "DEPLOYMENT_WEBHOOK_TARGETS must be a JSON object mapping slugs "
            "to deployment definitions."
        )

    targets: Dict[str, DeploymentTarget] = {}
    for slug, spec in data.items():
        if not isinstance(slug, str):
            raise DeploymentConfigError(
                "Deployment target keys must be strings."
            )
        if not isinstance(spec, dict):
            raise DeploymentConfigError(
                f"Deployment target '{slug}' must be a JSON object."
            )
        target = _coerce_target(slug, spec)
        targets[slug] = target
    return targets


def reload_deployment_targets() -> None:
    deployment_targets.cache_clear()


_apps_v1_api: Optional[client.AppsV1Api] = None


def _build_annotation_prefix() -> str:
    prefix = os.getenv("DEPLOY_WEBHOOK_ANNOTATION_PREFIX", "").strip()
    if not prefix:
        prefix = "deploy-webhook.splat-top.dev/"
    if not prefix.endswith("/"):
        prefix = f"{prefix}/"
    return prefix


def _ensure_apps_v1() -> client.AppsV1Api:
    global _apps_v1_api
    if _apps_v1_api is not None:
        return _apps_v1_api

    try:
        config.load_incluster_config()
    except ConfigException:
        try:
            config.load_kube_config()
        except ConfigException as exc:
            msg = "Unable to load Kubernetes configuration"
            logger.error(msg)
            raise KubernetesRolloutError(msg) from exc

    _apps_v1_api = client.AppsV1Api()
    return _apps_v1_api


def _annotation_key(name: str) -> str:
    prefix = _build_annotation_prefix()
    if "/" in name:
        return name
    return f"{prefix}{name}"


def trigger_rolling_update(
    target: DeploymentTarget,
    image: Optional[str],
    commit_sha: Optional[str],
    extra_annotations: Optional[Dict[str, str]] = None,
) -> Dict[str, str]:
    target.validate_image(image)

    ts_ms = int(time.time() * 1000)
    annotations: Dict[str, str] = {
        _annotation_key("last-triggered"): str(ts_ms)
    }
    if image:
        annotations[_annotation_key("image")] = image
    if commit_sha:
        annotations[_annotation_key("commit-sha")] = commit_sha

    for key, value in (extra_annotations or {}).items():
        if value is None:
            continue
        annotations[_annotation_key(str(key))] = str(value)

    patch_body: Dict[str, dict] = {
        "spec": {
            "template": {
                "metadata": {"annotations": annotations},
            }
        }
    }

    if image:
        container_name = target.container or target.deployment
        patch_body["spec"]["template"]["spec"] = {
            "containers": [
                {
                    "name": container_name,
                    "image": image,
                }
            ]
        }

    apps_v1 = _ensure_apps_v1()

    try:
        apps_v1.patch_namespaced_deployment(
            name=target.deployment,
            namespace=target.namespace,
            body=patch_body,
        )
    except ApiException as exc:
        logger.error(
            "Failed to trigger rollout for %s/%s: %s",
            target.namespace,
            target.deployment,
            exc,
        )
        raise KubernetesRolloutError(
            f"Rollout failed for {target.namespace}/{target.deployment}"
        ) from exc

    return annotations


def reset_kubernetes_client() -> None:
    global _apps_v1_api
    _apps_v1_api = None
