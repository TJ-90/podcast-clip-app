#!/usr/bin/env python3
"""Independent, offline, constant-path Story 1 preflight report validator."""
import argparse, hashlib, json, os, re, stat
from pathlib import Path, PurePosixPath
from typing import Mapping

REPORT_PATH="/tmp/podcast-clips-recovery-preflight/report.json"
SCHEMA="podcast-clips/story1-recovery-preflight/v1"
UP_COMMIT="1d2bd1c8f9d3ea46fc777a14d5a035558f07b7f7"; UP_TREE="ebfc8990216aded7ad4ab6d393fa6e0131a69fee"
ARCHIVE="99c9d77996595d6d75ed170240d5849ce381931f6d5e726d12e198ff15dae8a2"
UP_DIGEST="b05cc9e64c2285efab776bf05a6de65ba8396e0de8a6329c00a9a23ba3997aee"
OVERLAY_DIGEST="9f0be1ba6ee4c873ae761a8b8a77367ee6cad2c32f8d9f021d485939e634a655"
KNOWN_DIGEST="43cb57b8bf61100948512e0e66fd5c55380cc25ff2020ef81aa820b44386e732"
PROPS="19058640ca22d0398085d67d6a49e68892894a80"; DIST="20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78"; JAR="81a82aaea5abcc8ff68b3dfcb58b3c3c429378efd98e7433460610fecd7ae45f"
EVIDENCE="37593a4217bd442d407d8b0f63d7fcb2fa10f069"; WF_PATH=".github/workflows/preflight-recovery.yml"; WF_NAME="Story 1 recovery preflight"
ALLOWED_ENV={"HOME","LANG","LC_ALL","PATH"}
REFS={"refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562152128":"1152cfce3b78cbc9cfb64a69bb0eb68551273371","refs/heads/candidate/antennapod-1d2bd1c8f9d3-r29562160851":"c58e2607c57925486b856416e1b3f9044673e2be"}
RUNS={
"29562294514":{"id":29562294514,"conclusion":"failure","event":"workflow_dispatch","head_sha":"c58e2607c57925486b856416e1b3f9044673e2be","workflow_id":314940238,"workflow_path":".github/workflows/validate-candidate.yml","workflow_name":"Validate exact candidate"},
"29562814924":{"id":29562814924,"conclusion":"failure","event":"workflow_dispatch","head_sha":"2a29aaf00b6c9414f627b1e4a24a8536412c47d7","workflow_id":314940238,"workflow_path":".github/workflows/validate-candidate.yml","workflow_name":"Validate exact candidate"},
"29563023789":{"id":29563023789,"conclusion":"cancelled","event":"workflow_dispatch","head_sha":"2a29aaf00b6c9414f627b1e4a24a8536412c47d7","workflow_id":314940238,"workflow_path":".github/workflows/validate-candidate.yml","workflow_name":"Validate exact candidate"}}
PR={"number":1,"state":"closed","merged":False,"head_sha":"c58e2607c57925486b856416e1b3f9044673e2be"}
TUPLES={"regular-100755-to-100644","regular-100644-to-100755","regular-to-symlink","symlink-to-regular","regular-to-gitlink","gitlink-to-regular","symlink-target-identity","gitlink-commit-identity","symlink-to-gitlink","gitlink-to-symlink"}
PROPERTIES={"androidx-omission","androidx-value","nontransitive-omission","nontransitive-value","jvmargs-omission","jvmargs-value"}; SCOPE={"EF","EXCLUDE","NOOP","TASK","SHADOW","THRESHOLD"}
class Reject(RuntimeError): pass

def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def clean_path(value):
 if not isinstance(value,str) or not value or value.startswith(("/","\\")) or "\0" in value or "\\" in value or any(x in {"",".",".."} for x in value.split("/")) or str(PurePosixPath(value))!=value: raise Reject("invalid tuple path")
 return value
