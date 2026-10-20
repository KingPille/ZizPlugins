"""Prepare and publish a Dalamud package feed; credentials stay in Git Credential Manager."""
from __future__ import annotations
import argparse
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
MARKER = "<!-- ziz-plugins-distribution -->"
CONFIG = json.loads((ROOT / "distribution.json").read_text(encoding="utf-8"))
OWNER, REPO, BRANCH = CONFIG["owner"], CONFIG["repository"], CONFIG["branch"]
REPOSITORY = f"{OWNER}/{REPO}"
REPO_URL = f"https://github.com/{REPOSITORY}"
RAW_URL = f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}"

def digest(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def prepare(plugin):
    manifest = json.loads((plugin / "ZizBestiarium.json").read_text(encoding="utf-8-sig"))
    name, version = manifest["InternalName"], manifest["AssemblyVersion"]
    if name not in CONFIG["plugins"] or not re.fullmatch(r"\d+\.\d+\.\d+\.\d+", version):
        raise ValueError("Unexpected plugin name or assembly version")
    tag = f"{name}-v{version}"
    short = version[:-2] if version.endswith(".0") else version
    package = plugin / "dist" / f"{name}-{short}.zip"
    payload = package.read_bytes()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        required = {f"{name}.dll", f"{name}.json", "images/icon.png", "Data/fundpunkte.json"}
        if not required.issubset(archive.namelist()):
            raise ValueError("Package is missing plugin files")
        inside = json.loads(archive.read(f"{name}.json"))
        if inside["AssemblyVersion"] != version or inside["DalamudApiLevel"] != manifest["DalamudApiLevel"]:
            raise ValueError("Package and source manifest disagree")
        if archive.read(f"{name}.dll") != (plugin / "bin/Release" / f"{name}.dll").read_bytes():
            raise ValueError("Package DLL is outdated; run Package.ps1 first")
        icon = archive.read("images/icon.png")
    assets = ROOT / "release-assets"
    assets.mkdir(exist_ok=True)
    (assets / package.name).write_bytes(payload)
    sums_name = f"{name}-{version}-SHA256SUMS.txt"
    sums = f"{digest(payload)}  {package.name}\n".encode("utf-8")
    (assets / sums_name).write_bytes(sums)
    entry = dict(manifest)
    link = f"{REPO_URL}/releases/download/{tag}/{package.name}"
    entry.update(RepoUrl=REPO_URL, DownloadLinkInstall=link, DownloadLinkUpdate=link,
                 DownloadLinkTesting=link, IsHide=False, IsTestingExclusive=False,
                 IconUrl=f"{RAW_URL}/icons/{name}.png", LastUpdate=int(time.time()))
    feed = ROOT / "pluginmaster.json"
    entries = json.loads(feed.read_text(encoding="utf-8")) if feed.exists() else []
    write_json(feed, [e for e in entries if e["InternalName"] != name] + [entry])
    icons = ROOT / "icons"
    icons.mkdir(exist_ok=True)
    (icons / f"{name}.png").write_bytes(icon)
    return manifest, tag, {package.name: payload, sums_name: sums}

class GitHub:
    def __init__(self):
        self.token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if self.token:
            return
        environment = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
        result = subprocess.run(["git", "-c", "credential.interactive=false", "credential", "fill"],
                                input=f"protocol=https\nhost=github.com\nusername={OWNER}\n\n",
                                text=True, capture_output=True, env=environment)
        credentials = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        self.token = credentials.get("password", "")
        if result.returncode or not self.token:
            raise RuntimeError("No usable GitHub login in Git Credential Manager. Sign in to GitHub for Git first.")

    def request(self, method, path, data=None, content_type="application/json"):
        url = path if path.startswith("https://") else "https://api.github.com" + path
        if urllib.parse.urlparse(url).hostname not in {"api.github.com", "uploads.github.com"}:
            raise ValueError("Refusing to send credentials outside the GitHub API")
        body = data if isinstance(data, bytes) else json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "ZizPlugins-Publisher", "Content-Type": content_type}
        with urllib.request.urlopen(urllib.request.Request(url, body, headers, method=method), timeout=60) as response:
            raw = response.read()
            return json.loads(raw) if raw else None

def get_or_none(api, path):
    try:
        return api.request("GET", path)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

