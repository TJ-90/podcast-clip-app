#!/usr/bin/env python3
"""Offline deterministic hostile fixtures for recovery_preflight."""
from __future__ import annotations

import copy
import hashlib
import json
import unittest
from dataclasses import asdict

import recovery_preflight as p

COMMON = b'''android {\n defaultConfig { resValue "string", "app_name", "AntennaPod" }\n buildTypes { debug { resValue "string", "app_name", "AntennaPod Debug" } }\n}\n'''

def entries():
    result = {path: p.GitEntry(path, kind, mode, identity)
              for path, (kind, mode, identity, _target) in p.QUARANTINE.items()}
    required = set().union(*(set(v) for v in p.KNOWN_INPUTS.values()))
    for path in required:
        data = COMMON if path == "common.gradle" else f"// {path}\n".encode()
        result.setdefault(path, p.GitEntry(path, "blob", "100644", p.git_blob_sha(data)))
    result["gradle.properties"] = p.GitEntry("gradle.properties", "blob", "100644", p.GRADLE_PROPERTIES_BLOB)
    result["common.gradle"] = p.GitEntry("common.gradle", "blob", "100644", p.git_blob_sha(COMMON))
    result["src/main.txt"] = p.GitEntry("src/main.txt", "blob", "100644", p.git_blob_sha(b"main\n"))
    return result

def overlay():
    return {path: p.GitEntry(path, "blob", "100644", hashlib.sha1(path.encode()).hexdigest())
            for path in p.TRUSTED_OVERLAY_PATHS}

def input_bytes():
    result = {}
    for path in set().union(*(set(v) for v in p.KNOWN_INPUTS.values())):
        if path == "common.gradle": result[path] = COMMON
        elif path == "build.gradle": result[path] = b'def ci = System.getenv("CI")\napply from: "common.gradle"\n'
        else: result[path] = f"// {path}\n".encode()
    return result

def payload(values):
    rows = [{"path": e.path, "type": e.type, "mode": e.mode, "sha": e.identity} for e in values.values()]
    body = json.dumps([asdict(values[x]) for x in sorted(values)], sort_keys=True, separators=(",", ":"))
    return ({"sha": p.UPSTREAM_TREE, "truncated": False, "tree": rows},
            len(values), hashlib.sha256(body.encode()).hexdigest())

class TupleInventory(unittest.TestCase):
    def test_inventory_is_order_independent(self):
        base = entries(); document, count, digest = payload(base)
        observed = p.parse_git_tree(document, count, digest)
        document["tree"].reverse()
        self.assertEqual(observed, p.parse_git_tree(document, count, digest))

    def test_truncation_rejected(self):
        document, count, digest = payload(entries())
        for value in (True, None):
            attacked = copy.deepcopy(document); attacked["truncated"] = value
            with self.assertRaises(p.Reject): p.parse_git_tree(attacked, count, digest)

    def test_remove_change_add_mode_and_type_rejected(self):
        base = entries(); document, count, digest = payload(base)
        attacks = []
        removed = copy.deepcopy(document); removed["tree"].pop(); attacks.append(removed)
        changed = copy.deepcopy(document); changed["tree"][0]["sha"] = "0" * 40; attacks.append(changed)
        added = copy.deepcopy(document); added["tree"].append({"path":"evil","type":"blob","mode":"100644","sha":"1"*40}); attacks.append(added)
        mode = copy.deepcopy(document); mode["tree"][0]["mode"] = "100755"; attacks.append(mode)
        kind = copy.deepcopy(document); kind["tree"][0].update(type="commit", mode="160000"); attacks.append(kind)
        for attacked in attacks:
            with self.assertRaises(p.Reject): p.parse_git_tree(attacked, count, digest)

