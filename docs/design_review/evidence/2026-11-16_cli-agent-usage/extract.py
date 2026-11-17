#!/usr/bin/env python3
"""Extract command-usage statistics from Codex rollout logs (stdlib only).

Usage: python3 extract.py [--sessions-root ~/.codex/sessions/2026/11] [--days 14 15 16]
                          [--cwd /home/paul/corpus-structure] [--out DIR]

Writes aggregated JSON/CSV/Markdown into --out (default: this script's folder). No transcript text is
stored beyond short (<=200 char) command examples; likely secrets are masked.
"""

from __future__ import annotations

import argparse
import collections
import csv
import json
import re
import shlex
import statistics
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPLAY_WINDOW = __import__("datetime").timedelta(seconds=0.5)
DEC = json.JSONDecoder()
SECRET = re.compile(
    r"(?i)(password|passwd|secret|token|apikey|api_key|authorization|bearer)\s*[=:]\s*\S+|sk-[A-Za-z0-9]{16,}|postgres(?:ql)?://[^\s'\"]*:[^\s'\"@]*@"
)


def mask(s: str, n: int = 200) -> str:
    s = " ".join(s.split())
    s = SECRET.sub("<masked>", s)
    return s[:n]


# ----------------------------------------------------------------------------- JS input parsing
CMD_KEY = re.compile(r"""["']?cmd["']?\s*:\s*(?=["'`])""")


def read_js_string(src: str, i: int):
    q = src[i]
    j = i + 1
    buf = []
    while j < len(src):
        c = src[j]
        if c == "\\" and j + 1 < len(src):
            buf.append(src[j : j + 2])
            j += 2
            continue
        if c == q:
            break
        buf.append(c)
        j += 1
    raw = "".join(buf)
    try:
        if q == '"':
            return json.loads('"' + raw.replace("\\'", "'") + '"'), j + 1
        out, k = [], 0
        esc = {"n": "\n", "t": "\t", "\\": "\\", "'": "'", '"': '"', "`": "`", "$": "$", "r": "\r"}
        while k < len(raw):
            if raw[k] == "\\" and k + 1 < len(raw):
                nxt = raw[k + 1]
                if nxt == "u" and k + 5 < len(raw):
                    out.append(chr(int(raw[k + 2 : k + 6], 16)))
                    k += 6
                    continue
                out.append(esc.get(nxt, nxt))
                k += 2
            else:
                out.append(raw[k])
                k += 1
        return "".join(out), j + 1
    except Exception:
        return None, j + 1


def parse_exec_calls(js: str):
    """Return dicts {cmd, workdir, max_tokens} for each exec_command call in a JS snippet."""
    calls = []
    for m in re.finditer(r"tools\.exec_command\(", js):
        seg_start = m.end()
        km = CMD_KEY.search(js, seg_start, seg_start + 60)
        if not km:
            calls.append({"cmd": None, "workdir": None, "max_tokens": None})
            continue
        cmd, end = read_js_string(js, km.end())
        tail = js[end : end + 400]
        wd = re.search(r"""["']?workdir["']?\s*:\s*["']([^"']+)["']""", tail)
        mt = re.search(r"""["']?max_output_tokens["']?\s*:\s*(\d+)""", tail)
        calls.append(
            {"cmd": cmd, "workdir": wd.group(1) if wd else None, "max_tokens": int(mt.group(1)) if mt else None}
        )
    return calls


RESULT_RE = re.compile(
    r'(?<!\\)"chunk_id":"(\w+)","wall_time_seconds":([0-9.e+-]+)(?:,"exit_code":(-?\d+|null))?(?:,"session_id":(\d+))?,"original_token_count":(\d+),"output":'
)


def parse_results(blob: str):
    res = []
    for m in RESULT_RE.finditer(blob):
        try:
            out, _ = DEC.raw_decode(blob, m.end())
        except Exception:
            out = None
        res.append(
            {
                "wall": float(m.group(2)),
                "exit": None if m.group(3) in (None, "null") else int(m.group(3)),
                "poll_session": int(m.group(4)) if m.group(4) else None,
                "orig_tokens": int(m.group(5)),
                "out": out,
            }
        )
    return res


# ----------------------------------------------------------------------------- shell classification
TRIVIAL = {"cd", "pushd", "popd", "export", "set", "source", ".", "echo", "printf", "pwd", "true", "false", ":", "unset", "test", "["}
READERS = {"sed", "cat", "head", "tail", "nl", "less", "more", "bat", "awk"}
FS = {"ls", "find", "wc", "tree", "fd", "stat", "du", "file", "realpath", "dirname", "basename", "readlink", "which", "sort", "uniq", "cut", "xargs", "tr", "diff", "comm"}


