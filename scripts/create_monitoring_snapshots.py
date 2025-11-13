#!/usr/bin/env python3
"""
Create VolumeSnapshots for the monitoring PVCs (Grafana + Prometheus).

Usage:
    python scripts/create_monitoring_snapshots.py
        [--namespace monitoring]
        [--snapshot-class do-block-storage]
        [--pvc splattop-prod-grafana-storage]
        [--pvc prometheus-data-splattop-prod-prometheus-0]

By default this emits two VolumeSnapshot manifests (one per PVC) with a
UTC timestamp suffix, then pipes them to `kubectl apply -f -`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from textwrap import dedent

DEFAULT_PVCS = [
    "splattop-prod-grafana-storage",
    "prometheus-data-splattop-prod-prometheus-0",
]


def build_manifest(
    *,
    pvcs: list[str],
    namespace: str,
    snapshot_class: str,
    timestamp: str,
) -> str:
    docs: list[str] = []
    for pvc in pvcs:
        docs.append(
            dedent(
                f"""
                apiVersion: snapshot.storage.k8s.io/v1
                kind: VolumeSnapshot
                metadata:
                  name: {pvc}-snapshot-{timestamp}
                  namespace: {namespace}
                  labels:
                    app.kubernetes.io/managed-by: monitoring-snapshot-script
                    app.kubernetes.io/component: monitoring-pvc-snapshot
                    splattop.dev/pvc-name: {pvc}
                spec:
                  volumeSnapshotClassName: {snapshot_class}
                  source:
                    persistentVolumeClaimName: {pvc}
                """
            ).strip()
        )
    return "\n---\n".join(docs) + "\n"


def run_kubectl_apply(manifest: str) -> None:
    subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=manifest,
        text=True,
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--namespace",
        default="monitoring",
        help="Namespace that contains the PVCs (default: monitoring)",
    )
    parser.add_argument(
        "--snapshot-class",
        default="do-block-storage",
        help="VolumeSnapshotClass to use (default: do-block-storage)",
    )
    parser.add_argument(
        "--pvc",
        dest="pvcs",
        action="append",
        help=(
            "PVC name to snapshot (can be repeated). "
            "Defaults to Grafana + Prometheus PVCs."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the manifest instead of applying it.",
    )
    parser.add_argument(
        "--timestamp",
        help="Override the timestamp suffix (UTC, format YYYYMMDD-HHMMSS).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pvcs = args.pvcs or DEFAULT_PVCS
    timestamp = args.timestamp or dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    manifest = build_manifest(
        pvcs=pvcs,
        namespace=args.namespace,
        snapshot_class=args.snapshot_class,
        timestamp=timestamp,
    )
    if args.dry_run:
        print(manifest.strip())
        return
    run_kubectl_apply(manifest)
    print(f"Created snapshots for {', '.join(pvcs)} at {timestamp}")


if __name__ == "__main__":
    main()
