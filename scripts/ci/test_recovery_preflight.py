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
import validate_preflight_report as v
import unicodedata

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

def _strict_tuple_attacks(self):
 expected={"regular-100755-to-100644","regular-100644-to-100755","regular-to-symlink","symlink-to-regular",
           "regular-to-gitlink","gitlink-to-regular","symlink-target-identity","gitlink-commit-identity",
           "symlink-to-gitlink","gitlink-to-symlink"}
 self.assertEqual(p.tuple_negative_tests(),{name:"rejected" for name in expected})

def _strict_property_attacks(self):
 expected={"androidx-omission","androidx-value","nontransitive-omission","nontransitive-value","jvmargs-omission","jvmargs-value"}
 self.assertEqual(p.gradle_property_negative_tests(),{name:"rejected" for name in expected})
 p.validate_gradle_properties({"gradle.properties":p.GRADLE_PROPERTIES})

def _run_fixture(head="a"*40):
 return {"total_count":1,"workflow_runs":[{"run_attempt":1,"head_sha":head,"event":"workflow_dispatch",
          "path":p.PREFLIGHT_WORKFLOW_PATH,"name":p.PREFLIGHT_WORKFLOW_NAME}]}
def _ref_fixture():
 return [{"ref":ref,"object":{"sha":sha}} for ref,sha in p.HISTORICAL_REFS.items()]

def _strict_invariants(self):
 result=p.validate_operational_invariants(_run_fixture(),_ref_fixture())
 self.assertEqual(result["one_preflight"]["head_sha"],"a"*40)
 self.assertEqual(result["fresh_identity"]["allowed_historical_refs"],p.HISTORICAL_REFS)
 attacks=[]
 bad_runs=copy.deepcopy(_run_fixture()); bad_runs["workflow_runs"][0]["head_sha"]="short"; attacks.append((bad_runs,_ref_fixture()))
 bad_runs=copy.deepcopy(_run_fixture()); bad_runs["workflow_runs"][0]["event"]="push"; attacks.append((bad_runs,_ref_fixture()))
 bad_runs=copy.deepcopy(_run_fixture()); bad_runs["workflow_runs"][0]["path"]=".github/workflows/other.yml"; attacks.append((bad_runs,_ref_fixture()))
 bad_runs=copy.deepcopy(_run_fixture()); bad_runs["workflow_runs"][0]["name"]="Other"; attacks.append((bad_runs,_ref_fixture()))
 bad_runs=copy.deepcopy(_run_fixture()); bad_runs["workflow_runs"][0]["run_attempt"]=2; attacks.append((bad_runs,_ref_fixture()))
 added=_ref_fixture()+[{"ref":"refs/heads/candidate/antennapod-fresh","object":{"sha":"f"*40}}]; attacks.append((_run_fixture(),added))
 mutated=_ref_fixture(); mutated[0]["object"]["sha"]="0"*40; attacks.append((_run_fixture(),mutated))
 removed=_ref_fixture()[1:]; attacks.append((_run_fixture(),removed))
 for run_payload,refs_payload in attacks:
  with self.assertRaises(p.Reject): p.validate_operational_invariants(run_payload,refs_payload)

def _valid_strict_report():
 upstream=full_inventory(); projected,mappings=p.project_tree(upstream,overlay(),COMMON)
 manifest=p.report_manifest(projected); rows=p._expected_overlay_rows(); overlay_digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 origin_digest=p.inventory_digest(upstream); overlay_sha="a"*40
 dynamic=p.scan_dynamic_inputs(known_contents(),upstream)
 report={"schema":p.REPORT_SCHEMA,"status":"pass",
 "identity":{"upstream_commit":p.UPSTREAM_COMMIT,"upstream_tree":p.UPSTREAM_TREE,"upstream_archive_sha256":p.UPSTREAM_ARCHIVE_SHA256,"overlay_sha":overlay_sha},
 "historical_evidence":{"evidence_commit":p.EVIDENCE_COMMIT,"candidate_refs":copy.deepcopy(p.HISTORICAL_REFS),"pull_request":copy.deepcopy(p.HISTORICAL_PR),"validation_runs":copy.deepcopy(p.HISTORICAL_RUNS),"immutable":True},
 "overlay":{"entries":rows,"policy_digest":overlay_digest},
 "projection":{"upstream_tuple_count":2028,"upstream_tree_count":745,"upstream_digest":origin_digest,"projected_tuple_count":len(projected),"projected_digest":p.inventory_digest(projected),"origin_projection":mappings,"projected_manifest":manifest},
 "gradle_inputs":{"known_inventory":copy.deepcopy(p.KNOWN_INPUTS),"dynamic_inputs":dynamic,"gradle_properties_blob":p.GRADLE_PROPERTIES_BLOB,"wrapper_distribution_sha256":p.GRADLE_DISTRIBUTION_SHA256,"wrapper_jar_sha256":p.GRADLE_WRAPPER_JAR_SHA256},
 "negative_tests":{"tuples":p.tuple_negative_tests(),"gradle_properties":p.gradle_property_negative_tests(),"recovery_scope":p.recovery_scope_negative_tests()},
 "invariants":p.validate_operational_invariants(_run_fixture(overlay_sha),_ref_fixture()),
 "isolation":{"sanitized_environment":True,"candidate_workspace":"absent","credential_channels":"absent","runtime_cache_result_channels":"absent","constant_report_path":p.REPORT_PATH}}
 return report,origin_digest

