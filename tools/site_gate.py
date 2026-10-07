#!/usr/bin/env python3
"""site_gate.py — 公开站发布闸（fail-closed，纯标准库；本地主闸 + 公开仓库 CI 复检同一份）。

只认明确通过：每个必需检查器必须对每个文件显式返回 PASS；检查器缺失/抛异常/超时、
必需配置缺失（品牌词表、PII 私人词）一律 FAIL（退出码 ≠0）。
日志只打印「文件、行号、规则 id」，绝不打印命中原文；文件名本身命中规则时，文件名打码成 sha256 前缀。

用法:
  site_gate.py --paths <文件或目录...>      扫描
  site_gate.py --dist <dir> [--config C]    扫描构建产物（全部文件；字体按扩展名不做文本扫描，仍查类型/文件名）
  site_gate.py --manifest <dir> [--map M]   打印待发布清单（路径/大小/sha256/来源映射/git 作者）

配置（优先级）: --config <路径> > env SITE_GATE_CONFIG（整份配置 JSON 文本，CI 用 GitHub secret 注入）
  > 同目录 site_gate.config.json（仅 personal 私有仓库有）；都没有 ⇒ FAIL。
  公开仓库只放 site_gate.config.example.json（只有结构、词表为空，单独使用必 FAIL）。
num-* 规则只用于「我们自己的业务数字」可能出现的地方：diary/works/resume 栏目、首页/about 及其渲染 HTML；
  不用于 brandlab（第三方品牌事实，带出处）和 JS/CSS 打包产物。其余规则处处生效。
私人词（真名等）: env SITE_GATE_PII_TERMS（逗号分隔）；本地未设时读
  `python3 ~/.claude/lib/secret.py get SITE_GATE_PII_TERMS`；CI（env CI / GITHUB_ACTIONS）只认 env。
测试钩子（只会让闸更严）: SITE_GATE_TEST_SKIP=<checker id>（模拟检查器缺失）、
  SITE_GATE_TEST_RAISE=<checker id>（模拟检查器抛异常）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import struct
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG = HERE / "site_gate.config.json"
DEFAULT_MAP = HERE / ".site_export_map.json"
REQUIRED_CONFIG_KEYS = ("brands", "email_allowlist", "fuzzy_number_allowlist", "forbidden_ext",
                        "forbidden_name_regex", "image_ext", "text_ext", "allowed_binary_ext")
PASS = "PASS"


class GateError(Exception):
    """配置/环境级错误：一律 FAIL。消息里不得含命中原文。"""


# ── 配置 ──────────────────────────────────────────────────────────────────────
def load_config(path=None) -> dict:
    env_json = os.environ.get("SITE_GATE_CONFIG")
    if path:
        p = Path(path)
        if not p.is_file():
            raise GateError(f"config missing: {p}")
        raw, src = p.read_text(encoding="utf-8"), str(p)
    elif env_json is not None:
        raw, src = env_json, "env SITE_GATE_CONFIG"
    elif DEFAULT_CONFIG.is_file():
        raw, src = DEFAULT_CONFIG.read_text(encoding="utf-8"), str(DEFAULT_CONFIG)
    else:
        raise GateError("config missing: pass --config or set env SITE_GATE_CONFIG (JSON)")
    try:
        cfg = json.loads(raw)
    except Exception as e:  # noqa: BLE001
        raise GateError(f"config unreadable: {src} ({type(e).__name__})")
    if not isinstance(cfg, dict):
        raise GateError(f"config not an object: {src}")
    for k in REQUIRED_CONFIG_KEYS:
        if k not in cfg or not isinstance(cfg[k], list):
            raise GateError(f"config key missing or not a list: {k}")
    brands = [b.strip() for b in cfg["brands"] if isinstance(b, str) and b.strip()]
    if not brands:
        raise GateError("config brands empty")
    cfg["brands"] = brands
    cfg.setdefault("skip_dirs", [".git"])
    return cfg


def _in_ci() -> bool:
    return bool(os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"))


def load_pii_terms() -> list:
    raw = os.environ.get("SITE_GATE_PII_TERMS")
    if raw is None and not _in_ci():
        secret = Path(os.path.expanduser("~/.claude/lib/secret.py"))
        if not secret.is_file():
            raise GateError("SITE_GATE_PII_TERMS unset and secret.py not found")
        try:
            r = subprocess.run([sys.executable, str(secret), "get", "SITE_GATE_PII_TERMS"],
                               capture_output=True, text=True, timeout=30)
        except Exception as e:  # noqa: BLE001
            raise GateError(f"secret.py failed ({type(e).__name__})")
        if r.returncode != 0:
            raise GateError("secret SITE_GATE_PII_TERMS not registered/readable "
                            "(register via secret-manager, or set env SITE_GATE_PII_TERMS)")
        raw = r.stdout
    if raw is None:
        raise GateError("SITE_GATE_PII_TERMS unset (CI: set it from a GitHub secret)")
    terms = [t.strip() for t in raw.replace("\n", ",").split(",") if t.strip()]
    if not terms:
        raise GateError("SITE_GATE_PII_TERMS empty")
    return terms


# ── 规则 ──────────────────────────────────────────────────────────────────────
RE_PHONE = re.compile(r"(?<!\d)(?:\+?86[\s-]?)?1[3-9]\d[\s-]?\d{4}[\s-]?\d{4}(?!\d)")
RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
RE_WECHAT = re.compile(r"wxid_[A-Za-z0-9_\-]+|(?:微信|VX|vx|wechat|WeChat)\s*号?\s*[:：]")
RE_IDCARD = re.compile(r"(?<![0-9A-Za-z])\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx](?![0-9A-Za-z])")
RE_SECRET = re.compile(r"\bsk-[A-Za-z0-9_\-]{16,}|\bgh[pousr]_[A-Za-z0-9]{20,}|(?i:\bBearer\s+[A-Za-z0-9/_\-.]{12,})")
RE_PRIVATE_PATH = re.compile(r"(?<![\w/])(?:ip|resume|xhs)/[\w\-.]+/|~/|/Users/|/home/[a-z]")
NUMBER_RULES = [
    ("num-dollar", re.compile(r"[$＄]\s?\d|\d[\d,.]*\s*(?:美金|美元|USD)\b|\bUSD\s?\d")),
    ("num-wan", re.compile(r"\d[\d,.]*\s*[万亿]")),
    ("num-gmv", re.compile(r"(?i)GMV")),
    ("num-roi", re.compile(r"(?i)ROI\s*[:：=]?\s*\d")),
    ("num-yuan", re.compile(r"[¥￥]\s?\d|\d[\d,.]*\s*元")),
]


def _email_allowed(m: str, allow: list) -> bool:
    """allowlist 项含 @ = 整址精确匹配；不含 @ = 域名（含子域）匹配。"""
    m = m.lower()
    dom = m.rsplit("@", 1)[-1]
    for a in (x.lower() for x in allow):
        if ("@" in a and m == a) or ("@" not in a and (dom == a or dom.endswith("." + a))):
            return True
    return False


def term_matcher(terms):
    """ASCII 词按字母数字边界匹配（防随机哈希里撞词）；含非 ASCII 的词（中文名/公司名）按子串匹配。
    边界只看 [A-Za-z0-9]，所以 brand_shop / brand-inc 仍命中。"""
    pats = []
    for t in terms:
        if t.isascii():
            pats.append(re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I))
        else:
            pats.append(re.compile(re.escape(t), re.I))
    return lambda ln: any(p.search(ln) for p in pats)


# 只对 lockfile 生效：剥掉 "integrity": "sha512-<base64>" 的值（base64 里会随机撞出短词）；其余内容照常扫
LOCKFILE_NAMES = ("package-lock.json", "npm-shrinkwrap.json")
RE_LOCK_INTEGRITY = re.compile(r'("integrity"\s*:\s*")sha(?:1|256|384|512)-[A-Za-z0-9+/=]+(")')


def text_findings(text: str, cfg: dict, terms: list, checker: str) -> list:
    """返回 [(line_no, rule_id)]；line_no 从 1 计。只返回位置和规则，不返回原文。"""
    out = []
    lines = text.split("\n")
    if checker == "brand":
        hit = term_matcher(cfg["brands"])
        for i, ln in enumerate(lines, 1):
            if hit(ln):
                out.append((i, "brand"))
    elif checker == "pii":
        term_hit = term_matcher(terms)
        for i, ln in enumerate(lines, 1):
            if RE_PHONE.search(ln):
                out.append((i, "pii-phone"))
            if any(not _email_allowed(m.group(0), cfg["email_allowlist"]) for m in RE_EMAIL.finditer(ln)):
                out.append((i, "pii-email"))
            if RE_WECHAT.search(ln):
                out.append((i, "pii-wechat"))
            if RE_IDCARD.search(ln):
                out.append((i, "pii-idcard"))
            if term_hit(ln):
                out.append((i, "pii-term"))
            if RE_SECRET.search(ln):
                out.append((i, "secret"))
            if RE_PRIVATE_PATH.search(ln):
                out.append((i, "private-path"))
    elif checker == "numbers":
        allow = sorted(cfg["fuzzy_number_allowlist"], key=len, reverse=True)
        for i, ln in enumerate(lines, 1):
            s = ln
            for a in allow:
                s = s.replace(a, " ")
            for rid, rx in NUMBER_RULES:
                if rx.search(s):
                    out.append((i, rid))
    else:
        raise GateError(f"unknown text checker {checker}")
    return out


# ── 图片元数据（字节级解析，无 PIL） ───────────────────────────────────────────
class ImageParseError(Exception):
    pass


def png_meta(data: bytes) -> list:
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ImageParseError("not png")
    pos, found = 8, []
    while pos + 8 <= len(data):
        ln, typ = struct.unpack(">I4s", data[pos:pos + 8])
        if pos + 12 + ln > len(data):
            raise ImageParseError("truncated chunk")
        if typ in (b"tEXt", b"iTXt", b"zTXt", b"eXIf"):
            found.append(typ.decode("ascii"))
        pos += 12 + ln
        if typ == b"IEND":
            return found
    raise ImageParseError("no IEND")


JPEG_META_MARKERS = {0xE1, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEF, 0xFE}


def jpeg_segments(data: bytes):
    """yield (marker, start, end) for header segments up to SOS (inclusive marker, payload excluded)."""
    if data[:2] != b"\xff\xd8":
        raise ImageParseError("not jpeg")
    pos = 2
    while pos < len(data):
        if data[pos] != 0xFF:
            raise ImageParseError("bad marker")
        while pos < len(data) and data[pos] == 0xFF:
            pos += 1
        if pos >= len(data):
            raise ImageParseError("truncated")
        marker = data[pos]
        pos += 1
        if marker == 0xD9:  # EOI
            yield marker, pos - 2, pos
            return
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:
            continue
        if pos + 2 > len(data):
            raise ImageParseError("truncated length")
        (ln,) = struct.unpack(">H", data[pos:pos + 2])
        end = pos + ln
        if end > len(data):
            raise ImageParseError("truncated segment")
        yield marker, pos - 2, end
        if marker == 0xDA:  # SOS：之后是熵编码数据，不再有元数据段
            return
        pos = end
    raise ImageParseError("no SOS/EOI")


def jpeg_meta(data: bytes) -> list:
    return ["APP%d" % (m - 0xE0) if m != 0xFE else "COM"
            for m, _, _ in jpeg_segments(data) if m in JPEG_META_MARKERS]


GIF_OK_APPS = (b"NETSCAPE2.0", b"ANIMEXTS1.0")


def gif_blocks(data: bytes):
    """yield (kind, start, end)：kind ∈ header/ext-XX/app:<id>/image/trailer。"""
    if data[:6] not in (b"GIF87a", b"GIF89a"):
        raise ImageParseError("not gif")
    flags = data[10]
    pos = 13 + (3 * (2 << (flags & 7)) if flags & 0x80 else 0)
    if pos > len(data):
        raise ImageParseError("truncated header")
    yield "header", 0, pos

    def skip_sub(p):
        while True:
            if p >= len(data):
                raise ImageParseError("truncated sub-blocks")
            n = data[p]
            p += 1 + n
            if n == 0:
                return p

    while pos < len(data):
        b = data[pos]
        if b == 0x3B:
            yield "trailer", pos, pos + 1
            return
        if b == 0x21:
            if pos + 2 > len(data):
                raise ImageParseError("truncated ext")
            label = data[pos + 1]
            kind = "ext-%02X" % label
            if label == 0xFF:
                n = data[pos + 2]
                kind = "app:" + data[pos + 3:pos + 3 + min(n, 11)].decode("latin-1")
            end = skip_sub(pos + 2)
            yield kind, pos, end
            pos = end
        elif b == 0x2C:
            if pos + 10 > len(data):
                raise ImageParseError("truncated image desc")
            f = data[pos + 9]
            p = pos + 10 + (3 * (2 << (f & 7)) if f & 0x80 else 0)
            end = skip_sub(p + 1)  # +1 跳过 LZW min code size
            yield "image", pos, end
            pos = end
        else:
            raise ImageParseError("bad block")
    raise ImageParseError("no trailer")


def gif_meta(data: bytes) -> list:
    out = []
    for kind, _, _ in gif_blocks(data):
        if kind == "ext-FE":
            out.append("comment")
        elif kind.startswith("app:") and kind[4:].encode("latin-1") not in GIF_OK_APPS:
            out.append("appext")
    return out


def webp_meta(data: bytes) -> list:
    if data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        raise ImageParseError("not webp")
    pos, out = 12, []
    while pos + 8 <= len(data):
        typ, ln = data[pos:pos + 4], struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if typ in (b"EXIF", b"XMP "):
            out.append(typ.decode("ascii").strip())
        pos += 8 + ln + (ln & 1)
    if pos != len(data) and pos != len(data) + 1:
        raise ImageParseError("truncated riff")
    return out


def image_meta(path: Path, data: bytes) -> list:
    ext = path.suffix.lower()
    fn = {".png": png_meta, ".jpg": jpeg_meta, ".jpeg": jpeg_meta, ".gif": gif_meta, ".webp": webp_meta}.get(ext)
    if fn is None:
        raise ImageParseError("unsupported image type")
    return fn(data)


# ── 文件级检查器 ──────────────────────────────────────────────────────────────
# 每个检查器: (path, rel, data, cfg, terms) -> (PASS|"FAIL", [(line, rule)])
def _as_text(path: Path, data: bytes, cfg: dict):
    ext = path.suffix.lower()
    if ext in cfg["image_ext"] or ext in cfg["allowed_binary_ext"] or ext in cfg["forbidden_ext"]:
        return None
    return data.decode("utf-8")  # 解码失败抛异常 ⇒ filetype 检查器已判 FAIL；这里抛出也是 FAIL


def chk_filetype(path, rel, data, cfg, terms):
    ext, name = path.suffix.lower(), path.name
    f = []
    if ext in cfg["forbidden_ext"]:
        f.append((0, "file-forbidden-ext"))
    if any(re.search(rx, name, re.I) for rx in cfg["forbidden_name_regex"]):
        f.append((0, "file-forbidden-name"))
    known = set(cfg["text_ext"]) | set(cfg["image_ext"]) | set(cfg["allowed_binary_ext"]) | set(cfg["forbidden_ext"])
    if ext and ext not in known:
        f.append((0, "file-unknown-type"))
    if ext == "" or ext in cfg["text_ext"]:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            f.append((0, "file-not-utf8"))
    return ("FAIL" if f else PASS), f


NUM_SCOPE_DIRS = {"diary", "works", "resume"}
NUM_SKIP_EXT = {".js", ".mjs", ".cjs", ".css", ".map"}
PAGE_STEMS = {"index", "about"}


def num_scope(path: Path, rel: str) -> bool:
    """num-* 是否适用。按完整路径的目录名判断（扫哪一层根都一样，宁宽勿漏）。"""
    if path.suffix.lower() in NUM_SKIP_EXT:
        return False
    dirs = [d.lower() for d in Path(os.path.abspath(path)).parent.parts]
    if NUM_SCOPE_DIRS & set(dirs):
        return True
    rparts = [x.lower() for x in Path(rel).parts]
    stem = Path(rel).stem.lower()
    if "about" in rparts[:-1]:
        return True
    if stem in PAGE_STEMS and (len(rparts) == 1 or rparts[-2] == "pages"):
        return True  # 首页 / about（dist 根的 index.html、about.html，src/pages/index.astro 等）
    return False


def chk_filename(path, rel, data, cfg, terms):
    f = []
    for c in ("brand", "pii", "numbers") if num_scope(path, rel) else ("brand", "pii"):
        for _, rid in text_findings(rel, cfg, terms, c):
            if rid != "private-path":  # 相对路径本身不是私有路径泄露
                f.append((0, "filename-" + rid))
    return ("FAIL" if f else PASS), f


def _text_checker(name):
    def chk(path, rel, data, cfg, terms):
        try:
            text = _as_text(path, data, cfg)
        except UnicodeDecodeError:
            return "FAIL", [(0, "file-not-utf8")]
        if text is None:
            return PASS, []
        if name == "numbers" and not num_scope(path, rel):
            return PASS, []
        if path.name in LOCKFILE_NAMES:
            text = RE_LOCK_INTEGRITY.sub(r"\1\2", text)
        f = text_findings(text, cfg, terms, name)
        return ("FAIL" if f else PASS), f
    chk.__name__ = "chk_" + name
    return chk


def chk_image_meta(path, rel, data, cfg, terms):
    if path.suffix.lower() not in cfg["image_ext"]:
        return PASS, []
    try:
        found = image_meta(path, data)
    except (ImageParseError, struct.error, IndexError):
        return "FAIL", [(0, "image-unparseable")]
    return ("FAIL", [(0, "image-meta-" + k.lower()) for k in found]) if found else (PASS, [])


CHECKERS = {
    "filetype": chk_filetype,
    "filename": chk_filename,
    "brand": _text_checker("brand"),
    "pii": _text_checker("pii"),
    "numbers": _text_checker("numbers"),
    "image_meta": chk_image_meta,
}
REQUIRED_CHECKERS = ("filetype", "filename", "brand", "pii", "numbers", "image_meta")


def _active_checkers():
    skip = os.environ.get("SITE_GATE_TEST_SKIP", "")
    raise_id = os.environ.get("SITE_GATE_TEST_RAISE", "")
    active = {}
    for k, fn in CHECKERS.items():
        if k == skip:
            continue
        if k == raise_id:
            def boom(*a, **kw):
                raise RuntimeError("injected checker failure")
            active[k] = boom
        else:
            active[k] = fn
    return active


# ── 扫描 ──────────────────────────────────────────────────────────────────────
def iter_files(roots, cfg):
    skip = set(cfg.get("skip_dirs", []))
    for r in roots:
        r = Path(r)
        if r.is_file():
            yield r, r.parent
        elif r.is_dir():
            for dp, dns, fns in os.walk(r):
                dns[:] = sorted(d for d in dns if d not in skip)
                for fn in sorted(fns):
                    yield Path(dp) / fn, r
        else:
            raise GateError(f"path not found: {r}")


def _display(rel: str, masked: bool) -> str:
    if not masked:
        return rel
    # 整条相对路径打码：命中词可能在任一目录层（如 dist/<词>/index.html）
    return "<masked:%s>" % hashlib.sha256(rel.encode("utf-8")).hexdigest()[:8]


SELF_EXEMPT_RULES = {"private-path", "file-unknown-type"}
_SELF_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def scan(roots, cfg=None, terms=None, out=print) -> int:
    """返回 0=PASS，1=FAIL。任何异常由调用方转成 FAIL。"""
    cfg = cfg if cfg is not None else load_config()
    terms = terms if terms is not None else load_pii_terms()
    active = _active_checkers()
    files, failures = 0, 0
    for path, root in iter_files(roots, cfg):
        files += 1
        rel = os.path.relpath(path, root)
        data = path.read_bytes()
        results = {}
        for cid, fn in active.items():
            try:
                results[cid] = fn(path, rel, data, cfg, terms)
            except Exception as e:  # noqa: BLE001
                results[cid] = ("FAIL", [(0, "checker-error:%s:%s" % (cid, type(e).__name__))])
        # 闸脚本自身（与正在运行的这份逐字节相同）会命中自己的路径规则和 .py 类型：只豁免这两条规则，
        # 品牌 / PII / 数字等仍照常检查；内容被改过一个字节就不再算「自身」（2026-10-07 用户选方案 1）
        if path.name == Path(__file__).name and hashlib.sha256(data).hexdigest() == _SELF_SHA:
            for cid, res in list(results.items()):
                if isinstance(res, tuple) and len(res) == 2 and res[0] != PASS:
                    rest = [f for f in res[1] if f[1] not in SELF_EXEMPT_RULES]
                    if res[1] and not rest:
                        results[cid] = (PASS, [])
        masked = results.get("filename", ("FAIL", []))[0] != PASS
        disp = _display(rel, masked)
        for cid in REQUIRED_CHECKERS:
            res = results.get(cid)
            if res is None:
                out(f"FAIL {disp}:0 checker-missing:{cid}")
                failures += 1
                continue
            status, finds = res if isinstance(res, tuple) and len(res) == 2 else (None, [])
            if status != PASS:
                failures += 1
                if not finds:
                    out(f"FAIL {disp}:0 checker-no-explicit-pass:{cid}")
                for ln, rid in finds:
                    out(f"FAIL {disp}:{ln} {rid}")
    if files == 0:
        out("FAIL (no files to scan)")
        return 1
    if failures:
        out(f"GATE FAIL ({files} files, {failures} checker failures)")
        return 1
    out(f"GATE PASS ({files} files; checks: {', '.join(REQUIRED_CHECKERS)})")
    return 0


# ── 清单 ──────────────────────────────────────────────────────────────────────
def manifest(root: Path, map_path=None, out=print, cfg=None) -> int:
    cfg = cfg if cfg is not None else load_config()
    mp = Path(map_path) if map_path else DEFAULT_MAP
    srcmap = {}
    if mp.is_file():
        srcmap = json.loads(mp.read_text(encoding="utf-8")).get("files", {})
    root = Path(root)
    if not root.is_dir():
        raise GateError(f"manifest dir not found: {root}")
    out(f"# manifest {root}")
    out("path\tsize\tsha256\tsource\treview")
    for path, base in iter_files([root], cfg):
        rel = os.path.relpath(path, base)
        data = path.read_bytes()
        src = "-"
        for k, v in srcmap.items():
            if rel == k or rel.endswith("/" + k) or k.endswith("/" + rel):
                src = v
                break
        review = "需人工复核" if path.suffix.lower() in cfg["image_ext"] else "-"
        out(f"{rel}\t{len(data)}\t{hashlib.sha256(data).hexdigest()}\t{src}\t{review}")
    r = subprocess.run(["git", "-C", str(root), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if r.returncode == 0:
        top = r.stdout.strip()
        lg = subprocess.run(["git", "-C", top, "log", "--format=%an %ae"], capture_output=True, text=True)
        authors = sorted(set(x for x in lg.stdout.splitlines() if x.strip()))
        out(f"# git authors ({top}): " + ("; ".join(authors) if authors else "(no commits)"))
    else:
        out("# git authors: (not a git repo)")
    return 0


def _timeout(_s, _f):
    raise TimeoutError("site_gate timeout")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--paths", nargs="+")
    g.add_argument("--dist")
    g.add_argument("--manifest")
    ap.add_argument("--map", help="export 源映射 json（默认 ip/tools/.site_export_map.json）")
    ap.add_argument("--config", help="配置 json 路径（否则 env SITE_GATE_CONFIG 的 JSON 文本，否则同目录 site_gate.config.json）")
    ap.add_argument("--timeout", type=int, default=600)
    a = ap.parse_args(argv)
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, _timeout)
        signal.alarm(a.timeout)
    try:
        if a.manifest:
            return manifest(Path(a.manifest), a.map, cfg=load_config(a.config))
        roots = a.paths if a.paths else [a.dist]
        rc = scan(roots, cfg=load_config(a.config))
        return 0 if rc == 0 else 1
    except GateError as e:
        print(f"GATE FAIL (config/env): {e}")
        return 2
    except Exception as e:  # noqa: BLE001  任何意外 ⇒ FAIL，不打印异常消息（可能含原文）
        print(f"GATE FAIL (internal error: {type(e).__name__})")
        return 3
    finally:
        if hasattr(signal, "SIGALRM"):
            signal.alarm(0)


if __name__ == "__main__":
    sys.exit(main())
