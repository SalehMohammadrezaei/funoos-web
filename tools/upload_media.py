"""Upload the clips of the finished runs as assets of a GitHub release.

    python tools/upload_media.py <runs directory> <tag> <token file>

Creates the release (tag on the current default branch) if it does not exist, then uploads
every <case>__<view>.mp4 that is not already an asset. Restartable.
"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cases  # noqa: E402

OWNER, REPO = "SalehMohammadrezaei", "funoos-web"


def api(tok, path, data=None, method=None, raw=None, ctype="application/json", host="https://api.github.com"):
    body = raw if raw is not None else (json.dumps(data).encode() if data is not None else None)
    r = urllib.request.Request(host + path, data=body, method=method or ("POST" if body is not None else "GET"),
                               headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json", "Content-Type": ctype})
    with urllib.request.urlopen(r, timeout=600) as f:
        return json.load(f) if f.headers.get("Content-Type", "").startswith("application/json") else f.read()


def main(runs, tag, tokfile):
    tok = Path(tokfile).read_text().strip()
    try:
        rel = api(tok, f"/repos/{OWNER}/{REPO}/releases/tags/{tag}")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        rel = api(tok, f"/repos/{OWNER}/{REPO}/releases", {"tag_name": tag, "name": f"Clips of the pre-run library ({tag})",
                  "body": "H.264 clips of every view of every case of the Funoos web version. The site loads them from here.",
                  "draft": False, "prerelease": False})
    def assets():
        """name -> (id, size, state) of every asset of the release, all pages."""
        out, page = {}, 1
        while True:
            more = api(tok, f"/repos/{OWNER}/{REPO}/releases/{rel['id']}/assets?per_page=100&page={page}")
            out.update({a["name"]: (a["id"], a["size"], a["state"]) for a in more})
            if len(more) < 100:
                return out
            page += 1

    have = assets()
    upload = rel["upload_url"].split("{")[0]
    lib = {c["id"] for c in cases.build()}                         # only the current library, not retired runs
    files = []
    for m in sorted(Path(runs).glob("*/meta.json")):
        d = json.loads(m.read_text())
        if not d.get("ok") or d["case"]["id"] not in lib:
            continue
        for v in d["views"]:
            files.append((m.parent / v["mp4"], f"{d['case']['id']}__{Path(v['mp4']).stem}.mp4"))
    ok = lambda p, n: n in have and have[n][1] == p.stat().st_size and have[n][2] == "uploaded"  # noqa: E731
    todo = [(p, n) for p, n in files if not ok(p, n)]
    print(f"{len(files)} clips, {len(todo)} to upload, {sum(p.stat().st_size for p, _ in todo) / 1e6:.0f} MB", flush=True)
    failed = []
    for i, (p, name) in enumerate(todo, 1):
        for attempt in range(4):
            if name in have:                                       # changed clip, or a broken earlier attempt
                try:
                    api(tok, f"/repos/{OWNER}/{REPO}/releases/assets/{have.pop(name)[0]}", method="DELETE")
                except urllib.error.HTTPError as e:
                    if e.code != 404:
                        raise
            try:
                api(tok, f"?name={name}", raw=p.read_bytes(), ctype="video/mp4", host=upload); break
            except Exception as e:                                 # noqa: BLE001
                print("  retry", name, e, flush=True); time.sleep(5 * (attempt + 1))
                have = assets()                                    # a failed upload can leave a partial asset behind
        else:
            failed.append(name)
        if i % 25 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)} done", flush=True)
    have = assets()
    missing = [n for p, n in files if not ok(p, n)]
    print("release:", rel["html_url"])
    print(f"{len(files) - len(missing)} of {len(files)} clips in the release" + (f"; missing: {missing}" if missing else ""))
    return 1 if missing or failed else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:4]))