def commit_feed(api, prefix):
    parent = api.request("GET", f"{prefix}/git/ref/heads/{BRANCH}")["object"]["sha"]
    commit = api.request("GET", f"{prefix}/git/commits/{parent}")
    # Preserve other plugins from the exact branch snapshot being updated.
    remote = get_or_none(api, f"{prefix}/contents/pluginmaster.json?ref={parent}")
    incoming = json.loads((ROOT / "pluginmaster.json").read_text(encoding="utf-8"))
    if remote is not None:
        current = json.loads(base64.b64decode(remote["content"]))
        for entry in incoming:
            previous = next((e for e in current if e["InternalName"] == entry["InternalName"]), None)
            if previous and tuple(map(int, previous["AssemblyVersion"].split("."))) > tuple(map(int, entry["AssemblyVersion"].split("."))):
                raise ValueError("Refusing to downgrade an existing plugin feed entry")
        names = {e["InternalName"] for e in incoming}
        write_json(ROOT / "pluginmaster.json", [e for e in current if e["InternalName"] not in names] + incoming)
    files = ["README.md", "pluginmaster.json", "distribution.json", ".gitignore", "publish.py"]
    files += [p.relative_to(ROOT).as_posix() for p in (ROOT / "icons").glob("*.png")]
    tree = []
    for path in files:
        blob = api.request("POST", f"{prefix}/git/blobs", {
            "content": base64.b64encode((ROOT / path).read_bytes()).decode("ascii"), "encoding": "base64"})
        tree.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
    created = api.request("POST", f"{prefix}/git/trees", {"base_tree": commit["tree"]["sha"], "tree": tree})
    result = api.request("POST", f"{prefix}/git/commits", {
        "message": "Publish ZizBestiarium package feed", "tree": created["sha"], "parents": [parent]})
    api.request("PATCH", f"{prefix}/git/refs/heads/{BRANCH}", {"sha": result["sha"], "force": False})
    return result["sha"]

def publish(manifest, tag, assets):
    api = GitHub()
    if api.request("GET", "/user")["login"].lower() != OWNER.lower():
        raise RuntimeError("GitHub login differs from distribution.json; no changes made")
    prefix = f"/repos/{REPOSITORY}"
    repo = get_or_none(api, prefix)
    if repo is None:
        repo = api.request("POST", "/user/repos", {"name": REPO, "private": False, "auto_init": True,
                           "description": "Plugin-Quelle und Updates für die Ziz-Plugins (Dalamud/ZizLoader)."})
        print("CREATED", repo["html_url"])
        initial = api.request("GET", f"{prefix}/contents/README.md")
        api.request("PUT", f"{prefix}/contents/README.md", {
            "message": "Initialize Ziz plugin distribution",
            "sha": initial["sha"],
            "content": base64.b64encode((ROOT / "README.md").read_bytes()).decode("ascii")})
    else:
        readme = get_or_none(api, f"{prefix}/contents/README.md")
        if readme is None or MARKER not in base64.b64decode(readme["content"]).decode("utf-8"):
            raise RuntimeError("Existing repository has no Ziz distribution marker; no existing files changed")
        if repo["private"]:
            raise RuntimeError("Feed requires anonymous access; refusing to change repository visibility")
    if repo["default_branch"] != BRANCH:
        old = api.request("GET", f"{prefix}/git/ref/heads/{repo['default_branch']}")
        if get_or_none(api, f"{prefix}/git/ref/heads/{BRANCH}") is None:
            api.request("POST", f"{prefix}/git/refs", {"ref": f"refs/heads/{BRANCH}", "sha": old["object"]["sha"]})
        api.request("PATCH", prefix, {"default_branch": BRANCH})
    release = get_or_none(api, f"{prefix}/releases/tags/{tag}")
    if release is None:
        release = next((r for r in api.request("GET", f"{prefix}/releases?per_page=100") if r["tag_name"] == tag), None)
    if release is None:
        release = api.request("POST", f"{prefix}/releases", {
            "tag_name": tag, "target_commitish": BRANCH, "name": f"ZizBestiarium {manifest['AssemblyVersion']} - Testversion",
            "draft": True, "prerelease": True,
            "body": "Installation über die Paketquelle im README. DLL, Manifest, Icon und Fundpunkte enthalten. "
                    "Dalamud API 15 / .NET 10 / Windows x64. Autopilot im laufenden Spiel noch nicht validiert. "
                    "ZizNav/vnavmesh erforderlich; Instanzen benötigen ZizDuty und passende Freischaltungen/Gruppe. "
                    "22 lokale Prüfungen bestanden; Release-Build ohne Fehler und Warnungen."})
    for name, content in assets.items():
        existing = next((a for a in release["assets"] if a["name"] == name), None)
        if existing:
            if existing.get("digest") != "sha256:" + digest(content):
                raise RuntimeError(f"Release asset {name} differs or cannot be verified; increase the plugin version")
            continue
        if not release["draft"]:
            raise RuntimeError("Published release is incomplete; refusing to modify its assets")
        upload = release["upload_url"].split("{")[0] + "?name=" + urllib.parse.quote(name)
        asset = api.request("POST", upload, content, "application/zip" if name.endswith(".zip") else "text/plain")
        if asset.get("digest") and asset["digest"] != "sha256:" + digest(content):
            raise RuntimeError("GitHub digest differs from the local package")
        print("UPLOADED", name, len(content), digest(content))
    if release["draft"]:
        api.request("PATCH", f"{prefix}/releases/{release['id']}", {"draft": False, "prerelease": True})
    for name, content in assets.items():
        url = f"{REPO_URL}/releases/download/{tag}/{urllib.parse.quote(name)}"
        with urllib.request.urlopen(url, timeout=60) as response:
            if digest(response.read()) != digest(content):
                raise RuntimeError("Anonymous download differs from the local package")
        print("VERIFIED anonymous download", name)
    print("PUBLISHED", REPO_URL, "commit", commit_feed(api, prefix))
    print("FEED", RAW_URL + "/pluginmaster.json")