def _strict_report_tamper_rejection(self):
 self.assertEqual(p.PINNED_TUPLE_DIGEST,"b05cc9e64c2285efab776bf05a6de65ba8396e0de8a6329c00a9a23ba3997aee")
 report,synthetic_digest=_valid_strict_report(); production=p.PINNED_TUPLE_DIGEST; p.PINNED_TUPLE_DIGEST=synthetic_digest
 try:
  p.validate_report_schema(report)
  attacks=[]
  def attack(path,value):
   item=copy.deepcopy(report); target=item
   for key in path[:-1]: target=target[key]
   target[path[-1]]=value; attacks.append(item)
  attack(("identity","upstream_commit"),"0"*40)
  attack(("historical_evidence","immutable"),False)
  item=copy.deepcopy(report); item["historical_evidence"]["candidate_refs"].pop(next(iter(p.HISTORICAL_REFS))); attacks.append(item)
  item=copy.deepcopy(report); item["historical_evidence"]["validation_runs"]["29562294514"]["conclusion"]="success"; attacks.append(item)
  item=copy.deepcopy(report); item["overlay"]["entries"][0]["identity"]="0"*40; attacks.append(item)
  attack(("overlay","policy_digest"),"0"*64)
  attack(("gradle_inputs","gradle_properties_blob"),"0"*40)
  item=copy.deepcopy(report); item["gradle_inputs"]["dynamic_inputs"]["unresolved"]=["unknown"]; attacks.append(item)
  item=copy.deepcopy(report); item["negative_tests"]["tuples"]["symlink-to-gitlink"]="accepted"; attacks.append(item)
  attack(("invariants","one_preflight","event"),"push")
  attack(("invariants","one_preflight","head_sha"),"b"*40)
  attack(("isolation","credential_channels"),"present")
  attack(("projection","projected_digest"),"0"*64)
  item=copy.deepcopy(report); item["projection"]["projected_manifest"][0]["identity"]="0"*40; attacks.append(item)
  for index,item in enumerate(attacks):
   with self.subTest(tamper=index),self.assertRaises(p.Reject): p.validate_report_schema(item)
 finally: p.PINNED_TUPLE_DIGEST=production

AttackMatrix.test_explicit_mode_type_target_and_gitlink_attacks=_strict_tuple_attacks
AttackMatrix.test_independent_androidx_and_nontransitive_attacks=_strict_property_attacks
InputsIsolationAndSchema.test_one_preflight_fresh_identity_and_budget_invariants=_strict_invariants
InputsIsolationAndSchema.test_report_schema_and_constant_path_are_closed=_strict_report_tamper_rejection

