#!/usr/bin/env python3
"""Deterministic stdlib-only hostile fixtures for recovery_preflight."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from dataclasses import asdict

import recovery_preflight as p

COMMON = b'''android {\n defaultConfig { resValue "string", "app_name", "AntennaPod" }\n buildTypes { debug { resValue "string", "app_name", "AntennaPod Debug" } }\n}\n'''

def base_leaves():
    values = {path: p.GitEntry(path, kind, mode, identity)
              for path, (kind, mode, identity, _target) in p.QUARANTINE.items()}
    required = set().union(*(set(v) for v in p.KNOWN_INPUTS.values()))
    for path in required:
        data = COMMON if path == "common.gradle" else f"// {path}\n".encode()
        values.setdefault(path, p.GitEntry(path, "blob", "100644", p.git_blob_sha(data)))
    values["gradle.properties"] = p.GitEntry("gradle.properties", "blob", "100644", p.GRADLE_PROPERTIES_BLOB)
    values["common.gradle"] = p.GitEntry("common.gradle", "blob", "100644", p.git_blob_sha(COMMON))
    return values

def full_inventory():
    values = base_leaves()
    for index in range(p.UPSTREAM_TREE_ENTRY_COUNT):
        directory = f"fixture-tree-{index:04d}"
        values[directory] = p.GitEntry(directory, "tree", "040000", f"{index + 1:040x}")
        child = f"{directory}/item.txt"
        values[child] = p.GitEntry(child, "blob", "100644", p.git_blob_sha(child.encode()))
    index = 0
    while len(values) < p.PINNED_TUPLE_COUNT:
        path = f"fixture-leaf-{index:04d}.txt"; index += 1
        values[path] = p.GitEntry(path, "blob", "100644", p.git_blob_sha(path.encode()))
    assert len(values) == p.PINNED_TUPLE_COUNT
    assert sum(x.type == "tree" for x in values.values()) == p.UPSTREAM_TREE_ENTRY_COUNT
    return values

def overlay():
    return {path: p.GitEntry(path, rule.type, rule.mode, rule.identity)
            for path, rule in p.CANDIDATE_OVERLAY_POLICY.items()}

def known_contents():
    result = {}
    for path in set().union(*(set(v) for v in p.KNOWN_INPUTS.values())):
        if path == "common.gradle": result[path] = COMMON
        elif path == "build.gradle": result[path] = b'def ci = System.getenv("CI")\napply from: "common.gradle"\n'
        else: result[path] = f"// {path}\n".encode()
    return result

def tree_payload(values):
    rows = [{"path": e.path, "type": e.type, "mode": e.mode, "sha": e.identity} for e in values.values()]
    body = json.dumps([asdict(values[x]) for x in sorted(values)], sort_keys=True, separators=(",", ":"))
    return ({"sha": p.UPSTREAM_TREE, "truncated": False, "tree": rows}, len(values), hashlib.sha256(body.encode()).hexdigest())

class FullTupleProjection(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.values = full_inventory()

    def test_all_2028_tuples_and_745_trees_project_once(self):
        projected, mapping = p.project_tree(self.values, overlay(), COMMON)
        self.assertEqual(len(mapping), 2028)
        self.assertEqual(sum(row["origin"]["type"] == "tree" for row in mapping), 745)
        self.assertEqual(len({row["origin"]["path"] for row in mapping}), 2028)
        self.assertTrue(all(row["projected"]["path"] in projected for row in mapping))
        self.assertIn("upstream-quarantine/.github/workflows/checks.yml.disabled", projected)
        self.assertIn("upstream-quarantine/app/src/free/play.symlink-target", projected)
        self.assertIn("upstream-quarantine/app/src/main/play.gitlink", projected)

    def test_recursive_tree_truncation_and_every_tuple_mutation_fail(self):
        document, count, digest = tree_payload(self.values)
        p.parse_git_tree(document, count, digest)
        attacks = []
        short = copy.deepcopy(document); short["tree"].pop(); attacks.append(short)
        extra = copy.deepcopy(document); extra["tree"].append({"path":"evil","type":"blob","mode":"100644","sha":"1"*40}); attacks.append(extra)
        identity = copy.deepcopy(document); identity["tree"][0]["sha"] = "0"*40; attacks.append(identity)
        mode = copy.deepcopy(document); mode["tree"][0]["mode"] = "100755"; attacks.append(mode)
        kind = copy.deepcopy(document); kind["tree"][0].update(type="commit",mode="160000"); attacks.append(kind)
        truncated = copy.deepcopy(document); truncated["truncated"] = True; attacks.append(truncated)
        for attacked in attacks:
            with self.assertRaises(p.Reject): p.parse_git_tree(attacked, count, digest)

class OverlayAndFrozenControls(unittest.TestCase):
    def test_every_permitted_overlay_path_has_exact_tuple_category_rationale(self):
        p.validate_overlay(overlay())
        self.assertEqual(len(p.CANDIDATE_OVERLAY_POLICY), 11)
        for path, rule in p.CANDIDATE_OVERLAY_POLICY.items():
            self.assertRegex(rule.identity, r"^[0-9a-f]{40}$", path)
            self.assertTrue(rule.category, path); self.assertTrue(rule.rationale, path)
        for path in p.CANDIDATE_OVERLAY_POLICY:
            attacked = overlay(); original = attacked[path]
            attacked[path] = p.GitEntry(path, original.type, original.mode, "0"*40)
            with self.subTest(path=path), self.assertRaises(p.Reject): p.validate_overlay(attacked)

    def test_actual_validation_audit_tests_tasks_thresholds_are_frozen(self):
        p.validate_frozen_controls(p.FROZEN_CONTROLS)
        self.assertEqual(p.FROZEN_CONTROLS["validate_candidate_blob"], p.CANDIDATE_OVERLAY_POLICY[".github/workflows/validate-candidate.yml"].identity)
        self.assertEqual(p.FROZEN_CONTROLS["audit_candidate_blob"], p.CANDIDATE_OVERLAY_POLICY["scripts/ci/audit_candidate.py"].identity)
        self.assertEqual(p.FROZEN_CONTROLS["tests"], list(p.TASK_POLICY["tasks"]))
        self.assertEqual(p.FROZEN_CONTROLS["thresholds"], p.TASK_POLICY["thresholds"])

class AttackMatrix(unittest.TestCase):
    def test_explicit_mode_type_target_and_gitlink_attacks(self):
        expected = {"regular-100755-to-100644", "regular-100644-to-100755",
                    "regular-to-symlink", "symlink-to-regular", "regular-to-gitlink",
                    "gitlink-to-regular", "symlink-target-identity", "gitlink-commit-identity"}
        self.assertEqual(p.tuple_negative_tests(), {name:"rejected" for name in expected})

    def test_independent_androidx_and_nontransitive_attacks(self):
        expected = {"androidx-omission", "androidx-value", "nontransitive-omission", "nontransitive-value"}
        self.assertEqual(p.gradle_property_negative_tests(), {name:"rejected" for name in expected})
        p.validate_gradle_properties({"gradle.properties": p.GRADLE_PROPERTIES})

    def test_six_scope_attacks_mutate_actual_frozen_controls(self):
        expected = {name:"rejected" for name in ("EF","EXCLUDE","NOOP","TASK","SHADOW","THRESHOLD")}
        self.assertEqual(p.recovery_scope_negative_tests(), expected)

class InputsIsolationAndSchema(unittest.TestCase):
    def test_known_inputs_and_unresolved_dynamic_fail_closed(self):
        values = full_inventory(); p.validate_known_inputs(values)
        observed = p.scan_dynamic_inputs(known_contents(), values)
        self.assertEqual(observed["unresolved"], [])
        for fixture in (b"def x=System.getenv(name)\n", b"def x=providers.gradleProperty(name)\n",
                        b"apply from: configPath\n", b'file(System.getenv("CONFIG"))\n',
                        b'apply from: "missing.gradle"\n'):
            inputs = known_contents(); inputs["build.gradle"] = fixture
            with self.assertRaises(p.Reject): p.scan_dynamic_inputs(inputs, values)

    def test_sanitized_environment_rejects_all_channels(self):
        clean = {"PATH":"/usr/bin","HOME":"/tmp/empty","LANG":"C.UTF-8"}; p.validate_environment(clean)
        for name in ("GITHUB_TOKEN","ACTIONS_RUNTIME_TOKEN","RUNNER_TEMP","ANDROID_HOME","GRADLE_USER_HOME","JAVA_HOME"):
            attacked = dict(clean); attacked[name] = "channel"
            with self.assertRaises(p.Reject): p.validate_environment(attacked)

    def test_one_preflight_fresh_identity_and_budget_invariants(self):
        runs = {"total_count":1,"workflow_runs":[{"run_attempt":1}]}
        refs = [{"ref":p.OLD_CANDIDATE_BRANCH,"object":{"sha":p.OLD_CANDIDATE_COMMIT}}]
        result = p.validate_operational_invariants(runs, refs)
        self.assertEqual(result["validation_budget"], {"maximum_dispatches":3,"used_for_fresh_identity":0,
                                                       "required_consecutive_successes":2,"run2_failure_stop":True})
        attacks = [({"total_count":0,"workflow_runs":[]}, refs),
                   ({"total_count":2,"workflow_runs":[{"run_attempt":1},{"run_attempt":1}]}, refs),
                   ({"total_count":1,"workflow_runs":[{"run_attempt":2}]}, refs),
                   (runs, refs + [{"ref":"refs/heads/candidate/antennapod-fresh","object":{"sha":"f"*40}}])]
        for run_attack, ref_attack in attacks:
            with self.assertRaises(p.Reject): p.validate_operational_invariants(run_attack, ref_attack)

    def test_report_schema_and_constant_path_are_closed(self):
        row = {"origin":{"path":"x","type":"tree","mode":"040000","identity":"0"*40},
               "projected":{"path":"x","type":"tree","mode":"040000","identity":"1"*40}}
        origin_projection = [copy.deepcopy(row) for _ in range(p.PINNED_TUPLE_COUNT)]
        report = {"schema":p.REPORT_SCHEMA,"status":"pass",
                  "identity":{"upstream_commit":"x","upstream_tree":"x","upstream_archive_sha256":"x","overlay_sha":"x"},
                  "historical_evidence":{"evidence_commit":"x","old_candidate_commit":"x","old_candidate_branch":"x","pull_request":1,"immutable":True},
                  "overlay":{"entries":[],"policy_digest":"x"},
                  "projection":{"upstream_tuple_count":2028,"upstream_tree_count":745,"upstream_digest":"x","projected_tuple_count":1,"projected_digest":"x","origin_projection":origin_projection},
                  "gradle_inputs":{"known_inventory":p.KNOWN_INPUTS,"dynamic_inputs":{"literal_environment_and_properties":[],"static_root_config":[],"unresolved":[]},"gradle_properties_blob":"x","wrapper_distribution_sha256":"x","wrapper_jar_sha256":"x"},
                  "negative_tests":{"tuples":p.tuple_negative_tests(),"gradle_properties":p.gradle_property_negative_tests(),"recovery_scope":p.recovery_scope_negative_tests()},
                  "invariants":{"one_preflight":{"maximum":1,"observed":1,"run_attempt":1},
                                "fresh_identity":{"must_be_created_after_preflight":True,"present":False,"allowed_historical_identity":p.OLD_CANDIDATE_COMMIT},
                                "validation_budget":{"maximum_dispatches":3,"used_for_fresh_identity":0,"required_consecutive_successes":2,"run2_failure_stop":True}},
                  "isolation":{"sanitized_environment":True,"candidate_workspace":"absent","credential_channels":"absent","runtime_cache_result_channels":"absent","constant_report_path":p.REPORT_PATH}}
        p.validate_report_schema(report)
        self.assertEqual(p.REPORT_PATH, "/tmp/podcast-clips-recovery-preflight/report.json")
        attacked = dict(report); attacked["unexpected"] = True
        with self.assertRaises(p.Reject): p.validate_report_schema(attacked)

if __name__ == "__main__": unittest.main(verbosity=2)