def verify_feed():
    expected = json.loads((ROOT / "pluginmaster.json").read_text(encoding="utf-8"))
    url = RAW_URL + "/pluginmaster.json"
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url + f"?verify={int(time.time())}", timeout=30) as response:
                remote = json.loads(response.read())
            if remote != expected:
                raise ValueError("Feed is cached or differs from the local index")
            for entry in remote:
                if not isinstance(entry["LastUpdate"], int) or not entry["DownloadLinkInstall"].startswith(REPO_URL + "/releases/download/"):
                    raise ValueError("Invalid repository manifest")
                with urllib.request.urlopen(entry["IconUrl"], timeout=30) as response:
                    if not response.read().startswith(b"\x89PNG\r\n\x1a\n"):
                        raise ValueError("Icon is not a PNG")
            print("VERIFIED anonymous feed and icons", url)
            return
        except (urllib.error.URLError, ValueError):
            if attempt == 4:
                raise
            time.sleep(3)

def verify_local():
    entries = json.loads((ROOT / "pluginmaster.json").read_text(encoding="utf-8"))
    if not isinstance(entries, list) or not entries:
        raise ValueError("Feed must be a nonempty array")
    if len({e["InternalName"] for e in entries}) != len(entries):
        raise ValueError("Duplicate plugin entries")
    for entry in entries:
        url = entry["DownloadLinkInstall"]
        if not url.startswith(REPO_URL + "/releases/download/") or url != entry["DownloadLinkUpdate"]:
            raise ValueError("Invalid download links")
        if not isinstance(entry["DalamudApiLevel"], int) or not isinstance(entry["LastUpdate"], int):
            raise ValueError("API level and update timestamp must be integers")
        archive_path = ROOT / "release-assets" / urllib.parse.urlparse(url).path.rsplit("/", 1)[1]
        with zipfile.ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("Corrupt ZIP entry")
            manifest = json.loads(archive.read(entry["InternalName"] + ".json"))
            if manifest["AssemblyVersion"] != entry["AssemblyVersion"] or manifest["DalamudApiLevel"] != entry["DalamudApiLevel"]:
                raise ValueError("Feed and ZIP manifest disagree")
            forbidden = [n for n in archive.namelist() if n.startswith(("/", "\\")) or ".." in n.split("/") or
                         n.lower().endswith(("fortschritt.json", ".bak", ".unlesbar"))]
            if forbidden:
                raise ValueError("Unexpected personal files or invalid paths in ZIP")
        checksum = ROOT / "release-assets" / f"{entry['InternalName']}-{entry['AssemblyVersion']}-SHA256SUMS.txt"
        expected = f"{digest(archive_path.read_bytes())}  {archive_path.name}\n"
        if checksum.read_text(encoding="utf-8") != expected:
            raise ValueError("Package checksum file differs")
        print("VERIFIED local ZIP, CRC, manifest, feed links and checksum", archive_path.name)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugin-dir", type=Path, default=ROOT.parent / "ZizBestiarium")
    parser.add_argument("--check-auth", action="store_true")
    parser.add_argument("--publish", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--verify-local", action="store_true")
    args = parser.parse_args()
    if args.verify_local:
        verify_local()
        return
    if args.check_auth:
        api = GitHub()
        print("AUTHENTICATED", api.request("GET", "/user")["login"])
        print("REPOSITORY", "exists" if get_or_none(api, f"/repos/{REPOSITORY}") else "available", REPO_URL)
        return
    if args.verify:
        verify_feed()
        return
    manifest, tag, assets = prepare(args.plugin_dir.resolve())
    verify_local()
    print("PREPARED", tag, "assets", ", ".join(assets))
    if args.publish:
        publish(manifest, tag, assets)
        verify_feed()

if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as error:
        print(f"GitHub/HTTP request failed: HTTP {error.code} ({error.reason})", file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(f"Publish failed: {error}", file=sys.stderr)
        sys.exit(1)