class Recovery2LexicalResolver(unittest.TestCase):
    def test_exact_valid_matrix_and_common_gradle_regression(self):
        matrix = p.resolver_matrix_results()
        self.assertEqual(set(matrix["valid"]), set(p.R2_VALID_CASES))
        self.assertTrue(all(value == "accepted" for value in matrix["valid"].values()))
        declaring = "app/build.gradle"
        target = "common.gradle"
        entries = {
            declaring: p.GitEntry(declaring, "blob", "100644", "1" * 40),
            target: p.GitEntry(target, "blob", "100644", "2" * 40),
        }
        edge = p.resolve_static_literal(declaring, "../common.gradle", entries, 1)
        self.assertEqual(edge, {
            "declaring": {"path": declaring, "type": "blob", "mode": "100644", "identity": "1" * 40},
            "literal": "../common.gradle",
            "normalized_target": target,
            "target": {"path": target, "type": "blob", "mode": "100644", "identity": "2" * 40},
            "depth": 1,
        })

    def test_all_36_hostile_literals_targets_and_syntax_are_rejected(self):
        matrix = p.resolver_matrix_results()
        self.assertEqual(set(matrix["hostile"]), set(p.R2_HOSTILE_CASES))
        self.assertTrue(all(value == "rejected" for value in matrix["hostile"].values()))

    def test_all_10_spoofed_declaring_entries_are_rejected(self):
        matrix = p.resolver_matrix_results()
        self.assertEqual(set(matrix["declaring"]), set(p.R2_DECLARE_CASES))
        self.assertTrue(all(value == "rejected" for value in matrix["declaring"].values()))

    def test_multi_parent_in_root_passes_but_root_escape_fails(self):
        values = {
            "a/b/c/build.gradle": p.GitEntry("a/b/c/build.gradle", "blob", "100644", "1" * 40),
            "common.gradle": p.GitEntry("common.gradle", "blob", "100644", "2" * 40),
        }
        self.assertEqual(
            p.resolve_static_literal("a/b/c/build.gradle", "../../../common.gradle", values)["normalized_target"],
            "common.gradle",
        )
        with self.assertRaises(p.Reject):
            p.resolve_static_literal("a/b/c/build.gradle", "../../../../escape.gradle", values)

    def test_case_unicode_type_mode_blob_symlink_and_gitlink_targets_fail(self):
        declaring = p.GitEntry("app/build.gradle", "blob", "100644", "1" * 40)
        attacks = [
            {"app/build.gradle": declaring, "Common.gradle": p.GitEntry("Common.gradle", "blob", "100644", "2" * 40)},
            {"app/build.gradle": declaring, "common.gradle": p.GitEntry("common.gradle", "tree", "040000", "2" * 40)},
            {"app/build.gradle": declaring, "common.gradle": p.GitEntry("common.gradle", "blob", "120000", "2" * 40)},
            {"app/build.gradle": declaring, "common.gradle": p.GitEntry("common.gradle", "commit", "160000", "2" * 40)},
            {"app/build.gradle": declaring, "common.gradle": p.GitEntry("common.gradle", "blob", "100644", "bad")},
        ]
        for entries in attacks:
            with self.subTest(entries=entries), self.assertRaises(p.Reject):
                p.resolve_static_literal("app/build.gradle", "../common.gradle", entries)

    def test_no_filesystem_resolution_or_link_following_surface(self):
        forbidden = {"realpath", "resolve", "stat", "readlink", "submodule"}
        names = set(p.resolve_static_literal.__code__.co_names)
        self.assertTrue(forbidden.isdisjoint(names))


class Recovery2GraphTraversal(unittest.TestCase):
    @staticmethod
    def graph(mapping):
        contents = {}
        entries = {}
        for path, target in mapping.items():
            data = b"// leaf\n" if target is None else f'apply from: "{target}"\n'.encode()
            contents[path] = data
            entries[path] = p.GitEntry(path, "blob", "100644", p.git_blob_sha(data))
        return contents, entries

    def test_direct_two_node_and_indirect_cycles_fail(self):
        graphs = [
            {"a.gradle": "a.gradle"},
            {"a.gradle": "b.gradle", "b.gradle": "a.gradle"},
            {"a.gradle": "b.gradle", "b.gradle": "c.gradle", "c.gradle": "b.gradle"},
        ]
        for graph in graphs:
            contents, entries = self.graph(graph)
            with self.subTest(graph=graph), self.assertRaisesRegex(p.Reject, "cycle"):
                p.scan_static_graph(contents, entries, ["a.gradle"])

    def test_diamond_acyclic_graph_passes_and_binds_every_edge(self):
        contents = {
            "a.gradle": b'apply from: "b.gradle"\napply from: "c.gradle"\n',
            "b.gradle": b'apply from: "d.gradle"\n',
            "c.gradle": b'apply from: "d.gradle"\n',
            "d.gradle": b"// leaf\n",
        }
        entries = {
            path: p.GitEntry(path, "blob", "100644", p.git_blob_sha(data))
            for path, data in contents.items()
        }
        report = p.scan_static_graph(contents, entries, ["a.gradle"])
        self.assertEqual(len(report["static_include_edges"]), 4)
        self.assertEqual(report["unresolved"], [])

    def test_depth_32_passes_and_edge_33_fails(self):
        def chain(edges):
            mapping = {f"d{index}.gradle": f"d{index + 1}.gradle" for index in range(edges)}
            mapping[f"d{edges}.gradle"] = None
            return self.graph(mapping)
        contents, entries = chain(32)
        report = p.scan_static_graph(contents, entries, ["d0.gradle"])
        self.assertEqual(report["max_depth"], 32)
        contents, entries = chain(33)
        with self.assertRaisesRegex(p.Reject, "depth exceeds 32"):
            p.scan_static_graph(contents, entries, ["d0.gradle"])

    def test_deduplicated_target_still_validates_each_incoming_tuple(self):
        contents = {
            "a.gradle": b'apply from: "d.gradle"\n',
            "b.gradle": b'apply from: "d.gradle"\n',
            "d.gradle": b"// leaf\n",
        }
        entries = {
            path: p.GitEntry(path, "blob", "100644", p.git_blob_sha(data))
            for path, data in contents.items()
        }
        report = p.scan_static_graph(contents, entries, ["a.gradle", "b.gradle"])
        self.assertEqual(len(report["static_include_edges"]), 2)
        attacked = dict(entries)
        attacked["d.gradle"] = p.GitEntry("d.gradle", "blob", "120000", entries["d.gradle"].identity)
        with self.assertRaises(p.Reject):
            p.scan_static_graph(contents, attacked, ["a.gradle", "b.gradle"])