def rows_digest(rows):
 if not isinstance(rows,list): raise Reject("manifest is not a list")
 valid={"blob":{"100644","100755","120000"},"tree":{"040000"},"commit":{"160000"}}; values={}
 for row in rows:
  if not isinstance(row,Mapping) or set(row)!={"path","type","mode","identity"}: raise Reject("tuple schema changed")
  path=clean_path(row["path"]); kind=row["type"]
  if kind not in valid or row["mode"] not in valid[kind] or not isinstance(row["identity"],str) or not re.fullmatch(r"[0-9a-f]{40}",row["identity"]) or path in values: raise Reject("tuple invalid/duplicate")
  values[path]=dict(row)
 return digest([values[path] for path in sorted(values)])
def all_rejected(value,names): return isinstance(value,Mapping) and set(value)==names and all(x=="rejected" for x in value.values())
def validate_environment(env=None):
 if set(os.environ if env is None else env)-ALLOWED_ENV: raise Reject("non-allowlisted validator channel")

def validate(report,overlay_sha):
 if not re.fullmatch(r"[0-9a-f]{40}",overlay_sha): raise Reject("expected overlay SHA invalid")
 top={"schema","status","identity","historical_evidence","overlay","projection","gradle_inputs","negative_tests","invariants","isolation"}
 if not isinstance(report,Mapping) or set(report)!=top or report.get("schema")!=SCHEMA or report.get("status")!="pass": raise Reject("report envelope changed")
 identity={"upstream_commit":UP_COMMIT,"upstream_tree":UP_TREE,"upstream_archive_sha256":ARCHIVE,"overlay_sha":overlay_sha}
 if report.get("identity")!=identity: raise Reject("identity values changed")
 history={"evidence_commit":EVIDENCE,"candidate_refs":REFS,"pull_request":PR,"validation_runs":RUNS,"immutable":True}
 if report.get("historical_evidence")!=history or report["historical_evidence"]["immutable"] is not True: raise Reject("history changed")
 overlay=report.get("overlay")
 if not isinstance(overlay,Mapping) or set(overlay)!={"entries","policy_digest"} or overlay["policy_digest"]!=OVERLAY_DIGEST or digest(overlay["entries"])!=OVERLAY_DIGEST: raise Reject("overlay rows/digest changed")
 if not isinstance(overlay["entries"],list) or len(overlay["entries"])!=11 or any(set(row)!={"path","type","mode","identity","category","rationale"} for row in overlay["entries"]): raise Reject("overlay rows malformed")
 proj=report.get("projection"); pkeys={"upstream_tuple_count","upstream_tree_count","upstream_digest","projected_tuple_count","projected_digest","origin_projection","projected_manifest"}
 if not isinstance(proj,Mapping) or set(proj)!=pkeys or type(proj["upstream_tuple_count"]) is not int or proj["upstream_tuple_count"]!=2028 or type(proj["upstream_tree_count"]) is not int or proj["upstream_tree_count"]!=745: raise Reject("projection schema/count changed")
 mappings=proj["origin_projection"]; manifest=proj["projected_manifest"]
 if not isinstance(mappings,list) or len(mappings)!=2028 or not isinstance(manifest,list): raise Reject("projection incomplete")
 projected={row.get("path"):row for row in manifest if isinstance(row,Mapping)}
 if len(projected)!=len(manifest): raise Reject("projected manifest malformed/duplicate")
 origins=[]
 for mapping in mappings:
  if not isinstance(mapping,Mapping) or set(mapping)!={"origin","projected"}: raise Reject("mapping schema changed")
  origins.append(mapping["origin"]); result=mapping["projected"]
  if not isinstance(result,Mapping) or projected.get(result.get("path"))!=result: raise Reject("mapping result not in manifest")
 if rows_digest(origins)!=UP_DIGEST or proj["upstream_digest"]!=UP_DIGEST: raise Reject("upstream digest changed")
 pdigest=rows_digest(manifest)
 if type(proj["projected_tuple_count"]) is not int or proj["projected_tuple_count"]!=len(manifest) or proj["projected_digest"]!=pdigest: raise Reject("projected digest/count changed")
 gradle=report.get("gradle_inputs"); gkeys={"known_inventory","dynamic_inputs","gradle_properties_blob","wrapper_distribution_sha256","wrapper_jar_sha256"}
 if not isinstance(gradle,Mapping) or set(gradle)!=gkeys or digest(gradle["known_inventory"])!=KNOWN_DIGEST or gradle["gradle_properties_blob"]!=PROPS or gradle["wrapper_distribution_sha256"]!=DIST or gradle["wrapper_jar_sha256"]!=JAR: raise Reject("Gradle constants changed")
 dynamic=gradle["dynamic_inputs"]
 if not isinstance(dynamic,Mapping) or set(dynamic)!={"literal_environment_and_properties","static_root_config","unresolved"} or dynamic["unresolved"]!=[]: raise Reject("dynamic inputs unresolved/changed")
 if any(set(x)!={"path","api","name"} for x in dynamic["literal_environment_and_properties"]) or any(set(x)!={"declared_by","path"} for x in dynamic["static_root_config"]): raise Reject("dynamic row changed")
 negative=report.get("negative_tests")
 if not isinstance(negative,Mapping) or set(negative)!={"tuples","gradle_properties","recovery_scope"} or not all_rejected(negative["tuples"],TUPLES) or not all_rejected(negative["gradle_properties"],PROPERTIES) or not all_rejected(negative["recovery_scope"],SCOPE): raise Reject("negative outcomes changed")
 invariants={"one_preflight":{"maximum":1,"observed":1,"run_attempt":1,"head_sha":overlay_sha,"event":"workflow_dispatch","workflow_path":WF_PATH,"workflow_name":WF_NAME},"fresh_identity":{"must_be_created_after_preflight":True,"present":False,"allowed_historical_refs":REFS},"validation_budget":{"maximum_dispatches":3,"used_for_fresh_identity":0,"required_consecutive_successes":2,"run2_failure_stop":True}}
 if report.get("invariants")!=invariants or report["invariants"]["fresh_identity"]["present"] is not False or report["invariants"]["validation_budget"]["run2_failure_stop"] is not True: raise Reject("invariants changed")
 isolation={"sanitized_environment":True,"candidate_workspace":"absent","credential_channels":"absent","runtime_cache_result_channels":"absent","constant_report_path":REPORT_PATH}
 if report.get("isolation")!=isolation or report["isolation"]["sanitized_environment"] is not True: raise Reject("isolation changed")