def split_statements(cmd: str):
    """Split a shell string into statements -> list of (stages: list[str], heredoc_body)."""
    stmts, stages, cur = [], [], []
    i, n = 0, len(cmd)
    q = None
    pending = []
    heredocs = []

    def flush_stage():
        s = "".join(cur).strip()
        cur.clear()
        if s:
            stages.append(s)

    def flush_stmt():
        nonlocal stages, heredocs
        flush_stage()
        if stages:
            stmts.append((stages, "\n".join(heredocs)))
        stages, heredocs = [], []

    while i < n:
        c = cmd[i]
        if q:
            cur.append(c)
            if c == "\\" and q == '"' and i + 1 < n:
                cur.append(cmd[i + 1])
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c in "'\"":
            q = c
            cur.append(c)
            i += 1
            continue
        if c == "\\" and i + 1 < n:
            cur.append(cmd[i : i + 2])
            i += 2
            continue
        if cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            m = re.match(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", cmd[i:])
            if m:
                pending.append(m.group(2))
                cur.append(m.group(0))
                i += len(m.group(0))
                continue
        if c == "\n":
            if pending:
                lines = []
                i += 1
                term = pending.pop(0)
                while i < n:
                    e = cmd.find("\n", i)
                    e = n if e < 0 else e
                    line = cmd[i:e]
                    i = e + 1
                    if line.strip() == term:
                        break
                    lines.append(line)
                heredocs.append("\n".join(lines))
                continue
            flush_stmt()
            i += 1
            continue
        if cmd.startswith("&&", i) or cmd.startswith("||", i):
            flush_stmt()
            i += 2
            continue
        if c == ";":
            flush_stmt()
            i += 1
            continue
        if c == "|":
            flush_stage()
            i += 1
            continue
        cur.append(c)
        i += 1
    flush_stmt()
    return stmts


def toks(s: str):
    try:
        return shlex.split(s, posix=True)
    except ValueError:
        return s.split()


UV_VAL_OPTS = {"--project", "--with", "--python", "-p", "--directory", "--group", "--extra", "--env-file", "--with-requirements", "--package"}
ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def unwrap(t, depth=0):
    while t:
        w = t[0]
        if ASSIGN.match(w):
            t = t[1:]
            continue
        base = w.rsplit("/", 1)[-1]
        if base in {"env", "time", "nice", "command", "stdbuf", "nohup", "ionice", "sudo"}:
            t = t[1:]
            while t and (t[0].startswith("-") or ASSIGN.match(t[0])):
                t = t[1:]
            continue
        if base == "timeout":
            t = t[1:]
            while t and t[0].startswith("-"):
                t = t[1:]
            if t:
                t = t[1:]
            continue
        if base == "direnv" and len(t) > 2 and t[1] == "exec":
            t = t[3:]
            continue
        if base == "uv" and len(t) > 1 and t[1] == "run":
            t = t[2:]
            while t and t[0].startswith("-"):
                if t[0] in UV_VAL_OPTS and "=" not in t[0]:
                    t = t[2:]
                else:
                    t = t[1:]
            continue
        if base in {"bash", "sh", "zsh"} and depth < 2:
            for k, x in enumerate(t):
                if x in ("-c", "-lc", "-ic", "-lic", "-ec") and k + 1 < len(t):
                    return ("__recurse__", t[k + 1])
            return t
        break
    return t


def classify_stage(stage: str, body: str = "", depth=0):
    t = unwrap(toks(stage), depth)
    if isinstance(t, tuple):
        for stages, hb in split_statements(t[1]):
            c = classify_stage(stages[0], hb, depth + 1)
            if c["cls"] != "trivial":
                return c
        return {"cls": "trivial", "key": "trivial", "opts": [], "tokens": []}
    if not t:
        return {"cls": "trivial", "key": "trivial", "opts": [], "tokens": []}
    w = t[0].rsplit("/", 1)[-1]
    opts = [x.split("=")[0] for x in t[1:] if x.startswith("-")]

    def r(cls, key=None):
        return {"cls": cls, "key": key or cls, "opts": opts, "tokens": t}

    if w in TRIVIAL:
        return r("trivial")
    if w == "ci":
        words = []
        for x in t[1:]:
            if x == "--":
                break
            if x.startswith("-"):
                continue
            if re.match(r"^[a-z][a-z0-9-]*$", x) and len(words) < 2:
                words.append(x)
            else:
                break
        return r("ci", "ci " + " ".join(words) if words else "ci")
    if w == "just":
        rec = next((x for x in t[1:] if not x.startswith("-")), "")
        return r("just", f"just {rec}")
    if w in {"rg", "grep", "egrep", "fgrep", "ag", "ack"}:
        if "--files" in t:
            return r("rg-files", "rg --files")
        return r("rg", w)
    if w == "git":
        sub = next((x for x in t[1:] if not x.startswith("-")), "")
        return r("git", f"git {sub}")
    if w == "sed" and any(x.startswith("-") and not x.startswith("--") and "i" in x for x in t[1:]):
        return r("sed-i", "sed -i")
    if w == "perl" and any(x.startswith("-") and ("pi" in x or x.startswith("-i")) for x in t[1:]):
        return r("perl-i", "perl -pi")
    if w in READERS:
        return r("read", w)
    if w in FS:
        return r("fs", w)
    if re.match(r"^python3?(\.\d+)?$", w):
        if "-m" in t:
            mod = t[t.index("-m") + 1] if t.index("-m") + 1 < len(t) else ""
            if mod in ("pytest", "ruff", "pyrefly", "ty"):
                return r(mod, mod)
            return r("python-module", f"python -m {mod}")
        if "-c" in t or "-" in t[1:2] or body or len(t) == 1:
            return r("python-inline", "python inline")
        return r("python-script", "python script")
    if w in {"pytest", "ruff", "pyrefly", "ty", "psql", "jq", "pg_dump", "pg_restore", "alembic"}:
        return r(w)
    if w == "cargo":
        sub = next((x for x in t[1:] if not x.startswith("-") and not x.startswith("+")), "")
        return r("cargo", f"cargo {sub}")
    if w in {"ast-grep", "sg"}:
        return r("ast-grep")
    if w == "apply_patch":
        return r("apply_patch-shell")
    if w == "tee":
        return r("read")
    return r("other", w)


def analyse_cmd(cmd: str):
    items = []
    for stages, body in split_statements(cmd):
        for si, st in enumerate(stages):
            c = classify_stage(st, body if si == 0 else "")
            c["stage"] = si
            c["body"] = body if si == 0 else ""
            c["text"] = st
            items.append(c)
    subst = [c for c in items if c["cls"] != "trivial"]
    primary = next((c for c in subst if c["stage"] == 0), subst[0] if subst else None)
    return items, subst, primary


# ----------------------------------------------------------------------------- feature regexes
REDIR = re.compile(r"(?:(?<![0-9&<-])>>?|&>>?|\btee(?:\s+-a)?)\s*(?P<p>[^\s|&;<>()'\"`]+|\"[^\"]+\"|'[^']+')")
HEX32 = re.compile(r"\b[0-9a-f]{32}\b")
USAGE = re.compile(r"(No such option|No such command|Missing argument|Missing option|Got unexpected extra|Invalid value for|\brefused:|^Usage: ci|\nUsage: ci)")
ENVERR = {
    "lock_wait": re.compile(r"(?i)(waiting for (file )?lock|lock contention|database is locked|could not obtain lock|Blocking waiting for file lock|already running)"),
    "module_or_cmd_missing": re.compile(r"(ModuleNotFoundError|command not found|ImportError)"),
    "stale_lock": re.compile(r"(?i)(lockfile .* needs to be updated|lock file .* out of date)"),
    "timeout": re.compile(r"(?i)(timed out|TimeoutError)"),
    "db_conn": re.compile(r"(?i)(connection refused|could not connect|password authentication failed|role .* does not exist|server closed the connection)"),
    "permission_or_disk": re.compile(r"(?i)(permission denied|no space left|read-only file system)"),
    "sandbox": re.compile(r"(?i)(operation not permitted|sandbox)"),
}
PATH_RE = re.compile(r"[\w.-]+\.(?:md|toml|py|rs|json|sql|yml|yaml|txt|rst|cfg|sh)$")


def read_paths(items):
    out = []
    for c in items:
        if c["cls"] == "read" and c["tokens"] and c["key"] != "tee":
            args = [x for x in c["tokens"][1:] if not x.startswith("-")]
            if c["key"] in ("sed", "awk"):
                args = args[1:]
            if c["key"] in ("head", "tail"):
                args = [x for x in args if not x.isdigit()]
            for a in args:
                if re.match(r"^\d*>", a) or a.startswith("&"):
                    continue
                if PATH_RE.search(a) or "/" in a:
                    out.append(a[2:] if a.startswith("./") else a)
    return out


def rg_pattern(c):
    t = c["tokens"]
    skip_val = {"-g", "--glob", "-t", "--type", "-A", "-B", "-C", "-m", "--max-count", "-f", "-j", "--max-depth", "-T", "--type-not", "-d", "--include", "--exclude"}
    k = 1
    while k < len(t):
        x = t[k]
        if x in ("-e", "--regexp") and k + 1 < len(t):
            return t[k + 1]
        if x in skip_val and k + 1 < len(t):
            k += 2
            continue
        if x.startswith("-"):
            k += 1
            continue
        return x
    return ""


IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*$")


def classify_pattern(p: str):
    """Pattern shape. 'def_anchor' = any alternative anchored with def/class/fn/struct/impl."""
    if not p:
        return "none"
    if re.search(r"(^|[|(\s^\\])(def|class|fn|struct|enum|impl|trait|pub fn|async def)\s", p) or re.search(r"\b(def|class|fn)\\s", p):
        return "def_anchor"
    if re.search(r"\b(import|from)\s", p):
        return "import"
    if IDENT.match(p):
        return "bare_identifier"
    alts = [a.strip("()\\b ") for a in re.split(r"\\?\|", p) if a]
    if len(alts) > 1 and all(IDENT.match(a) for a in alts):
        return "identifier_alternation"
    if re.match(r"^[#^\\]*#", p):
        return "heading"
    if re.search(r"[A-Za-z_]+_[a-z_]+|[a-z][A-Z][a-z]|[A-Z][a-z]+[A-Z]", p) and not re.search(r"[A-Za-z]{3,}\s[A-Za-z]{3,}", p):
        return "identifier_like_mixed"
    return "other_regex_or_prose"


def rg_scope(c):
    t = c["tokens"]
    paths = [x for x in t[2:] if not x.startswith("-") and ("/" in x or x.endswith((".md", ".py", ".rs", ".toml")))]
    if not paths:
        return "unscoped(cwd)"
    kinds = set()
    for x in paths:
        if x.startswith(("docs", "STATUS", "AGENTS", ".agents", ".claude")) or x.endswith(".md"):
            kinds.add("docs")
        elif "/tests" in x or x.startswith("tests"):
            kinds.add("tests")
        elif x.startswith(("python", "crates", "src")) or x.endswith((".py", ".rs", ".sql", ".yaml")):
            kinds.add("src")
        else:
            kinds.add("other")
    return "+".join(sorted(kinds))


RX = {
    "receipt_or_ci_output": re.compile(r"(build/ci|reportlog|report-log|junit|receipt|ci results|ci test|--json|json\.load\(sys\.stdin|failures)", re.I),
    "code_intel": re.compile(r"(\bimport ast\b|ast\.parse|ast\.walk|libcst|griffe|astroid|inspect\.|importlib|rglob\(['\"]\*\.(py|rs)|os\.walk|glob\(['\"].*\.py|tree_sitter)"),
    "database": re.compile(r"(psycopg|sqlalchemy|create_engine|\bpsql\b|\bSELECT\b.*\bFROM\b|information_schema|pg_catalog|asyncpg)", re.I | re.S),
    "file_rewrite": re.compile(r"(write_text\(|open\([^)]*['\"]w['\"]|\.replace\(|re\.sub\(|re\.subn\()"),
    "docs_or_text": re.compile(r"(\.md['\"]|docs/|read_text\(|splitlines|STATUS)", re.I),
}


def inline_primary(text):
    tags = [k for k, rx in RX.items() if rx.search(text)]
    for k in ("code_intel", "receipt_or_ci_output", "database", "file_rewrite", "docs_or_text"):
        if k in tags:
            return k, tags
    return "other", tags


def tsd(x):
    return datetime.fromisoformat(x.replace("Z", "+00:00")) if x else None


# ----------------------------------------------------------------------------- log loading
def load_session(path: Path):
    meta = None
    execs, polls, patches = [], [], []
    fcalls = collections.Counter()
    calls = {}
    callpolls = {}
    with path.open() as fh:
        for line in fh:
            if meta is None and '"session_meta"' in line[:150]:
                p = json.loads(line)["payload"]
                meta = {
                    "cwd": p.get("cwd"),
                    "role": p.get("agent_role") or ("root" if p.get("thread_source") == "user" else None),
                    "thread_source": p.get("thread_source"),
                    "nickname": p.get("agent_nickname"),
                    "start": p.get("timestamp"),
                }
                continue
            if '"custom_tool_call' not in line and '"function_call"' not in line:
                continue
            d = json.loads(line)
            # Forked sessions replay inherited parent history stamped within ~0.5 s of the session start; skip it.
            if meta and tsd(d.get("timestamp")) - tsd(meta["start"]) < REPLAY_WINDOW:
                continue
            p = d.get("payload", {})
            ts = d.get("timestamp")
            t = p.get("type")
            if t == "function_call":
                fcalls[p.get("name")] += 1
            elif t == "custom_tool_call":
                js = p.get("input", "")
                cid = p.get("call_id")
                recs = []
                ec = parse_exec_calls(js)
                for c in ec:
                    rec = {"cmd": c["cmd"], "workdir": c["workdir"], "max_tokens": c["max_tokens"], "ts": ts, "call_id": cid}
                    execs.append(rec)
                    recs.append(rec)
                for m in re.finditer(r'tools\.apply_patch\(("(?:[^"\\]|\\.)*")', js):
                    try:
                        patches.append({"ts": ts, "patch": json.loads(m.group(1))})
                    except Exception:
                        pass
                pr = []
                for m in re.finditer(r"tools\.write_stdin\(\{\s*[\"']?session_id[\"']?\s*:\s*(\d+)", js):
                    pd = {"ts": ts, "session": int(m.group(1))}
                    polls.append(pd)
                    pr.append(pd)
                callpolls[cid] = pr
                calls[cid] = recs
            elif t == "custom_tool_call_output":
                recs = calls.get(p.get("call_id"))
                if recs is None:
                    continue
                o = p.get("output")
                items = o if isinstance(o, list) else [{"text": o}]
                texts = [it.get("text", "") for it in items if isinstance(it, dict)]
                blob = "\n".join(texts[1:]) if len(texts) > 1 else (texts[0] if texts else "")
                top_trunc = "Warning: truncated output" in blob[:200]
                res = parse_results(blob)
                pr = callpolls.get(p.get("call_id")) or []
                if pr and not recs and len(res) == len(pr):
                    for pd, rr in zip(pr, res):
                        pd.update({"out_ts": ts, "exit": rr["exit"], "orig_tokens": rr["orig_tokens"], "wall": rr["wall"]})
                for rec in recs:
                    rec["out_ts"] = ts
                    rec["script_trunc"] = top_trunc
                if len(res) == len(recs) and recs:
                    pairs = list(zip(recs, res))
                elif len(recs) == 1 and res:
                    pairs = [(recs[0], res[0])]
                else:
                    pairs = []
                for rec, rr in pairs:
                    rec.update({"exit": rr["exit"], "poll_session": rr["poll_session"], "orig_tokens": rr["orig_tokens"], "wall": rr["wall"]})
                    out = rr["out"]
                    rec["out_bytes"] = len(out.encode("utf-8", "replace")) if out is not None else None
                    if out:
                        rec["usage_err"] = bool(USAGE.search(out))
                        rec["env"] = [k for k, rx in ENVERR.items() if rx.search(out)]
                        rec["result_ids"] = HEX32.findall(out)[:3]
                        rec["head"] = out[:300]
                        rec["trunc_marker"] = out.startswith("Warning: truncated output")
                        rec["out_paths"] = sorted(set(re.findall(r"(?m)^([\w./@+-]+\.\w{1,5}):\d+[:-]", out)))[:60]
    return meta, execs, polls, patches, fcalls


# ----------------------------------------------------------------------------- analysis helpers
def pct(xs, q):
    if not xs:
        return 0
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def dist(xs):
    return {"n": len(xs), "sum": sum(xs), "median": statistics.median(xs) if xs else 0, "p90": pct(xs, 0.9), "p99": pct(xs, 0.99), "max": max(xs) if xs else 0}


def norm_cmd(cmd: str):
    s = re.sub(r"^\s*cd\s+\S+\s*&&\s*", "", cmd.strip())
    s = re.sub(r"\b[0-9a-f]{12,40}\b", "<ID>", s)
    return re.sub(r"\s+", " ", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sessions-root", default=str(Path.home() / ".codex/sessions/2026/11"))
    ap.add_argument("--days", nargs="*", default=["14", "15", "16"])
    ap.add_argument("--cwd", default="/home/paul/corpus-structure")
    ap.add_argument("--out", default=str(HERE))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for d in a.days:
        files += sorted((Path(a.sessions_root) / d).glob("rollout-*.jsonl"))
    sessions = []
    for f in files:
        with f.open() as fh:
            first = fh.readline()
        if f'"cwd":"{a.cwd}' not in first:
            continue
        meta, execs, polls, patches, fcalls = load_session(f)
        if meta is None:
            continue
        meta["file"] = f.name
        sessions.append({"meta": meta, "execs": execs, "polls": polls, "patches": patches, "fcalls": fcalls})
    print(f"{len(sessions)} sessions", file=sys.stderr)

    R = collections.defaultdict
    cls_count, cls_bytes, cls_tokens = collections.Counter(), collections.Counter(), collections.Counter()
    cls_sizes = R(list)
    role_cls = R(collections.Counter)
    role_n, role_bytes = collections.Counter(), collections.Counter()
    contains = collections.Counter()
    ci_sub = collections.Counter()
    ci_opts = R(collections.Counter)
    ci_examples, ci_bytes = {}, R(int)
    all_exec = []
    unparsed = total = 0
    capped, cap_total, trunc_marker = collections.Counter(), collections.Counter(), collections.Counter()
    per_session = []
    help_by_group, docs_commands = collections.Counter(), collections.Counter()
    usage_errors = []
    ci_pipe = collections.Counter()
    buildci_ref = collections.Counter()
    extremes = collections.Counter()
    extremes_cls = collections.Counter()
    ci_exit = collections.Counter()
    repl_pairs = collections.defaultdict(set)
    env_hits = collections.Counter()
    env_examples = R(list)
    inline_count = collections.Counter()
    inline_examples = R(list)
    capture_seq = []
    reread_cls, producer_cls = collections.Counter(), collections.Counter()
    repeated = collections.Counter()
    read_path_count = collections.Counter()
    read_path_sessions = R(set)
    rg_classes = collections.Counter()
    rg_scopes = collections.Counter()
    rg_multi = 0
    env_prefix = collections.Counter()
    read_cat = collections.Counter()
    sed_window = []
    poll_stats = []
    rg_examples = R(list)
    chains = []
    chain_count = 0
    test_rows = []
    mech = []
    sess_first_reads = []
    ci_next = collections.Counter()
    poll_total = sleep_total = 0

    for si, S in enumerate(sessions):
        meta = S["meta"]
        role = meta["role"] or "unknown"
        execs = S["execs"]
        role_n[role] += len(execs)
        sleep_total += S["fcalls"].get("sleep", 0)
        poll_total += len(S["polls"])
        seen_norm = collections.Counter()
        captured = {}
        sess_reads = []
        analysed = []
        for ei, e in enumerate(execs):
            total += 1
            e["idx"] = ei
            if e["cmd"] is None:
                unparsed += 1
                continue
            items, subst, primary = analyse_cmd(e["cmd"])
            e["items"], e["subst"], e["primary"] = items, subst, primary
            pc = primary["cls"] if primary else "trivial"
            e["pc"] = pc
            b = e.get("out_bytes")
            cls_count[pc] += 1
            role_cls[role][pc] += 1
            if b is not None:
                cls_bytes[pc] += b
                cls_sizes[pc].append(b)
                role_bytes[role] += b
            ot = e.get("orig_tokens")
            if ot is not None:
                cls_tokens[pc] += ot
            for cl in {c["cls"] for c in subst}:
                contains[cl] += 1
            if e.get("max_tokens") and ot is not None:
                cap_total[pc] += 1
                if ot > e["max_tokens"]:
                    capped[pc] += 1
            if e.get("trunc_marker") or e.get("script_trunc"):
                trunc_marker[pc] += 1
            seen_norm[norm_cmd(e["cmd"])] += 1
            if ot is not None:
                for th in (100_000, 1_000_000):
                    if ot > th:
                        extremes[f">{th} tokens before cap"] += 1
                        extremes_cls[(f">{th}", pc)] += 1
            if e.get("head") is not None:
                if "direnv:" in e["head"][:300]:
                    extremes["output begins with direnv load/unload noise"] += 1
                extremes["outputs with parsed head"] += 1
                if re.search(r"direnv: error|Agent environment unavailable", e["head"]):
                    extremes["output reports direnv blocked / agent environment unavailable"] += 1
            if e.get("poll_session") is not None:
                extremes["exec returned a still-running session id (needs write_stdin poll)"] += 1
            if e.get("exit") is not None or e.get("poll_session") is not None:
                extremes["exec with parsed result"] += 1
            cis = [c for c in subst if c["cls"] == "ci"]
            for c in cis:
                k = c["key"]
                ci_sub[k] += 1
                for o in set(c["opts"]):
                    ci_opts[k][o] += 1
                ci_examples.setdefault(k, mask(c["text"]))
                if "--help" in c["opts"] or "-h" in c["opts"]:
                    parts = k.split()
                    help_by_group[parts[1] if len(parts) > 1 else "(root)"] += 1
                if k.startswith("ci docs commands"):
                    docs_commands[mask(c["text"], 120)] += 1
            if len(cis) == 1 and len(subst) <= 3 and b is not None:
                ci_bytes[cis[0]["key"]] += b
            for ix, c in enumerate(items[:-1]):
                nx = items[ix + 1]
                if c["cls"] == "ci" and nx["stage"] == c["stage"] + 1:
                    ci_pipe[(c["key"], nx["cls"] if nx["cls"] != "read" else nx["key"])] += 1
            if re.search(r"build/ci/", e["cmd"]):
                buildci_ref[pc] += 1
            nonzero = e.get("exit") not in (0, None)
            help_call = any(("--help" in c["opts"] or "-h" in c["opts"]) for c in cis)
            if cis and nonzero and not help_call and e.get("usage_err"):
                nxt = execs[ei + 1]["cmd"] if ei + 1 < len(execs) and execs[ei + 1]["cmd"] else ""
                hl = next((l for l in (e.get("head") or "").splitlines() if USAGE.search(l)), (e.get("head") or "")[:120])
                usage_errors.append({"session": si, "role": role, "cmd": mask(e["cmd"]), "msg": mask(hl, 120), "next": mask(nxt), "exit": e.get("exit")})
            if cis and e.get("exit") is not None:
                ci_exit[(cis[0]["key"], "nonzero" if nonzero else "zero")] += 1
            if pc not in ("read", "rg", "rg-files", "fs", "git"):
                for k in e.get("env") or []:
                    env_hits[k] += 1
                    if len(env_examples[k]) < 4:
                        env_examples[k].append(mask(e["cmd"], 120))
            if re.search(r"PYTHONPATH=", e["cmd"]):
                env_prefix["PYTHONPATH="] += 1
            if re.search(r"UV_PROJECT_ENVIRONMENT=", e["cmd"]):
                env_prefix["UV_PROJECT_ENVIRONMENT="] += 1
            if re.search(r"UV_NO_SYNC=1|--no-sync", e["cmd"]):
                env_prefix["UV_NO_SYNC/--no-sync"] += 1
            if re.search(r"CORPUS_DATABASE__", e["cmd"]):
                env_prefix["CORPUS_DATABASE__*"] += 1
            if re.search(r"(^|\s)cd\s", e["cmd"]):
                env_prefix["cd in command"] += 1
            if re.search(r"/home/paul/(ddo-|corpus-structure-)|/tmp/ddo-", e["cmd"] + (e.get("workdir") or "")):
                env_prefix["alternate worktree path"] += 1
            for ix, c in enumerate(items):
                if not ((c["cls"] == "python-inline" and c["stage"] == 0) or c["cls"] == "jq"):
                    continue
                text = e["cmd"] if c["cls"] == "jq" else ((c["body"] or "") + " " + c["text"])
                prev_ci = c["stage"] > 0 and ix > 0 and items[ix - 1]["cls"] == "ci"
                writes = bool(re.search(r"(write_text\(|write_bytes\(|open\([^)]*['\"](w|a)['\"])", text))
                tags = [k for k, rx in RX.items() if rx.search(text)]
                if c["cls"] == "jq":
                    p = "jq:parses ci output/receipts" if (prev_ci or re.search(r"build/ci|\bci (results|test)", e["cmd"])) else "jq:other"
                elif writes:
                    fp = re.search(r"['\"]([\w./-]+\.(?:py|rs|md|toml|sql|json|yaml|yml|txt))['\"]", text)
                    fpath = fp.group(1) if fp else ""
                    tgt = "docs" if fpath.startswith(("docs/", "STATUS", "AGENTS", ".agents", ".claude")) or fpath.endswith(".md") else ("tests" if "/tests/" in fpath else "src")
                    p = f"file-edit script ({tgt})"
                elif "code_intel" in tags:
                    p = "code-intel (ast/inspect/importlib/walk)"
                elif prev_ci or re.search(r"build/ci|reportlog|junit|sys\.stdin|subprocess[^)]*['\"]ci['\"]", text):
                    p = "parses ci output/receipts"
                elif "database" in tags:
                    p = "database/sql"
                elif "docs_or_text" in tags:
                    p = "reads docs/text"
                else:
                    p = "other"
                inline_count[p] += 1
                if len(inline_examples[p]) < 8:
                    inline_examples[p].append(mask((c["body"] or c["text"]).replace("\n", " | "), 200))
                if c["cls"] != "jq" and writes:
                    pairs = re.findall(r"\.replace\(\s*(?:'([^']{6,}?)'|\"([^\"]{6,}?)\")\s*,\s*(?:'([^']*?)'|\"([^\"]*?)\")", text)
                    files = set(re.findall(r"['\"]([\w./-]+\.(?:py|rs|md|toml|sql|json|yaml))['\"]", text))
                    for pr in pairs:
                        repl_pairs[(si, (pr[0] or pr[1])[:80], (pr[2] or pr[3])[:80])].add(tuple(sorted(files))[:1])
                    loop = bool(re.search(r"(rglob|glob\(|for \w+ in )", text))
                    mech.append({"session": si, "role": role, "kind": "python edit (loop/multi-file)" if (loop or len(files) >= 3) else "python edit (single-file)", "files": len(files), "example": mask(text, 200)})
            for c in subst:
                if c["cls"] in ("sed-i", "perl-i"):
                    mech.append({"session": si, "role": role, "kind": c["cls"], "files": len([x for x in c["tokens"][1:] if "/" in x]), "example": mask(c["text"], 200)})
            producer = cis[0]["key"] if cis else (primary["key"] if primary else "?")
            if not any(c["body"] for c in subst):
                for c in subst:
                    if c["cls"] in ("read", "trivial") and c["key"] in ("cat",):
                        pass
                    for m in REDIR.finditer(c["text"]):
                        pth = m.group("p").strip("'\"")
                        if not pth or pth.startswith(("&", "/dev/", "$")) or pth.isdigit():
                            continue
                        if not re.match(r"^(/tmp/|/var/tmp/|build/|tmp/|\.tmp|/home/paul/\S*/build/|\S*(/results/|/scratch/|/out/))", pth):
                            continue
                        captured[pth] = (ei, producer, mask(e["cmd"], 160))
            for pth, (pi, prod, pcmd) in list(captured.items()):
                if pi < ei and pth in e["cmd"]:
                    readers = [c for c in subst if pth in c["text"] or pth in (c["body"] or "")]
                    rc = readers[0] if readers else (primary or {"cls": "?", "key": "?"})
                    if rc["cls"] not in ("read", "rg", "jq", "python-inline", "fs"):
                        continue
                    rk = rc["key"]
                    capture_seq.append({"session": si, "role": role, "producer": prod, "path": pth, "gap": ei - pi, "reader": rk, "producer_cmd": pcmd, "follow_cmd": mask(e["cmd"], 160)})
                    reread_cls[rk] += 1
                    producer_cls[prod] += 1
                    del captured[pth]
            for c in items:
                if c["cls"] == "read" and c["key"] == "sed":
                    mm = re.search(r"-n\s+['\"]?(\d+),(\d+)p", c["text"])
                    if mm:
                        sed_window.append(int(mm.group(2)) - int(mm.group(1)) + 1)
            for pth in read_paths(items):
                cat_ = "docs/skills/roles" if pth.startswith(("docs", "STATUS", "AGENTS", ".agents", ".claude")) or pth.endswith(".md") else ("tests" if "/tests/" in pth else ("src" if pth.startswith(("python", "crates")) else "other"))
                read_cat[cat_] += 1
                read_path_count[pth] += 1
                read_path_sessions[pth].add(si)
                sess_reads.append(pth)
            for c in subst:
                if c["cls"] == "rg" and c["stage"] == 0:
                    pat = rg_pattern(c)
                    k = classify_pattern(pat)
                    rg_classes[k] += 1
                    rg_scopes[rg_scope(c)] += 1
                    if len(re.split(r"\\?\|", pat)) >= 4:
                        rg_multi += 1
                    if len(rg_examples[k]) < 6:
                        rg_examples[k].append(mask(c["text"], 160))
            analysed.append(e)
        for n, c in seen_norm.items():
            if c >= 3 and not n.startswith(("git status", "git diff --stat")):
                repeated[n[:200]] += 1
        for i, e in enumerate(analysed):
            if e.get("pc") == "rg" and e.get("out_paths"):
                hits = set(e["out_paths"])
                nread = sum(1 for e2 in analysed[i + 1 : i + 7] for pth in read_paths(e2["items"]) if pth in hits)
                if nread >= 2:
                    chain_count += 1
                    if len(chains) < 12:
                        chains.append(mask(e["cmd"], 140))
        for e in analysed:
            for c in e["subst"]:
                if c["cls"] == "ci" and c["key"] == "ci test":
                    has_sep = "--" in c["tokens"]
                    paths = c["tokens"][c["tokens"].index("--") + 1 :] if has_sep else []
                    test_rows.append({"session": si, "role": role, "kind": "ci test (paths)" if has_sep else "ci test (full/flags)", "selection": " ".join(sorted(paths))[:160], "exit": e.get("exit"), "wall": e.get("wall"), "still_running": e.get("poll_session") is not None, "ids": e.get("result_ids")})
        for e in analysed:
            ps = e.get("poll_session")
            if ps is None:
                continue
            mine = [pd for pd in S["polls"] if pd["session"] == ps and pd["ts"] >= e["ts"]]
            done = [pd for pd in mine if pd.get("exit") is not None]
            t0 = tsd(e["ts"])
            t1 = tsd(done[0]["out_ts"]) if done else None
            key = (e["primary"]["key"] if e["primary"] and e["primary"]["cls"] in ("ci", "just", "cargo", "pyrefly", "ruff") else (e["primary"]["cls"] if e["primary"] else "?"))
            poll_stats.append({"key": key, "polls": len(mine), "empty_polls": sum(1 for pd in mine if pd.get("orig_tokens") == 0), "completed": bool(done), "duration_s": (t1 - t0).total_seconds() if (t0 and t1) else None, "yield_cmd": mask(e["cmd"], 120)})
        sc = collections.Counter(e.get("pc", "unparsed") for e in execs)
        per_session.append({"idx": si, "role": role, "nickname": meta["nickname"], "file": meta["file"], "start": meta["start"], "execs": len(execs), "write_stdin_polls": len(S["polls"]), "apply_patch": len(S["patches"]), "out_bytes": sum(e.get("out_bytes") or 0 for e in execs), "ci_cmds": sum(1 for e in execs if any(c["cls"] == "ci" for c in e.get("subst", []))), "rg": sc["rg"], "read": sc["read"], "git": sc["git"], "python_inline": sc["python-inline"]})
        sess_first_reads.append(sess_reads[:10])
        all_exec.append(analysed)
        for i, e in enumerate(analysed[:-1]):
            if any(c["cls"] == "ci" for c in e["subst"]):
                ci_next[(e["primary"]["key"] if e["primary"] else "?", analysed[i + 1]["pc"])] += 1

    reads_after = []
    rerun = collections.Counter()
    test_kinds = collections.Counter(r["kind"] for r in test_rows)
    for r in test_rows:
        rerun[(r["session"], r["selection"])] += 1
    for si, analysed in enumerate(all_exec):
        for i, e in enumerate(analysed):
            if not any(c["key"] == "ci test" for c in e["subst"] if c["cls"] == "ci"):
                continue
            ids = e.get("result_ids") or []
            for e2 in analysed[i + 1 : i + 15]:
                if (ids and any(x in e2["cmd"] for x in ids)) or re.search(r"ci (test failures|results)", e2["cmd"]) or "build/ci" in e2["cmd"]:
                    t0, t1 = tsd(e.get("out_ts") or e["ts"]), tsd(e2["ts"])
                    kind = next((c["key"] for c in e2["subst"] if c["cls"] == "ci"), "build/ci file read")
                    if t0 and t1:
                        reads_after.append({"gap_s": (t1 - t0).total_seconds(), "kind": kind, "steps": e2["idx"] - e["idx"]})
                    break

    patch_eps = []
    for si, S in enumerate(sessions):
        pairs = collections.defaultdict(set)
        for pt in S["patches"]:
            cur = prev = None
            for ln in pt["patch"].split("\n"):
                if ln.startswith("*** Update File:"):
                    cur = ln.split(":", 1)[1].strip()
                elif ln.startswith("-") and not ln.startswith("---"):
                    prev = ln[1:].strip()
                elif ln.startswith("+") and prev is not None:
                    if len(prev) > 12 and prev != ln[1:].strip():
                        pairs[(prev, ln[1:].strip())].add(cur)
                    prev = None
                else:
                    prev = None
        for (m, p), fs_ in pairs.items():
            if len(fs_) >= 3:
                patch_eps.append({"session": si, "role": S["meta"]["role"], "files": len(fs_), "removed": mask(m, 100), "added": mask(p, 100)})
    patch_eps.sort(key=lambda x: -x["files"])

    # ------------------------------------------------------------------ outputs
    def wj(name, obj):
        (out / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n")

    def wc(name, header, rows):
        with (out / name).open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)

    summary = {
        "window": {"days": a.days, "cwd": a.cwd},
        "sessions": len(sessions),
        "sessions_by_role": collections.Counter(s["meta"]["role"] or "unknown" for s in sessions),
        "exec_commands": total,
        "unparsed_cmd_literal": unparsed,
        "execs_by_role": role_n,
        "apply_patch_calls": sum(len(s["patches"]) for s in sessions),
        "write_stdin_polls": poll_total,
        "sleep_calls": sleep_total,
        "function_calls": dict(sum((s["fcalls"] for s in sessions), collections.Counter())),
        "output_bytes_total": sum(cls_bytes.values()),
        "output_bytes_by_role": role_bytes,
        "rg_chain_rg_then_2plus_reads_of_hits": chain_count,
        "rg_chain_examples": chains,
        "commands_containing_class_anywhere": contains,
    }
    wj("summary.json", summary)
    rows = []
    for k, n in cls_count.most_common():
        sz = cls_sizes[k]
        rows.append([k, n, round(100 * n / max(1, total), 1), cls_bytes[k], cls_tokens[k], statistics.median(sz) if sz else 0, pct(sz, 0.9), max(sz) if sz else 0, capped[k], cap_total[k], trunc_marker[k]])
    wc("command_mix.csv", ["primary_class", "count", "pct_of_execs", "out_bytes", "orig_tokens", "median_bytes", "p90_bytes", "max_bytes", "over_max_output_tokens", "with_cap_known", "truncation_marker"], rows)
    wj("command_mix_by_role.json", {r: dict(c.most_common()) for r, c in role_cls.items()})
    wc("ci_subcommands_top40.csv", ["subcommand", "count", "out_bytes_when_sole_ci", "options_used", "example"], [[k, n, ci_bytes[k], ";".join(f"{o}:{c}" for o, c in ci_opts[k].most_common(8)), ci_examples[k]] for k, n in ci_sub.most_common(40)])
    wj("ci_all_subcommands.json", dict(ci_sub.most_common()))
    big = sorted(((e["out_bytes"], e.get("orig_tokens"), e["pc"], e["cmd"]) for an in all_exec for e in an if e.get("out_bytes") is not None), key=lambda x: -x[0])
    wc("largest_outputs_top30.csv", ["out_bytes", "orig_tokens", "class", "command"], [[b, t, c, mask(cmd, 200)] for b, t, c, cmd in big[:30]])
    wj("output_size_distribution.json", {"overall": dist([x[0] for x in big]), "by_class": {k: dist(v) for k, v in cls_sizes.items()}})
    wj("capture_then_reread.json", {"sequences": len(capture_seq), "by_reader": reread_cls, "by_producer": producer_cls, "median_gap_execs": statistics.median([c["gap"] for c in capture_seq]) if capture_seq else 0, "examples": capture_seq[:25]})
    wc("capture_then_reread_all.csv", ["session", "role", "producer", "gap", "reader", "path", "producer_cmd", "follow_cmd"], [[c["session"], c["role"], c["producer"], c["gap"], c["reader"], c["path"], c["producer_cmd"], c["follow_cmd"]] for c in capture_seq])
    wj("inline_scripts.json", {"counts": inline_count, "examples": inline_examples})
    wj("discoverability.json", {"help_by_ci_group": help_by_group, "docs_commands_invocations": docs_commands, "usage_errors": len(usage_errors), "next_after_usage_error": collections.Counter(("--help" if "--help" in u["next"] else (u["next"].split()[0] if u["next"] else "")) for u in usage_errors), "examples": usage_errors[:40]})
    wc("usage_errors.csv", ["session", "role", "exit", "cmd", "msg", "next"], [[u["session"], u["role"], u["exit"], u["cmd"], u["msg"], u["next"]] for u in usage_errors])
    wc("repeated_commands_top40.csv", ["normalized_command", "sessions_with_>=3_repeats"], repeated.most_common(40))
    wc("most_read_paths_top40.csv", ["path", "reads", "sessions"], [[p, n, len(read_path_sessions[p])] for p, n in read_path_count.most_common(40)])
    orient = collections.Counter(p for rs in sess_first_reads for p in set(rs))
    wj("session_start_reads.json", {"sessions": len(sess_first_reads), "paths_in_first_10_reads_by_session_count": dict(orient.most_common(25))})
    wj("source_navigation.json", {"rg_pattern_classes": rg_classes, "rg_scopes": rg_scopes, "rg_patterns_with_4plus_alternatives": rg_multi, "read_target_categories": read_cat, "sed_window_line_counts": dist(sed_window), "cmd_env_prefix": env_prefix, "examples": rg_examples, "rg_total": sum(rg_classes.values()), "rg_files": cls_count["rg-files"], "rg_then_reads_chains": chain_count, "share_of_execs_pct": {k: round(100 * cls_count[k] / max(1, total), 1) for k in ("rg", "read", "rg-files", "fs")}})
    wj("test_loop.json", {"launches_by_kind": test_kinds, "other_test_routes_primary": {k: cls_count[k] for k in ("pytest", "cargo", "just")}, "reads_after_launch": {"n": len(reads_after), "median_gap_s": statistics.median([r["gap_s"] for r in reads_after]) if reads_after else None, "by_kind": collections.Counter(r["kind"] for r in reads_after), "median_steps": statistics.median([r["steps"] for r in reads_after]) if reads_after else None}, "launch_returned_still_running": sum(1 for r in test_rows if r["still_running"]), "selections_rerun_in_session": sum(1 for k, v in rerun.items() if v > 1 and k[1]), "rerun_top": [[list(k), v] for k, v in rerun.most_common(12) if v > 1], "launch_exit_codes": collections.Counter(r["exit"] for r in test_rows)})
    agg = collections.defaultdict(lambda: {"launches": 0, "polls": 0, "empty_polls": 0, "completed": 0, "durations": []})
    for r in poll_stats:
        g = agg[r["key"]]
        g["launches"] += 1
        g["polls"] += r["polls"]
        g["empty_polls"] += r["empty_polls"]
        g["completed"] += r["completed"]
        if r["duration_s"] is not None:
            g["durations"].append(r["duration_s"])
    wj("ci_pipelines.json", {"ci_stage_piped_to": {f"{k[0]} | {k[1]}": n for k, n in ci_pipe.most_common(40)}, "ci_piped_total": sum(ci_pipe.values()), "ci_piped_to_python_or_jq": sum(n for (k, v), n in ci_pipe.items() if v in ("python-inline", "jq", "python-script")), "commands_referencing_build_ci_paths_by_class": buildci_ref})
    wj("output_extremes.json", {"counts": extremes, "by_class": {f"{k[0]} {k[1]}": n for k, n in extremes_cls.most_common()}})
    wj("long_running_commands.json", {k: {**{x: y for x, y in v.items() if x != "durations"}, "duration_s": dist(v["durations"])} for k, v in sorted(agg.items(), key=lambda kv: -kv[1]["launches"])})
    wj("ci_exit_codes.json", {f"{k[0]} [{k[1]}]": n for k, n in sorted(ci_exit.items())})
    rp = collections.defaultdict(list)
    for (si_, old, new), fl in repl_pairs.items():
        rp[(old, new)].append(si_)
    wj("repeated_replace_pairs.json", [{"old": o, "new": n, "sessions": sorted(set(v)), "scripts": len(v)} for (o, n), v in sorted(rp.items(), key=lambda kv: -len(kv[1])) if len(v) >= 3 and len(o.strip()) >= 20][:25])
    wc("ci_test_launches.csv", ["session", "role", "kind", "selection", "exit", "wall_s", "still_running_after_yield", "ids"], [[r["session"], r["role"], r["kind"], r["selection"], r["exit"], r["wall"], r["still_running"], " ".join(r["ids"] or [])] for r in test_rows])
    wj("mechanical_edits.json", {"edit_scripts_total": len(mech), "by_kind": collections.Counter(m["kind"] for m in mech), "examples": mech[:25], "apply_patch_repeated_replacement_episodes": len(patch_eps), "apply_patch_examples": patch_eps[:20]})
    wj("env_and_waiting.json", {"output_flags": env_hits, "examples": env_examples, "write_stdin_polls": poll_total, "sleep_calls": sleep_total, "next_class_after_ci": {f"{x} -> {y}": n for (x, y), n in ci_next.most_common(40)}})
    wc("per_session.csv", list(per_session[0].keys()), [list(p.values()) for p in per_session])
    md = ["# Aggregated tables (generated by extract.py)\n", f"Sessions: {len(sessions)}; exec_command calls: {total}; apply_patch calls: {summary['apply_patch_calls']}.\n", "\n## Command mix (primary class)\n", "| class | count | % | out MB | over cap | trunc marker |", "|---|---|---|---|---|---|"]
    for k, n in cls_count.most_common(25):
        md.append(f"| {k} | {n} | {round(100 * n / max(1, total), 1)} | {cls_bytes[k] / 1e6:.2f} | {capped[k]}/{cap_total[k]} | {trunc_marker[k]} |")
    md.append("\n## Top ci subcommands\n\n| subcommand | n | common options |\n|---|---|---|")
    for k, n in ci_sub.most_common(40):
        md.append(f"| {k} | {n} | {', '.join(o for o, _ in ci_opts[k].most_common(5))} |")
    (out / "tables.md").write_text("\n".join(md) + "\n")
    print("done", file=sys.stderr)


if __name__ == "__main__":
    main()