class Recovery2ScopeAndInventory(unittest.TestCase):
    def test_closed_eight_path_categories_and_mandatory_workflow(self):
        self.assertEqual(set(p.R2_ALLOWED_CHANGES), {
            "scripts/ci/recovery_preflight.py",
            "scripts/ci/test_recovery_preflight.py",
            "scripts/ci/validate_preflight_report.py",
            "config/recovery-preflight-report-v2.schema.json",
            "config/recovery-2-control.lock.json",
            ".github/workflows/preflight-recovery-2.yml",
            "UPSTREAM.md",
            "docs/base-selection-report.md",
        })
        self.assertEqual(p.R2_ALLOWED_CHANGES[p.R2_WORKFLOW_PATH], ("add", "one-shot-workflow"))
        self.assertNotIn(p.PREFLIGHT_WORKFLOW_PATH, p.R2_ALLOWED_CHANGES)

    def test_schema_report_parent_authorization_and_gate_constants(self):
        self.assertEqual(p.R2_REPORT_SCHEMA, "podcast-clips/story1-recovery-preflight/v2")
        self.assertEqual(p.R2_REPORT_PATH, "/tmp/podcast-clips-recovery-2-preflight/report-v2.json")
        self.assertEqual(p.R2_PARENT, "c43ddf3409ea0ea793982f07926ce1e1a6925c82")
        self.assertEqual(p.R2_MAX_INCLUDE_DEPTH, 32)
        self.assertEqual(p.UPSTREAM_COMMIT, "1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7")
        self.assertEqual(p.TASK_POLICY["thresholds"]["max_dispatches"], 3)
        self.assertEqual(p.TASK_POLICY["thresholds"]["required_consecutive_successes"], 2)

    def test_complete_pagination_accepts_101_rows_and_rejects_duplicates_or_total_drift(self):
        original = p._public_json
        def row(index):
            return {"id": index, "run_attempt": 1, "event": "workflow_dispatch", "head_sha": "a" * 40,
                    "status": "completed", "conclusion": "success", "path": p.R2_WORKFLOW_PATH,
                    "name": p.R2_WORKFLOW_NAME}
        pages = {
            1: {"total_count": 101, "workflow_runs": [row(index) for index in range(1, 101)]},
            2: {"total_count": 101, "workflow_runs": [row(101)]},
        }
        try:
            p._public_json = lambda url: pages[int(url.rsplit("page=", 1)[1])]
            rows, evidence = p._r2_paginated_runs("workflow")
            self.assertEqual(len(rows), 101)
            self.assertEqual(evidence["pages"], 2)
            attacked = copy.deepcopy(pages)
            attacked[2]["workflow_runs"] = [row(100)]
            p._public_json = lambda url: attacked[int(url.rsplit("page=", 1)[1])]
            with self.assertRaises(p.Reject):
                p._r2_paginated_runs("workflow")
            attacked = copy.deepcopy(pages)
            attacked[2]["total_count"] = 102
            p._public_json = lambda url: attacked[int(url.rsplit("page=", 1)[1])]
            with self.assertRaises(p.Reject):
                p._r2_paginated_runs("workflow")
        finally:
            p._public_json = original

    def test_matrix_inventory_is_complete(self):
        matrix = p.resolver_matrix_results()
        self.assertEqual(
            {section: len(values) for section, values in matrix.items()},
            {"valid": 10, "hostile": 36, "declaring": 10, "recursion": 9},
        )
