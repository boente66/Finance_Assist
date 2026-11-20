"""Publish verified artifacts to the existing test.17 prerelease without moving its tag."""
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import zipfile

REPO = "boente66/Finance_Assist"
TAG = "rebuild-v2.1.0-test.17-20261107"
SHA = os.environ["SOURCE_SHA"]
SUFFIX = os.environ["ASSET_SUFFIX"]
RUNS = {"multiplatform": int(os.environ["MULTIPLATFORM_RUN"]),
        "ubuntu24": int(os.environ["UBUNTU24_RUN"])}
FULL_PASSED = int(os.environ["FULL_PASSED"])
FOCUSED_PASSED = int(os.environ["FOCUSED_PASSED"])
assert re.fullmatch(r"[0-9a-f]{40}", SHA)
assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,79}", SUFFIX)
assert FULL_PASSED > 0 and FOCUSED_PASSED > 0 and all(value > 0 for value in RUNS.values())


def gh(*args):
    return subprocess.check_output(["gh", *map(str, args)], text=True)


def api(path):
    return json.loads(gh("api", f"repos/{REPO}/{path}"))


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    root = Path(os.environ["RUNNER_TEMP"]) / SUFFIX
    incoming, outgoing = root / "artifacts", root / "publish"
    outgoing.mkdir(parents=True, exist_ok=True)
    for run_id in RUNS.values():
        run = api(f"actions/runs/{run_id}")
        assert run["head_sha"] == SHA and run["conclusion"] == "success", run_id
        jobs = api(f"actions/runs/{run_id}/jobs?per_page=100")["jobs"]
        assert jobs and all(job["conclusion"] == "success" for job in jobs), run_id
    release = api(f"releases/tags/{TAG}")
    assert release["prerelease"] and not release["draft"]
    original_ref = api(f"git/ref/tags/{TAG}")["object"]
    artifacts = {
        "finance-assist-linux-ubuntu-22.04-amd64": RUNS["multiplatform"],
        "finance-assist-windows-x64": RUNS["multiplatform"],
        "finance-assist-macos-arm64": RUNS["multiplatform"],
        "finance-assist-macos-x64": RUNS["multiplatform"],
        "finance-assist-ubuntu24.04-amd64": RUNS["ubuntu24"],
    }
    for name, run_id in artifacts.items():
        gh("run", "download", run_id, "--repo", REPO, "--name", name,
           "--dir", incoming / name)
    packages = sorted(path for path in incoming.rglob("*")
                      if path.suffix in {".deb", ".zip"})
    assert len(packages) == 5, packages
    records = []
    for source in packages:
        expected = Path(str(source) + ".sha256").read_text().split()[0]
        actual = digest(source)
        assert actual == expected, source
        target = outgoing / f"{source.stem}_{SUFFIX}{source.suffix}"
        target.hardlink_to(source)
        if source.suffix == ".zip":
            with zipfile.ZipFile(source) as archive:
                assert archive.testzip() is None, source
                if "windows-x64" in source.name:
                    entries = [name for name in archive.namelist() if name.endswith(".exe")]
                    assert len(entries) == 1, entries
                    executable = outgoing / f"FinanceAssist-test.17-{SUFFIX}-windows-x64.exe"
                    with archive.open(entries[0]) as inp, executable.open("wb") as out:
                        import shutil
                        shutil.copyfileobj(inp, out)
                    records.append({"name": executable.name, "size": executable.stat().st_size,
                                    "sha256": digest(executable)})
        else:
            version = subprocess.check_output(
                ["dpkg-deb", "-f", str(source), "Version"], text=True).strip()
            assert version in {"2.1.0~test17", "2.1.0~test17+ubuntu24.04.1"}, version
        records.append({"name": target.name, "size": target.stat().st_size, "sha256": actual})
    assert len(records) == 6
    reports = list(incoming.rglob("views-*.json"))
    assert len(reports) >= 5, reports
    for report in reports:
        assert json.loads(report.read_text())["ok"], report
    for record in records:
        (outgoing / (record["name"] + ".sha256")).write_text(
            f"{record['sha256']}  {record['name']}\n")
    manifest = {"version": "2.1.0-test.17", "source_commit": SHA, "release_tag": TAG,
                "workflows": RUNS,
                "validation": {"full_suite_passed": FULL_PASSED, "focused_passed": FOCUSED_PASSED,
                               "ci_jobs_passed": 14}, "assets": records}
    (outgoing / f"{SUFFIX}-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    known = {item["name"]: item for item in release["assets"]}
    expected_files = {path.name: {"size": path.stat().st_size, "sha256": digest(path)}
                      for path in outgoing.iterdir()}

    def upload(path):
        previous = known.get(path.name)
        expected = expected_files[path.name]
        if previous:
            if previous["state"] == "starter" and previous["size"] == 0:
                gh("api", "--method", "DELETE",
                   f"repos/{REPO}/releases/assets/{previous['id']}")
            else:
                assert previous["size"] == expected["size"], path.name
                assert previous.get("digest") == "sha256:" + expected["sha256"], path.name
                return
        gh("release", "upload", TAG, path, "--repo", REPO)

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(upload, sorted(outgoing.iterdir())))
    remote = {item["name"]: item for item in api(f"releases/{release['id']}/assets?per_page=100")}
    verification = []
    for name, expected in expected_files.items():
        item = remote[name]
        assert item["state"] == "uploaded" and item["size"] == expected["size"], name
        assert item["digest"] == "sha256:" + expected["sha256"], name
        verification.append({"name": name, **expected, "url": item["browser_download_url"]})
    assert len(verification) == 13
    assert api(f"git/ref/tags/{TAG}")["object"] == original_ref
    (root / "verification.json").write_text(json.dumps(verification, indent=2) + "\n")
    print(f"{len(verification)}/13 arquivos publicados e verificados; tag preservada.")


if __name__ == "__main__":
    main()
