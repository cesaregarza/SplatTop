import glob
from typing import Any, Iterator

from ruamel.yaml import YAML


def _iter_deployments() -> Iterator[tuple[str, dict[str, Any]]]:
    yaml = YAML(typ="safe")
    for filepath in glob.glob("k8s/**/deployment*.yaml", recursive=True):
        with open(filepath, "r", encoding="utf-8") as handle:
            docs = yaml.load_all(handle)
            for doc in docs:
                if isinstance(doc, dict) and doc.get("kind") == "Deployment":
                    yield filepath, doc


def test_all_deployments_have_security_context() -> None:
    for filepath, manifest in _iter_deployments():
        spec = manifest["spec"]["template"]["spec"]
        assert (
            "securityContext" in spec
        ), f"{filepath} missing pod securityContext"

        for container in spec.get("containers", []):
            assert (
                "securityContext" in container
            ), f"{filepath} container {container.get('name')} missing securityContext"


def test_deployments_run_as_non_root() -> None:
    for filepath, manifest in _iter_deployments():
        sec_ctx = manifest["spec"]["template"]["spec"].get(
            "securityContext", {}
        )
        assert (
            sec_ctx.get("runAsNonRoot") is True
        ), f"{filepath} should set runAsNonRoot: true"


def test_deployments_have_resource_limits() -> None:
    for filepath, manifest in _iter_deployments():
        containers = manifest["spec"]["template"]["spec"].get(
            "containers", []
        )
        for container in containers:
            resources = container.get("resources") or {}
            assert (
                "limits" in resources
            ), f"{filepath} container {container.get('name')} missing resource limits"


def test_deployments_have_health_checks() -> None:
    for filepath, manifest in _iter_deployments():
        containers = manifest["spec"]["template"]["spec"].get(
            "containers", []
        )
        for container in containers:
            assert (
                "readinessProbe" in container
            ), f"{filepath} container {container.get('name')} missing readinessProbe"
            assert (
                "livenessProbe" in container
            ), f"{filepath} container {container.get('name')} missing livenessProbe"