# --- ADR-003 Amendment A independent oracle and mutation tests. ---
class AmendmentAExecutedFixtures(unittest.TestCase):
    def test_matrix_cases_are_executed_and_transcript_is_derived(self):
        matrix = p.resolver_matrix_results()
        transcript = p.R2_MATRIX_TRANSCRIPT
        self.assertEqual([row["ordinal"] for row in transcript], list(range(1, 11)))
        self.assertEqual(
            [row["case"] for row in transcript],
            ["VALID-10", "CYCLE-01", "CYCLE-02", "CYCLE-03", "CYCLE-04",
             "DEPTH-01", "DEPTH-02", "DEPTH-03", "DEPTH-04", "DEPTH-05"],
        )
        self.assertEqual(transcript[0]["detail"]["edges"], 32)
        self.assertEqual(transcript[0]["detail"]["target_33_reads"], 0)
        self.assertIn("a.gradle -> b.gradle -> a.gradle", transcript[2]["detail"]["cycle"])
        self.assertEqual({row["case"] for row in transcript[1:]}, set(matrix["recursion"]))

    def test_parameterized_execution_cannot_be_replaced_by_labels(self):
        original = p._r2_valid_10
        calls = []
        def wrapped():
            calls.append("VALID-10")
            return original()
        p._r2_valid_10 = wrapped
        try:
            p.resolver_matrix_results()
        finally:
            p._r2_valid_10 = original
        self.assertEqual(calls, ["VALID-10"])
        self.assertEqual(len(p.R2_MATRIX_TRANSCRIPT), 10)

def amendment_independent_resolve(declaring, literal, origin):
    if not literal or "\\" in literal or "\0" in literal or literal.startswith("/"):
        raise ValueError("hostile literal")
    if unicodedata.normalize("NFC", literal) != literal:
        raise ValueError("non-NFC")
    base = declaring.split("/")[:-1]
    for part in literal.split("/"):
        if part in {"", "."}:
            raise ValueError("empty/dot")
        if part == "..":
            if not base:
                raise ValueError("escape")
            base.pop()
        else:
            base.append(part)
    path = "/".join(base)
    if path not in origin:
        raise ValueError("missing")
    return path

def amendment_fixture_report():
    contents = {
        "a.gradle": b'apply from: "b.gradle"\napply from: "c.gradle"\n',
        "b.gradle": b"// leaf\n",
        "c.gradle": b"// leaf\n",
    }
    origin = {
        path: {"path": path, "type": "blob", "mode": "100644", "identity": p.git_blob_sha(data)}
        for path, data in contents.items()
    }
    edges = []
    for target in ("b.gradle", "c.gradle"):
        resolved = amendment_independent_resolve("a.gradle", target, origin)
        edges.append({
            "declaring": copy.deepcopy(origin["a.gradle"]),
            "literal": target,
            "normalized_target": resolved,
            "target": copy.deepcopy(origin[resolved]),
            "depth": 1,
        })
    report = {
        "resolver": {
            "version": 2, "semantics": "declaring-relative-posix-lexical",
            "max_include_depth": 32, "realpath": False, "follow_symlinks": False,
            "fetch_gitlinks": False, "edges": edges, "max_observed_depth": 1,
            "cycles": [], "unresolved": [],
        },
        "gradle_inputs": {"known_inventory": {"fixture": ["a.gradle"]}},
    }
    return report, origin, contents