def read_report():
 path=Path(REPORT_PATH)
 if path.is_symlink() or path.resolve()!=path: raise Reject("report path indirect")
 fd=os.open(REPORT_PATH,os.O_RDONLY|(os.O_NOFOLLOW if hasattr(os,"O_NOFOLLOW") else 0))
 try:
  info=os.fstat(fd)
  if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or not 0<info.st_size<=32*1024*1024 or info.st_mode&0o077: raise Reject("report metadata invalid")
  with os.fdopen(fd,"r",encoding="utf-8") as handle:
   fd=-1
   def unique(pairs):
    value={}
    for key,item in pairs:
     if key in value: raise Reject("duplicate JSON key")
     value[key]=item
    return value
   return json.load(handle,object_pairs_hook=unique)
 finally:
  if fd>=0: os.close(fd)
def self_test():
 validate_environment({"PATH":"/usr/bin","HOME":"/tmp/empty","LANG":"C.UTF-8"})
 try: validate_environment({"PATH":"/usr/bin","GITHUB_TOKEN":"x"})
 except Reject: pass
 else: raise AssertionError("credential accepted")
 rows=[{"path":"a","type":"blob","mode":"100644","identity":"1"*40},{"path":"d","type":"tree","mode":"040000","identity":"2"*40}]
 baseline=rows_digest(rows); changed=json.loads(json.dumps(rows)); changed[0]["identity"]="3"*40
 if baseline==rows_digest(changed): raise AssertionError("digest did not bind identity")
 try: rows_digest(rows+[dict(rows[0])])
 except Reject: pass
 else: raise AssertionError("duplicate accepted")
 if not all_rejected({"a":"rejected"},{"a"}) or all_rejected({"a":"accepted"},{"a"}): raise AssertionError("attack matrix validator failed")
def main():
 parser=argparse.ArgumentParser(); parser.add_argument("--expected-overlay-sha"); parser.add_argument("--self-test",action="store_true"); args=parser.parse_args()
 if args.self_test: self_test(); return
 validate_environment()
 if not args.expected_overlay_sha: parser.error("--expected-overlay-sha required")
 validate(read_report(),args.expected_overlay_sha)
if __name__=="__main__": main()