class ClosedProjection(unittest.TestCase):
    def test_every_leaf_maps_once(self):
        projected = p.project_tree(entries(), overlay(), COMMON)
        self.assertIn("upstream-quarantine/gradlew.disabled", projected)
        self.assertIn("upstream-quarantine/app/src/free/play.symlink-target", projected)
        self.assertIn("upstream-quarantine/app/src/main/play.gitlink", projected)
        self.assertIn("licenses/AntennaPod-LICENSE.txt", projected)
        self.assertNotIn("gradlew", projected)

    def test_allowlist_and_overlay_alterations_rejected(self):
        policy = dict(p.QUARANTINE); policy.pop("gradlew")
        with self.assertRaises(p.Reject): p.validate_quarantine(entries(), policy)
        changed = dict(p.QUARANTINE); changed["gradlew"] = ("blob", "100644", changed["gradlew"][2], None)
        with self.assertRaises(p.Reject): p.validate_quarantine(entries(), changed)
        short = overlay(); short.pop(next(iter(short)))
        with self.assertRaises(p.Reject): p.validate_overlay(short)
        extra = overlay(); extra["evil"] = p.GitEntry("evil", "blob", "100644", "0"*40)
        with self.assertRaises(p.Reject): p.validate_overlay(extra)

class GradleInputs(unittest.TestCase):
    def test_complete_gradle_properties_exact_bytes(self):
        p.validate_gradle_properties({"gradle.properties": p.GRADLE_PROPERTIES})
        attacks = [{},
                   {"gradle.properties": p.GRADLE_PROPERTIES + b"extra=true\n"},
                   {"gradle.properties": p.GRADLE_PROPERTIES.replace(b"4096", b"2048")},
                   {"gradle.properties": p.GRADLE_PROPERTIES,
                    "nested/gradle.properties": b"bad=true\n"}]
        for attacked in attacks:
            with self.assertRaises(p.Reject): p.validate_gradle_properties(attacked)

    def test_each_known_category_or_path_removal_fails(self):
        base = entries(); p.validate_known_inputs(base)
        for category, paths in p.KNOWN_INPUTS.items():
            altered = copy.deepcopy(p.KNOWN_INPUTS)
            if paths: altered[category] = paths[1:]
            else: altered.pop(category)
            with self.subTest(category=category), self.assertRaises(p.Reject):
                p.validate_known_inputs(base, altered)
        for path in set().union(*(set(v) for v in p.KNOWN_INPUTS.values())):
            attacked = dict(base); attacked.pop(path)
            with self.subTest(path=path), self.assertRaises(p.Reject):
                p.validate_known_inputs(attacked)

    def test_literal_inputs_resolve_and_dynamic_inputs_fail_closed(self):
        base = entries(); result = p.scan_dynamic_inputs(input_bytes(), base)
        self.assertEqual(result["unresolved"], [])
        self.assertIn({"path":"build.gradle","api":"System.getenv","name":"CI"}, result["literal_environment_and_properties"])
        fixtures = [b"def x=System.getenv(name)\n", b"def x=providers.gradleProperty(name)\n",
                    b"apply from: configPath\n", b'file(System.getenv("CONFIG"))\n',
                    b'apply from: "missing.gradle"\n']
        for fixture in fixtures:
            values = input_bytes(); values["build.gradle"] = fixture
            with self.assertRaises(p.Reject): p.scan_dynamic_inputs(values, base)

class ScopeAndIsolation(unittest.TestCase):
    def test_all_recovery_scope_attacks_rejected(self):
        self.assertEqual(p.recovery_scope_negative_tests(),
                         {x:"rejected" for x in ("EF","EXCLUDE","NOOP","TASK","SHADOW","THRESHOLD")})

    def test_credentials_runtime_build_channels_rejected(self):
        clean = {"PATH":"/usr/bin","HOME":"/tmp/empty","LANG":"C.UTF-8"}
        p.validate_environment(clean)
        for name in ("GITHUB_TOKEN","ACTIONS_RUNTIME_TOKEN","RUNNER_TEMP","ANDROID_HOME","GRADLE_USER_HOME","JAVA_HOME"):
            attacked = dict(clean); attacked[name] = "channel"
            with self.assertRaises(p.Reject): p.validate_environment(attacked)

if __name__ == "__main__": unittest.main(verbosity=2)