class AmendmentAIndependentEdgeOracle(unittest.TestCase):
    def test_exact_edges_and_all_endpoint_order_canaries(self):
        report, origin, contents = amendment_fixture_report()
        old_loader = v._AMEND_CONTENT_LOADER
        v._AMEND_CONTENT_LOADER = lambda path: contents[path]
        try:
            v.validate_resolver(report, origin)
            attacks = []
            def mutate(index, side, field, value):
                item = copy.deepcopy(report)
                item["resolver"]["edges"][index][side][field] = value
                attacks.append(item)
            mutate(0, "target", "identity", "9" * 40)
            mutate(0, "target", "mode", "100755")
            mutate(0, "target", "type", "tree")
            mutate(0, "declaring", "identity", "8" * 40)
            mutate(0, "declaring", "path", "missing.gradle")
            mutate(0, "target", "path", "B.gradle")
            mutate(0, "target", "path", "Gra\u0301dle.gradle")
            omitted = copy.deepcopy(report); omitted["resolver"]["edges"].pop(); attacks.append(omitted)
            duplicate = copy.deepcopy(report); duplicate["resolver"]["edges"].append(copy.deepcopy(duplicate["resolver"]["edges"][0])); attacks.append(duplicate)
            extra = copy.deepcopy(report); extra["resolver"]["edges"].append(copy.deepcopy(extra["resolver"]["edges"][1])); attacks.append(extra)
            reordered = copy.deepcopy(report); reordered["resolver"]["edges"].reverse(); attacks.append(reordered)
            for index, attacked in enumerate(attacks):
                with self.subTest(canary=index), self.assertRaises(v.Reject):
                    v.validate_resolver(attacked, origin)
        finally:
            v._AMEND_CONTENT_LOADER = old_loader

    def test_false_projection_rejected_against_independent_2028_digest(self):
        upstream = full_inventory()
        origins = [p._r2_tuple(upstream[path]) for path in sorted(upstream)]
        mappings = [{"origin": copy.deepcopy(row), "projected": copy.deepcopy(row)} for row in origins]
        rows = p._expected_overlay_rows()
        report = {
            "overlay": {"entries": rows, "policy_digest": v.digest(rows)},
            "projection": {
                "upstream_tuple_count": 2028, "upstream_tree_count": 745,
                "upstream_digest": v.rows_digest(origins),
                "projected_tuple_count": 2028, "projected_digest": v.rows_digest(origins),
                "origin_projection": mappings, "projected_manifest": copy.deepcopy(origins),
            },
        }
        old_digest = v.UP_DIGEST
        v.UP_DIGEST = v.rows_digest(origins)
        try:
            observed = v.validate_projection(report)
            self.assertEqual(len(observed), 2028)
            attacked = copy.deepcopy(report)
            attacked["projection"]["origin_projection"][0]["origin"]["identity"] = "9" * 40
            with self.assertRaises(v.Reject):
                v.validate_projection(attacked)
        finally:
            v.UP_DIGEST = old_digest

def amendment_lock():
    return {
        "schema": v.LOCK_SCHEMA,
        "authorization": {
            "active_goal_continuation": True,
            "adr_sha256": v.ADR_SHA256,
            "test_addendum_sha256": v.TEST_ADDENDUM_SHA256,
            "supersedes": "G009 no-corrected-preflight constraint only",
        },
        "parent": v.PARENT,
        "amendment": {
            "adr_amendment_sha256": v.AMENDMENT_SHA256,
            "test_addendum_sha256": v.AMENDMENT_TEST_SHA256,
            "path_proof_sha256": v.PATH_PROOF_SHA256,
            "aggregate_parent": v.PARENT,
            "rejected_control": v.REJECTED_CONTROL,
            "rejected_tree": v.REJECTED_TREE,
            "repair_parent": v.REJECTED_CONTROL,
            "incremental_paths": list(v.REPAIR_PATHS),
            "schema_blob": v.SCHEMA_BLOB,
            "workflow_id": v.WORKFLOW_ID,
            "zero_runs_required": True,
        },
        "allowed_changes": v.expected_allowed_changes(),
        "controls": {
            "scripts/ci/recovery_preflight.py": "1" * 40,
            "scripts/ci/test_recovery_preflight.py": "2" * 40,
            "scripts/ci/validate_preflight_report.py": "3" * 40,
            "config/recovery-preflight-report-v2.schema.json": v.SCHEMA_BLOB,
        },
        "workflow": {"path": v.WORKFLOW_PATH, "name": v.WORKFLOW_NAME, "trigger": "workflow_dispatch", "permissions": {}},
        "report": {"schema": v.SCHEMA_ID, "path": v.REPORT_PATH},
        "resolver": {"version": 2, "semantics": "declaring-relative-posix-lexical", "max_include_depth": 32, "realpath": False, "follow_symlinks": False, "fetch_gitlinks": False},
        "historical": {
            "g001": "failed-attempt-1", "g009": "failed-attempt-1", "g002": "pending",
            "evidence_commit": v.EVIDENCE, "terminal_report_commit": v.PARENT,
            "legacy_workflow_id": v.LEGACY_WORKFLOW_ID, "legacy_run_id": v.LEGACY_RUN_ID,
            "legacy_control_sha": v.LEGACY_CONTROL, "legacy_artifacts": 0,
        },
        "gates": {
            "upstream_commit": v.UP_COMMIT, "upstream_tree": v.UP_TREE,
            "archive_sha256": v.ARCHIVE, "candidate_max_dispatches": 3,
            "required_consecutive_successes": 2, "critical_gap_budget": 0,
            "max_minutes": 25, "run2_failure_stop": True,
        },
    }

