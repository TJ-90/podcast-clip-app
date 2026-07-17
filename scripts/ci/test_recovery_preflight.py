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

if __name__=="__main__": unittest.main(verbosity=2)
