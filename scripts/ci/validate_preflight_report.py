#!/usr/bin/env python3
"""Independent closed-value validator for the ADR-003 Recovery-2 report."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import unicodedata
from datetime import datetime
from pathlib import PurePosixPath
from typing import Mapping

REPORT_PATH = "/tmp/podcast-clips-recovery-2-preflight/report-v2.json"
SCHEMA_ID = "podcast-clips/story1-recovery-preflight/v2"
LOCK_SCHEMA = "podcast-clips/story1-recovery-2-control-lock/v1"
PARENT = "c43ddf3409ea0ea793982f07926ce1e1a6925c82"
ADR_SHA256 = "0645e92eecb4336ef03cd712c7845cc460bc264594564cd60611b5b8b9c6357d"
TEST_ADDENDUM_SHA256 = "1366f23b876662a20107523d028b0324e114a866250839f353ccbab01ca53511"
UP_COMMIT = "1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7"
UP_TREE = "ebfc8990216aded7ad4ab6d393fa6e0131a69fee"
ARCHIVE = "99c9d77996595d6d75ed170240d5849ce381931f6d5e726d12e198ff15dae8a2"
UP_DIGEST = "b05cc9e64c2285efab776bf05a6de65ba8396e0de8a6329c00a9a23ba3997aee"
OVERLAY_DIGEST = "9f0be1ba6ee4c873ae761a8b8a77367ee6cad2c32f8d9f021d485939e634a655"
KNOWN_DIGEST = "43cb57b8bf61100948512e0e66fd5c55380cc25ff2020ef81aa820b44386e732"
PROPS = "19058640ca22d0398085d67d6a49e68892894a80"
DIST = "20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78"
JAR = "81a82aaea5abcc8ff68b3dfcb58b3c3c429378efd98e7433460610fecd7ae45f"
EVIDENCE = "37593a4217bd442d407d8b0f63d7fcb2fa10f069"
LEGACY_WORKFLOW_ID = 315057380
LEGACY_WORKFLOW_PATH = ".github/workflows/preflight-recovery.yml"
LEGACY_WORKFLOW_NAME = "Story 1 recovery preflight"
LEGACY_WORKFLOW_BLOB = "06008a439355c8be6d657a92c244e03ba27afdaa"
LEGACY_RUN_ID = 29575201182
LEGACY_CONTROL = "fc0ed383c0f4e1cf527f88d0ac3033973a379a4e"
WORKFLOW_PATH = ".github/workflows/preflight-recovery-2.yml"
WORKFLOW_NAME = "Recovery 2 — one-shot trusted preflight"
ALLOWED_ENV = {"HOME", "LANG", "LC_ALL", "PATH"}
REFS = {
    "refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562152128": "1152cfce3b78cbc9cfb64a69bb0eb68551273371",
    "refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562160851": "c58e2607c57925486b856416e1b3f9044673e2be",
}
RUNS = {
    "29562294514": {"id": 29562294514, "conclusion": "failure", "event": "workflow_dispatch", "head_sha": "c58e2607c57925486b856416e1b3f9044673e2be", "workflow_id": 314940238, "workflow_path": ".github/workflows/validate-candidate.yml", "workflow_name": "Validate exact candidate"},
    "29562814924": {"id": 29562814924, "conclusion": "failure", "event": "workflow_dispatch", "head_sha": "2a29aaf00b6c9414f627b1e4a24a8536412c47d7", "workflow_id": 314940238, "workflow_path": ".github/workflows/validate-candidate.yml", "workflow_name": "Validate exact candidate"},
    "29563023789": {"id": 29563023789, "conclusion": "cancelled", "event": "workflow_dispatch", "head_sha": "2a29aaf00b6c9414f627b1e4a24a8536412c47d7", "workflow_id": 314940238, "workflow_path": ".github/workflows/validate-candidate.yml", "workflow_name": "Validate exact candidate"},
}
PR = {"number": 1, "state": "closed", "merged": False, "head_sha": "c58e2607c57925486b856416e1b3f9044673e2be"}
TUPLES = {"regular-100755-to-100644", "regular-100644-to-100755", "regular-to-symlink", "symlink-to-regular", "regular-to-gitlink", "gitlink-to-regular", "symlink-target-identity", "gitlink-commit-identity", "symlink-to-gitlink", "gitlink-to-symlink"}
PROPERTIES = {"androidx-omission", "androidx-value", "nontransitive-omission", "nontransitive-value", "jvmargs-omission", "jvmargs-value"}
SCOPE = {"EF", "EXCLUDE", "NOOP", "TASK", "SHADOW", "THRESHOLD"}
VALID = {f"VALID-{index:02d}" for index in range(1, 11)}
HOSTILE = {f"HOST-{index:02d}" for index in range(1, 37)}
DECLARE = {f"DECLARE-{index:02d}" for index in range(1, 11)}
RECURSION = {"CYCLE-01", "CYCLE-02", "CYCLE-03", "CYCLE-04", "DEPTH-01", "DEPTH-02", "DEPTH-03", "DEPTH-04", "DEPTH-05"}
TOP = {"schema", "status", "authorization", "historical_evidence", "control", "correction_diff", "workflow", "identity", "overlay", "projection", "gradle_inputs", "resolver", "negative_tests", "invariants", "isolation", "workflow_inventory", "observations"}
ALLOWED_CHANGES = {
    "scripts/ci/recovery_preflight.py": ("modify", "resolver-report"),
    "scripts/ci/test_recovery_preflight.py": ("modify", "focused-tests"),
    "scripts/ci/validate_preflight_report.py": ("modify", "schema-validator"),
    "config/recovery-preflight-report-v2.schema.json": ("add", "schema"),
    "config/recovery-2-control.lock.json": ("add", "lock"),
    WORKFLOW_PATH: ("add", "one-shot-workflow"),
    "UPSTREAM.md": ("modify", "report-metadata"),
    "docs/base-selection-report.md": ("modify", "report-metadata"),
}

class Reject(RuntimeError):
    pass

def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def unique_json(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise Reject(f"duplicate JSON key: {key}")
        value[key] = item
    return value

def read_regular_json(path: str, maximum: int) -> object:
    flags = os.O_RDONLY | (os.O_NOFOLLOW if hasattr(os, "O_NOFOLLOW") else 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size <= 0 or info.st_size > maximum:
            raise Reject(f"JSON control metadata invalid: {path}")
        with os.fdopen(descriptor, "r", encoding="utf-8") as handle:
            descriptor = -1
            return json.load(handle, object_pairs_hook=unique_json, parse_constant=lambda value: (_ for _ in ()).throw(Reject(f"non-finite JSON: {value}")))
    finally:
        if descriptor >= 0:
            os.close(descriptor)

def clean_path(value: object) -> str:
    if not isinstance(value, str) or not value or value.startswith(("/", chr(92))) or chr(0) in value or chr(92) in value:
        raise Reject("invalid tuple path")
    if unicodedata.normalize("NFC", value) != value:
        raise Reject("non-NFC tuple path")
    parts = value.split("/")
    if any(item in {"", ".", ".."} for item in parts) or str(PurePosixPath(value)) != value:
        raise Reject("non-canonical tuple path")
    return value

def tuple_row(row: object, regular_only: bool = False) -> dict[str, str]:
    if not isinstance(row, Mapping) or set(row) != {"path", "type", "mode", "identity"}:
        raise Reject("tuple schema changed")
    path = clean_path(row["path"])
    kind, mode, identity = row["type"], row["mode"], row["identity"]
    valid = {"blob": {"100644", "100755", "120000"}, "tree": {"040000"}, "commit": {"160000"}}
    if kind not in valid or mode not in valid[kind] or not isinstance(identity, str) or not re.fullmatch(r"[0-9a-f]{40}", identity):
        raise Reject("tuple value invalid")
    if regular_only and (kind != "blob" or mode not in {"100644", "100755"}):
        raise Reject("tuple is not a regular blob")
    return {"path": path, "type": kind, "mode": mode, "identity": identity}

def rows_digest(rows: object) -> str:
    if not isinstance(rows, list):
        raise Reject("tuple manifest is not a list")
    values = {}
    folded = set()
    for raw in rows:
        row = tuple_row(raw)
        key = unicodedata.normalize("NFC", row["path"]).casefold()
        if row["path"] in values or key in folded:
            raise Reject("tuple manifest duplicate/collision")
        values[row["path"]] = row
        folded.add(key)
    return digest([values[path] for path in sorted(values)])

def all_outcome(value: object, names: set[str], outcome: str) -> bool:
    return isinstance(value, Mapping) and set(value) == names and all(item == outcome for item in value.values())

def validate_environment(env: Mapping[str, str] | None = None) -> None:
    current = os.environ if env is None else env
    if set(current) - ALLOWED_ENV:
        raise Reject("non-allowlisted validator channel")

def expected_allowed_changes() -> list[dict[str, str]]:
    return [
        {"path": path, "operation": operation, "category": category}
        for path, (operation, category) in sorted(ALLOWED_CHANGES.items())
    ]

def validate_lock(lock: object) -> Mapping[str, object]:
    keys = {"schema", "authorization", "parent", "allowed_changes", "controls", "workflow", "report", "resolver", "historical", "gates"}
    if not isinstance(lock, Mapping) or set(lock) != keys or lock.get("schema") != LOCK_SCHEMA:
        raise Reject("control lock envelope changed")
    authorization = {"active_goal_continuation": True, "adr_sha256": ADR_SHA256, "test_addendum_sha256": TEST_ADDENDUM_SHA256, "supersedes": "G009 no-corrected-preflight constraint only"}
    if lock.get("authorization") != authorization or lock.get("parent") != PARENT:
        raise Reject("authorization/parent lock changed")
    if lock.get("allowed_changes") != expected_allowed_changes():
        raise Reject("allowed correction paths/categories changed")
    controls = lock.get("controls")
    required_controls = {
        "scripts/ci/recovery_preflight.py",
        "scripts/ci/test_recovery_preflight.py",
        "scripts/ci/validate_preflight_report.py",
        "config/recovery-preflight-report-v2.schema.json",
    }
    if not isinstance(controls, Mapping) or set(controls) != required_controls or not all(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value) for value in controls.values()):
        raise Reject("control blob lock changed")
    if lock.get("workflow") != {"path": WORKFLOW_PATH, "name": WORKFLOW_NAME, "trigger": "workflow_dispatch", "permissions": {}}:
        raise Reject("workflow lock changed")
    if lock.get("report") != {"schema": SCHEMA_ID, "path": REPORT_PATH}:
        raise Reject("report lock changed")
    if lock.get("resolver") != {"version": 2, "semantics": "declaring-relative-posix-lexical", "max_include_depth": 32, "realpath": False, "follow_symlinks": False, "fetch_gitlinks": False}:
        raise Reject("resolver lock changed")
    historical = {
        "g001": "failed-attempt-1", "g009": "failed-attempt-1", "g002": "pending",
        "evidence_commit": EVIDENCE, "terminal_report_commit": PARENT,
        "legacy_workflow_id": LEGACY_WORKFLOW_ID, "legacy_run_id": LEGACY_RUN_ID,
        "legacy_control_sha": LEGACY_CONTROL, "legacy_artifacts": 0,
    }
    if lock.get("historical") != historical:
        raise Reject("historical lock changed")
    gates = {"upstream_commit": UP_COMMIT, "upstream_tree": UP_TREE, "archive_sha256": ARCHIVE, "candidate_max_dispatches": 3, "required_consecutive_successes": 2, "critical_gap_budget": 0, "max_minutes": 25, "run2_failure_stop": True}
    if lock.get("gates") != gates:
        raise Reject("candidate gate lock changed")
    return lock

def validate_schema(schema: object) -> None:
    if not isinstance(schema, Mapping) or schema.get("$id") != SCHEMA_ID or schema.get("type") != "object" or schema.get("additionalProperties") is not False:
        raise Reject("report schema identity/closure changed")
    if set(schema.get("required", [])) != TOP or len(schema.get("required", [])) != len(TOP):
        raise Reject("report schema required fields changed")
    constants = {
        "schema": SCHEMA_ID, "report_path": REPORT_PATH, "parent": PARENT,
        "legacy_workflow_id": LEGACY_WORKFLOW_ID, "legacy_run_id": LEGACY_RUN_ID,
        "legacy_control_sha": LEGACY_CONTROL, "workflow_path": WORKFLOW_PATH,
        "workflow_name": WORKFLOW_NAME, "max_include_depth": 32,
        "candidate_max_dispatches": 3, "required_consecutive_successes": 2,
        "critical_gap_budget": 0,
    }
    if schema.get("x-constants") != constants:
        raise Reject("report schema constants changed")
    if schema.get("x-matrix-cardinality") != {"resolver_valid": 10, "resolver_hostile": 36, "declaring": 10, "recursion": 9}:
        raise Reject("report schema matrix cardinality changed")

def validate_projection(report: Mapping[str, object]) -> None:
    overlay = report.get("overlay")
    if not isinstance(overlay, Mapping) or set(overlay) != {"entries", "policy_digest"} or overlay.get("policy_digest") != OVERLAY_DIGEST or digest(overlay.get("entries")) != OVERLAY_DIGEST:
        raise Reject("frozen candidate overlay changed")
    if not isinstance(overlay.get("entries"), list) or len(overlay["entries"]) != 11:
        raise Reject("overlay entry count changed")
    projection = report.get("projection")
    keys = {"upstream_tuple_count", "upstream_tree_count", "upstream_digest", "projected_tuple_count", "projected_digest", "origin_projection", "projected_manifest"}
    if not isinstance(projection, Mapping) or set(projection) != keys or projection.get("upstream_tuple_count") != 2028 or projection.get("upstream_tree_count") != 745:
        raise Reject("projection schema/count changed")
    mappings, manifest = projection["origin_projection"], projection["projected_manifest"]
    if not isinstance(mappings, list) or len(mappings) != 2028 or not isinstance(manifest, list):
        raise Reject("projection manifests incomplete")
    projected = {}
    for raw in manifest:
        row = tuple_row(raw)
        if row["path"] in projected:
            raise Reject("projected tuple duplicate")
        projected[row["path"]] = row
    origins = []
    for mapping in mappings:
        if not isinstance(mapping, Mapping) or set(mapping) != {"origin", "projected"}:
            raise Reject("origin projection schema changed")
        origin, result = tuple_row(mapping["origin"]), tuple_row(mapping["projected"])
        origins.append(origin)
        if projected.get(result["path"]) != result:
            raise Reject("origin result is not bound to projected manifest")
    if rows_digest(origins) != UP_DIGEST or projection.get("upstream_digest") != UP_DIGEST:
        raise Reject("pinned upstream tuple digest changed")
    observed = rows_digest(manifest)
    if projection.get("projected_tuple_count") != len(manifest) or projection.get("projected_digest") != observed:
        raise Reject("projected tuple digest/count changed")

def validate_gradle(report: Mapping[str, object]) -> None:
    gradle = report.get("gradle_inputs")
    keys = {"known_inventory", "dynamic_inputs", "gradle_properties_blob", "wrapper_distribution_sha256", "wrapper_jar_sha256"}
    if not isinstance(gradle, Mapping) or set(gradle) != keys or digest(gradle.get("known_inventory")) != KNOWN_DIGEST:
        raise Reject("known Gradle inventory changed")
    if (gradle.get("gradle_properties_blob"), gradle.get("wrapper_distribution_sha256"), gradle.get("wrapper_jar_sha256")) != (PROPS, DIST, JAR):
        raise Reject("Gradle property/wrapper constants changed")
    dynamic = gradle.get("dynamic_inputs")
    if not isinstance(dynamic, Mapping) or set(dynamic) != {"literal_environment_and_properties", "static_root_config", "unresolved"} or dynamic.get("unresolved") != []:
        raise Reject("dynamic input report changed/unresolved")
    if any(set(row) != {"path", "api", "name"} for row in dynamic["literal_environment_and_properties"]):
        raise Reject("literal environment/property row changed")
    if any(set(row) != {"declared_by", "path"} for row in dynamic["static_root_config"]):
        raise Reject("legacy static include row changed")

def validate_resolver(report: Mapping[str, object]) -> None:
    resolver = report.get("resolver")
    keys = {"version", "semantics", "max_include_depth", "realpath", "follow_symlinks", "fetch_gitlinks", "edges", "max_observed_depth", "cycles", "unresolved"}
    exact = {"version": 2, "semantics": "declaring-relative-posix-lexical", "max_include_depth": 32, "realpath": False, "follow_symlinks": False, "fetch_gitlinks": False}
    if not isinstance(resolver, Mapping) or set(resolver) != keys or any(resolver.get(key) != value for key, value in exact.items()):
        raise Reject("resolver contract changed")
    if resolver.get("cycles") != [] or resolver.get("unresolved") != [] or type(resolver.get("max_observed_depth")) is not int or not 0 <= resolver["max_observed_depth"] <= 32:
        raise Reject("resolver result unresolved/outside depth")
    edges = resolver.get("edges")
    if not isinstance(edges, list):
        raise Reject("resolver edge list missing")
    for edge in edges:
        if not isinstance(edge, Mapping) or set(edge) != {"declaring", "literal", "normalized_target", "target", "depth"}:
            raise Reject("resolver edge schema changed")
        declaring = tuple_row(edge["declaring"], True)
        target = tuple_row(edge["target"], True)
        if edge.get("normalized_target") != target["path"] or type(edge.get("literal")) is not str or type(edge.get("depth")) is not int or not 1 <= edge["depth"] <= 32:
            raise Reject("resolver edge values changed")
        if declaring["path"] == target["path"] and edge["literal"] != target["path"].rsplit("/", 1)[-1]:
            raise Reject("resolver self edge/cycle escaped")

def validate_negative(report: Mapping[str, object]) -> None:
    negative = report.get("negative_tests")
    keys = {"tuples", "gradle_properties", "recovery_scope", "resolver_valid", "resolver_hostile", "declaring", "recursion"}
    if not isinstance(negative, Mapping) or set(negative) != keys:
        raise Reject("negative-test envelope changed")
    if not all_outcome(negative["tuples"], TUPLES, "rejected") or not all_outcome(negative["gradle_properties"], PROPERTIES, "rejected") or not all_outcome(negative["recovery_scope"], SCOPE, "rejected"):
        raise Reject("prior negative-test outcome changed")
    if not all_outcome(negative["resolver_valid"], VALID, "accepted") or not all_outcome(negative["resolver_hostile"], HOSTILE, "rejected") or not all_outcome(negative["declaring"], DECLARE, "rejected"):
        raise Reject("Recovery-2 resolver matrix changed")
    recursion_expected = {name: ("accepted" if name in {"CYCLE-04", "DEPTH-01", "DEPTH-02"} else "rejected") for name in RECURSION}
    if negative["recursion"] != recursion_expected:
        raise Reject("Recovery-2 recursion matrix changed")

def canonical_run(row: object) -> dict[str, object]:
    keys = {"id", "run_attempt", "event", "head_sha", "status", "conclusion", "path", "name"}
    if not isinstance(row, Mapping) or set(row) != keys:
        raise Reject("workflow run tuple schema changed")
    if type(row["id"]) is not int or type(row["run_attempt"]) is not int or not isinstance(row["head_sha"], str):
        raise Reject("workflow run tuple type changed")
    return dict(row)

def validate_inventory(value: object, control_sha: str, workflow_id: int, run_id: int) -> list[dict[str, object]]:
    keys = {"pages", "page_counts", "total_count", "inventory_sha256", "runs"}
    if not isinstance(value, Mapping) or set(value) != keys or value.get("total_count") != 1:
        raise Reject("Recovery-2 workflow inventory is not exactly one")
    if type(value.get("pages")) is not int or value["pages"] < 1 or not isinstance(value.get("page_counts"), list) or len(value["page_counts"]) != value["pages"] or sum(value["page_counts"]) != 1:
        raise Reject("Recovery-2 pagination evidence incomplete")
    runs = [canonical_run(row) for row in value.get("runs", [])]
    if len(runs) != 1 or digest(runs) != value.get("inventory_sha256"):
        raise Reject("Recovery-2 inventory digest changed")
    run = runs[0]
    exact = {"id": run_id, "run_attempt": 1, "event": "workflow_dispatch", "head_sha": control_sha, "path": WORKFLOW_PATH, "name": WORKFLOW_NAME}
    if any(run.get(key) != expected for key, expected in exact.items()) or run.get("status") not in {"queued", "in_progress"} or run.get("conclusion") is not None:
        raise Reject("Recovery-2 sole run identity changed")
    if workflow_id <= LEGACY_WORKFLOW_ID:
        raise Reject("Recovery-2 workflow ID is not distinct")
    return runs

def timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise Reject("observation timestamp is not RFC3339 UTC")
    try:
        return datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        raise Reject("observation timestamp malformed") from None

def validate_report(report: object, control_sha: str, lock: Mapping[str, object]) -> None:
    if not isinstance(report, Mapping) or set(report) != TOP or report.get("schema") != SCHEMA_ID or report.get("status") != "pass":
        raise Reject("Recovery-2 report envelope changed")
    if report.get("authorization") != lock["authorization"]:
        raise Reject("Recovery-2 report authorization changed")
    identity = {"upstream_commit": UP_COMMIT, "upstream_tree": UP_TREE, "upstream_archive_sha256": ARCHIVE, "control_sha": control_sha}
    if report.get("identity") != identity:
        raise Reject("Recovery-2 upstream/control identity changed")
    control = report.get("control")
    control_keys = {"control_sha", "first_parent", "allowed_changes", "control_blobs", "report_schema", "report_path", "resolver_version", "max_include_depth"}
    expected_control = {"control_sha": control_sha, "first_parent": PARENT, "allowed_changes": lock["allowed_changes"], "control_blobs": lock["controls"], "report_schema": SCHEMA_ID, "report_path": REPORT_PATH, "resolver_version": 2, "max_include_depth": 32}
    if not isinstance(control, Mapping) or set(control) != control_keys or control != expected_control:
        raise Reject("Recovery-2 control values changed")
    changes = report.get("correction_diff")
    if not isinstance(changes, list) or not changes:
        raise Reject("Recovery-2 correction diff missing")
    changed = set()
    allowed = {row["path"]: row for row in lock["allowed_changes"]}
    for row in changes:
        if not isinstance(row, Mapping) or set(row) != {"path", "operation", "category", "old", "new"}:
            raise Reject("Recovery-2 correction row schema changed")
        path = row["path"]
        if path in changed or path not in allowed or {key: row[key] for key in ("path", "operation", "category")} != allowed[path]:
            raise Reject("Recovery-2 correction row escaped category lock")
        changed.add(path)
        new = tuple_row(row["new"])
        if new["path"] != path or new["type"] != "blob" or new["mode"] != "100644":
            raise Reject("Recovery-2 changed tuple is not ordinary blob")
        if row["operation"] == "add":
            if row["old"] is not None:
                raise Reject("Recovery-2 addition has old tuple")
        else:
            old = tuple_row(row["old"])
            if old["path"] != path or old["type"] != "blob" or old["mode"] != "100644":
                raise Reject("Recovery-2 modification old tuple invalid")
    if WORKFLOW_PATH not in changed or not changed <= set(ALLOWED_CHANGES):
        raise Reject("Recovery-2 correction path set invalid")
    history = report.get("historical_evidence")
    history_keys = {"evidence_commit", "terminal_report_commit", "goals", "legacy_preflight", "candidate_refs", "pull_request", "validation_runs", "immutable"}
    if not isinstance(history, Mapping) or set(history) != history_keys or history.get("evidence_commit") != EVIDENCE or history.get("terminal_report_commit") != PARENT or history.get("goals") != {"G001": "failed-attempt-1", "G009": "failed-attempt-1", "G002": "pending"} or history.get("candidate_refs") != REFS or history.get("pull_request") != PR or history.get("validation_runs") != RUNS or history.get("immutable") is not True:
        raise Reject("immutable G001/G009/candidate history changed")
    legacy = history.get("legacy_preflight")
    legacy_keys = {"workflow_id", "workflow_path", "workflow_name", "workflow_blob", "run_id", "run_attempt", "event", "head_sha", "status", "conclusion", "artifacts", "error", "inventory"}
    legacy_exact = {"workflow_id": LEGACY_WORKFLOW_ID, "workflow_path": LEGACY_WORKFLOW_PATH, "workflow_name": LEGACY_WORKFLOW_NAME, "workflow_blob": LEGACY_WORKFLOW_BLOB, "run_id": LEGACY_RUN_ID, "run_attempt": 1, "event": "workflow_dispatch", "head_sha": LEGACY_CONTROL, "status": "completed", "conclusion": "failure", "artifacts": 0, "error": "Reject: non-canonical Git path: '../common.gradle'"}
    if not isinstance(legacy, Mapping) or set(legacy) != legacy_keys or any(legacy.get(key) != value for key, value in legacy_exact.items()) or legacy.get("inventory", {}).get("total_count") != 1:
        raise Reject("legacy preflight evidence changed")
    validate_projection(report)
    validate_gradle(report)
    validate_resolver(report)
    validate_negative(report)
    isolation = {"sanitized_environment": True, "candidate_workspace": "absent", "credential_channels": "absent", "runtime_cache_result_channels": "absent-from-parser", "constant_report_path": REPORT_PATH, "checkout": False, "android_gradle_execution": False, "realpath": False, "follow_symlinks": False, "fetch_gitlinks": False}
    if report.get("isolation") != isolation:
        raise Reject("Recovery-2 isolation values changed")
    invariants = report.get("invariants")
    expected_invariants = {
        "legacy_preflight": {"workflow_id": LEGACY_WORKFLOW_ID, "run_id": LEGACY_RUN_ID, "run_attempt": 1, "head_sha": LEGACY_CONTROL, "conclusion": "failure", "artifacts": 0},
        "recovery2_preflight": {"maximum_runs": 1, "prior_runs": 0, "required_run_attempt": 1, "candidate_created": False},
        "candidate_gate": lock["gates"],
    }
    if invariants != expected_invariants:
        raise Reject("Recovery-2 invariants changed")
    workflow = report.get("workflow")
    workflow_keys = {"id", "name", "path", "state", "blob", "control_sha", "run_id", "run_attempt", "event", "status"}
    if not isinstance(workflow, Mapping) or set(workflow) != workflow_keys or workflow.get("name") != WORKFLOW_NAME or workflow.get("path") != WORKFLOW_PATH or workflow.get("state") != "active" or workflow.get("control_sha") != control_sha or workflow.get("run_attempt") != 1 or workflow.get("event") != "workflow_dispatch" or workflow.get("status") not in {"queued", "in_progress"} or not isinstance(workflow.get("id"), int) or not isinstance(workflow.get("run_id"), int) or not isinstance(workflow.get("blob"), str) or not re.fullmatch(r"[0-9a-f]{40}", workflow["blob"]):
        raise Reject("Recovery-2 workflow identity changed")
    final_runs = validate_inventory(report.get("workflow_inventory"), control_sha, workflow["id"], workflow["run_id"])
    observations = report.get("observations")
    if not isinstance(observations, list) or len(observations) != 2 or [row.get("stage") for row in observations if isinstance(row, Mapping)] != ["in_workflow_start", "in_workflow_end"]:
        raise Reject("Recovery-2 observation stages changed")
    observed_times = []
    for observation in observations:
        if not isinstance(observation, Mapping) or set(observation) != {"stage", "observed_at", "pages", "page_counts", "total_count", "inventory_sha256", "runs"}:
            raise Reject("Recovery-2 observation schema changed")
        observed_times.append(timestamp(observation["observed_at"]))
        validate_inventory({key: observation[key] for key in ("pages", "page_counts", "total_count", "inventory_sha256", "runs")}, control_sha, workflow["id"], workflow["run_id"])
    if not observed_times[0] < observed_times[1]:
        raise Reject("Recovery-2 observations are not monotonically ordered")
    if final_runs[0]["id"] != workflow["run_id"]:
        raise Reject("Recovery-2 workflow/inventory run mismatch")

def self_test(lock: Mapping[str, object], schema: Mapping[str, object]) -> None:
    validate_environment({"PATH": "/usr/bin", "HOME": "/tmp/empty", "LANG": "C.UTF-8"})
    try:
        validate_environment({"PATH": "/usr/bin", "GITHUB_TOKEN": "secret"})
    except Reject:
        pass
    else:
        raise AssertionError("credential channel accepted")
    validate_lock(lock)
    validate_schema(schema)
    rows = [{"path": "a", "type": "blob", "mode": "100644", "identity": "1" * 40}, {"path": "d", "type": "tree", "mode": "040000", "identity": "2" * 40}]
    baseline = rows_digest(rows)
    changed = json.loads(json.dumps(rows)); changed[0]["identity"] = "3" * 40
    if baseline == rows_digest(changed):
        raise AssertionError("tuple digest failed to bind identity")
    for attacked in (rows + [dict(rows[0])], [{"path": "../x", "type": "blob", "mode": "100644", "identity": "1" * 40}]):
        try:
            rows_digest(attacked)
        except Reject:
            pass
        else:
            raise AssertionError("hostile tuple manifest accepted")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", required=True)
    parser.add_argument("--lock", required=True)
    parser.add_argument("--report", default=REPORT_PATH)
    parser.add_argument("--expected-control-sha")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    validate_environment()
    lock = validate_lock(read_regular_json(args.lock, 1024 * 1024))
    schema = read_regular_json(args.schema, 1024 * 1024)
    validate_schema(schema)
    if args.self_test:
        self_test(lock, schema)
        return
    if args.report != REPORT_PATH or not args.expected_control_sha or not re.fullmatch(r"[0-9a-f]{40}", args.expected_control_sha):
        raise Reject("constant report path/exact control SHA required")
    report = read_regular_json(REPORT_PATH, 32 * 1024 * 1024)
    validate_report(report, args.expected_control_sha, lock)

if __name__ == "__main__":
    main()