def amendment_full_report():
    lock = amendment_lock()
    upstream = full_inventory()
    contents = known_contents()
    for path, data in contents.items():
        upstream[path] = p.GitEntry(path, "blob", "100644", p.git_blob_sha(data))
    origins = [p._r2_tuple(upstream[path]) for path in sorted(upstream)]
    mappings = [{"origin": copy.deepcopy(row), "projected": copy.deepcopy(row)} for row in origins]
    roots = sorted(set().union(*(set(value) for value in p.KNOWN_INPUTS.values())))
    detailed = p.scan_static_graph(contents, upstream, roots)
    overlay_rows = p._expected_overlay_rows()
    control_sha = "a" * 40
    run = {
        "id": 9001, "run_attempt": 1, "event": "workflow_dispatch",
        "head_sha": control_sha, "status": "in_progress", "conclusion": None,
        "path": v.WORKFLOW_PATH, "name": v.WORKFLOW_NAME,
    }
    inventory = {
        "pages": 1, "page_counts": [1], "total_count": 1,
        "inventory_sha256": v.digest([run]), "runs": [run],
    }
    legacy = {
        "workflow_id": v.LEGACY_WORKFLOW_ID, "workflow_path": v.LEGACY_WORKFLOW_PATH,
        "workflow_name": v.LEGACY_WORKFLOW_NAME, "workflow_blob": v.LEGACY_WORKFLOW_BLOB,
        "run_id": v.LEGACY_RUN_ID, "run_attempt": 1, "event": "workflow_dispatch",
        "head_sha": v.LEGACY_CONTROL, "status": "completed", "conclusion": "failure",
        "artifacts": 0, "error": "Reject: non-canonical Git path: '../common.gradle'",
        "inventory": {"total_count": 1},
    }
    report = {
        "schema": v.SCHEMA_ID, "status": "pass",
        "authorization": copy.deepcopy(lock["authorization"]),
        "historical_evidence": {
            "evidence_commit": v.EVIDENCE, "terminal_report_commit": v.PARENT,
            "goals": {"G001": "failed-attempt-1", "G009": "failed-attempt-1", "G002": "pending"},
            "legacy_preflight": legacy, "candidate_refs": copy.deepcopy(v.REFS),
            "pull_request": copy.deepcopy(v.PR), "validation_runs": copy.deepcopy(v.RUNS),
            "immutable": True,
        },
        "control": {
            "control_sha": control_sha, "first_parent": v.PARENT,
            "allowed_changes": copy.deepcopy(lock["allowed_changes"]),
            "control_blobs": copy.deepcopy(lock["controls"]), "report_schema": v.SCHEMA_ID,
            "report_path": v.REPORT_PATH, "resolver_version": 2, "max_include_depth": 32,
        },
        "correction_diff": [{
            "path": v.WORKFLOW_PATH, "operation": "add", "category": "one-shot-workflow",
            "old": None,
            "new": {"path": v.WORKFLOW_PATH, "type": "blob", "mode": "100644", "identity": "4" * 40},
        }],
        "workflow": {
            "id": v.WORKFLOW_ID, "name": v.WORKFLOW_NAME, "path": v.WORKFLOW_PATH,
            "state": "active", "blob": "5" * 40, "control_sha": control_sha,
            "run_id": 9001, "run_attempt": 1, "event": "workflow_dispatch", "status": "in_progress",
        },
        "identity": {
            "upstream_commit": v.UP_COMMIT, "upstream_tree": v.UP_TREE,
            "upstream_archive_sha256": v.ARCHIVE, "control_sha": control_sha,
        },
        "overlay": {"entries": overlay_rows, "policy_digest": v.digest(overlay_rows)},
        "projection": {
            "upstream_tuple_count": 2028, "upstream_tree_count": 745,
            "upstream_digest": v.rows_digest(origins), "projected_tuple_count": 2028,
            "projected_digest": v.rows_digest(origins), "origin_projection": mappings,
            "projected_manifest": copy.deepcopy(origins),
        },
        "gradle_inputs": {
            "known_inventory": copy.deepcopy(p.KNOWN_INPUTS),
            "dynamic_inputs": p.scan_dynamic_inputs(contents, upstream),
            "gradle_properties_blob": v.PROPS, "wrapper_distribution_sha256": v.DIST,
            "wrapper_jar_sha256": v.JAR,
        },
        "resolver": {
            "version": 2, "semantics": "declaring-relative-posix-lexical",
            "max_include_depth": 32, "realpath": False, "follow_symlinks": False,
            "fetch_gitlinks": False, "edges": detailed["static_include_edges"],
            "max_observed_depth": detailed["max_depth"], "cycles": [], "unresolved": [],
        },
        "negative_tests": {
            "tuples": {name: "rejected" for name in v.TUPLES},
            "gradle_properties": {name: "rejected" for name in v.PROPERTIES},
            "recovery_scope": {name: "rejected" for name in v.SCOPE},
            "resolver_valid": {name: "accepted" for name in v.VALID},
            "resolver_hostile": {name: "rejected" for name in v.HOSTILE},
            "declaring": {name: "rejected" for name in v.DECLARE},
            "recursion": {name: ("accepted" if name in {"CYCLE-04", "DEPTH-01", "DEPTH-02"} else "rejected") for name in v.RECURSION},
        },
        "invariants": {
            "legacy_preflight": {
                "workflow_id": v.LEGACY_WORKFLOW_ID, "run_id": v.LEGACY_RUN_ID,
                "run_attempt": 1, "head_sha": v.LEGACY_CONTROL,
                "conclusion": "failure", "artifacts": 0,
            },
            "recovery2_preflight": {
                "maximum_runs": 1, "prior_runs": 0, "required_run_attempt": 1,
                "candidate_created": False,
            },
            "candidate_gate": copy.deepcopy(lock["gates"]),
        },
        "isolation": {
            "sanitized_environment": True, "candidate_workspace": "absent",
            "credential_channels": "absent", "runtime_cache_result_channels": "absent-from-parser",
            "constant_report_path": v.REPORT_PATH, "checkout": False,
            "android_gradle_execution": False, "realpath": False,
            "follow_symlinks": False, "fetch_gitlinks": False,
        },
        "workflow_inventory": copy.deepcopy(inventory),
        "observations": [
            {"stage": "in_workflow_start", "observed_at": "2026-07-18T00:00:00Z", **copy.deepcopy(inventory)},
            {"stage": "in_workflow_end", "observed_at": "2026-07-18T00:00:01Z", **copy.deepcopy(inventory)},
        ],
    }
    return report, lock, contents, origins

class AmendmentAFullValidatorRegression(unittest.TestCase):
    def test_target_identity_only_mutation_fails_full_validate_report(self):
        report, lock, contents, origins = amendment_full_report()
        old_digest, old_loader = v.UP_DIGEST, v._AMEND_CONTENT_LOADER
        v.UP_DIGEST = v.rows_digest(origins)
        v._AMEND_CONTENT_LOADER = lambda path: contents[path]
        try:
            v.validate_report(report, "a" * 40, lock)
            attacked = copy.deepcopy(report)
            attacked["resolver"]["edges"][0]["target"]["identity"] = "9" * 40
            with self.assertRaises(v.Reject):
                v.validate_report(attacked, "a" * 40, lock)
        finally:
            v.UP_DIGEST, v._AMEND_CONTENT_LOADER = old_digest, old_loader

    def test_always_pass_validator_is_caught_by_meta_canary(self):
        report, lock, contents, origins = amendment_full_report()
        attacked = copy.deepcopy(report)
        attacked["resolver"]["edges"][0]["target"]["identity"] = "9" * 40
        old_digest, old_loader, old_validator = v.UP_DIGEST, v._AMEND_CONTENT_LOADER, v.validate_resolver
        v.UP_DIGEST = v.rows_digest(origins)
        v._AMEND_CONTENT_LOADER = lambda path: contents[path]
        v.validate_resolver = lambda *_args, **_kwargs: None
        def require_reject():
            try:
                v.validate_report(attacked, "a" * 40, lock)
            except v.Reject:
                return
            raise AssertionError("always-pass validator accepted target mutation")
        try:
            with self.assertRaises(AssertionError):
                require_reject()
        finally:
            v.UP_DIGEST, v._AMEND_CONTENT_LOADER, v.validate_resolver = old_digest, old_loader, old_validator

if __name__=="__main__": unittest.main(verbosity=2)