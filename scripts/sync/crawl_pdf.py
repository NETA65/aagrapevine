"""PDF inspection for the crawler (scripts/sync/crawl.py).

  * head_from_response()   – status / size / type / Last-Modified from any HTTP response
  * download_pdf()         – streaming GET with a size cap and a time cap
  * analyze_pdf()          – pypdfium2: metadata title, page count, text of pages 1-2 (also page by
                             page, so a bilingual sheet can be told from a one-language document),
                             and a small WebP thumbnail of page 1 (Pillow)
  * analyze_pdf_isolated() – analyze_pdf() in a separate process with a time limit and, on Linux, a
                             memory limit: a file that crashes or hangs the PDF reader costs that one
                             document, never the crawl (the crawler uses this one)

Nothing here raises for a bad file: every function returns an error string instead.
Personal metadata (Author, Creator…) is deliberately NOT read — AA anonymity.

    python -m scripts.sync.crawl_pdf --analyze [--thumb FILE] [--memory-mb N] < file.pdf
        (the child process: prints analyze_pdf()'s result as one line of JSON)
"""
from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
import time
from email.utils import parsedate_to_datetime
from pathlib import Path

from .common import ROOT, clean_text, now_iso, to_iso

THUMB_WIDTH = 360          # px — cards show ~180-240 px, so this is sharp on retina screens
THUMB_QUALITY = 65         # WebP quality → ~8-25 KB per thumbnail
THUMB_MAX_RATIO = 1.6      # very tall first pages are cropped to the top (height ≤ 1.6 × width)
TEXT_PAGES = 2             # pages of text sampled for language / title detection
TEXT_MAX_CHARS = 4000
PARSE_TIMEOUT_S = 60       # one document's analysis (a separate process; usually 1-3 s) …
PARSE_MEMORY_MB = 2048     # … and the memory it may use (Linux only: RLIMIT_DATA, see limit_memory)


def http_date_iso(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return to_iso(parsedate_to_datetime(value))
    except (TypeError, ValueError, IndexError, OverflowError):
        return None


def head_from_response(r) -> dict:
    """Compact record of an HTTP response for a PDF (works for HEAD and streamed GET)."""
    h = r.headers
    size = h.get("Content-Length")
    try:
        size = int(size) if size is not None else None
    except ValueError:
        size = None
    # Content-Length of a compressed response is not the file size
    if h.get("Content-Encoding", "").lower() not in ("", "identity"):
        size = None
    return {
        "status": r.status_code,
        "size": size,
        "type": (h.get("Content-Type") or "").split(";")[0].strip().lower() or None,
        "last_modified": http_date_iso(h.get("Last-Modified")),
        "final_url": r.url if getattr(r, "url", None) else None,
        "checked_at": now_iso(),
    }


def download_pdf(session, url: str, *, max_bytes: int, max_seconds: float = 90.0,
                 timeout=(10, 30)) -> tuple[dict, bytes | None, str | None, bool]:
    """GET a PDF with caps. Returns (head, data, error, final).

    `final` = True when retrying later is pointless (404/410, too large, not a PDF)."""
    r = session.get(url, stream=True, timeout=timeout,
                    headers={"Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.5"})
    if r is None:
        return {"status": None, "checked_at": now_iso()}, None, "unreachable", False
    head = head_from_response(r)
    try:
        if r.status_code in (404, 410):
            return head, None, f"http {r.status_code}", True
        if r.status_code != 200:
            return head, None, f"http {r.status_code}", False
        if head.get("type") and "html" in head["type"]:
            return head, None, "not-pdf", True
        if head.get("size") and head["size"] > max_bytes:
            return head, None, "too-large", True
        buf = io.BytesIO()
        t0 = time.monotonic()
        for chunk in r.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            buf.write(chunk)
            if buf.tell() > max_bytes:
                return head, None, "too-large", True
            if time.monotonic() - t0 > max_seconds:
                return head, None, "slow-download", False
        data = buf.getvalue()
    except Exception as e:  # connection reset mid-stream, decode errors…
        return head, None, f"download: {type(e).__name__}", False
    finally:
        try:
            r.close()
        except Exception:
            pass
    if b"%PDF" not in data[:1024]:
        return head, None, "not-pdf", True
    if not head.get("size"):
        head["size"] = len(data)
    return head, data, None, False


def analyze_pdf(data: bytes, thumb_file: Path | None) -> dict:
    """Read a PDF in memory. Returns details dict:
        {title, pages, text, page_texts, error, final, thumb_written}
    `text` / `page_texts` are the (not stored) text sample of the first pages, joined / one per page;
    callers keep only derived values."""
    out: dict = {"title": None, "pages": None, "text": "", "page_texts": [], "error": None, "final": False,
                 "thumb_written": False}
    try:
        import pypdfium2 as pdfium
    except Exception as e:  # pragma: no cover - dependency missing
        out.update(error=f"pypdfium2 missing: {e}", final=False)
        return out
    pdf = None
    try:
        try:
            pdf = pdfium.PdfDocument(data)
        except pdfium.PdfiumError as e:
            msg = str(e).lower()
            out.update(error="encrypted" if "password" in msg else "invalid-pdf", final=True)
            return out
        try:
            meta = pdf.get_metadata_dict(skip_empty=True)
        except Exception:
            meta = {}
        out["title"] = clean_text(meta.get("Title") or "") or None
        out["pages"] = len(pdf)
        if not out["pages"]:
            out.update(error="no-pages", final=True)
            return out
        # --- text sample (first pages) ---------------------------------------------------
        parts = []
        for i in range(min(TEXT_PAGES, out["pages"])):
            page = textpage = None
            try:
                page = pdf[i]
                textpage = page.get_textpage()
                parts.append(textpage.get_text_range() or "")
            except Exception:
                pass
            finally:
                for obj in (textpage, page):
                    try:
                        obj and obj.close()
                    except Exception:
                        pass
        out["text"] = "\n".join(parts).replace("\r\n", "\n").replace("\r", "\n")[:TEXT_MAX_CHARS]
        out["page_texts"] = [p[:TEXT_MAX_CHARS] for p in parts]
        # --- thumbnail of page 1 ---------------------------------------------------------
        if thumb_file is not None:
            page = bitmap = None
            try:
                page = pdf[0]
                w, h = page.get_size()
                scale = max(0.05, min(4.0, THUMB_WIDTH / max(w, 1)))
                bitmap = page.render(scale=scale)
                img = bitmap.to_pil()
                if img.mode != "RGB":
                    img = img.convert("RGB")
                if img.height > img.width * THUMB_MAX_RATIO:
                    img = img.crop((0, 0, img.width, int(img.width * THUMB_MAX_RATIO)))
                thumb_file.parent.mkdir(parents=True, exist_ok=True)
                tmp = thumb_file.with_name(thumb_file.name + ".tmp")   # *.tmp is git-ignored
                img.save(tmp, "WEBP", quality=THUMB_QUALITY, method=6)
                tmp.replace(thumb_file)
                out["thumb_written"] = True
            except Exception as e:
                out["error"] = f"thumb: {type(e).__name__}"
            finally:
                for obj in (bitmap, page):
                    try:
                        obj and obj.close()
                    except Exception:
                        pass
    except Exception as e:  # anything unexpected inside pdfium
        out.update(error=f"analyze: {type(e).__name__}: {e}"[:120], final=False)
    finally:
        try:
            pdf and pdf.close()
        except Exception:
            pass
    return out


# --------------------------------------------------------------------------- the reader in a child process
def limit_memory(mb: int) -> bool:
    """Cap this process's memory at `mb` MB. Linux: RLIMIT_DATA — the heap and every private writable
    mapping, i.e. memory really in use; address space that is only reserved (as some allocators do up
    front) does not count, so a limit on it (RLIMIT_AS) could break the reader for every file.
    An allocation beyond the cap fails (Python: MemoryError) instead of the machine running out of
    memory. Elsewhere (Windows) nothing happens → False."""
    if not sys.platform.startswith("linux") or not mb or mb <= 0:
        return False
    try:
        import resource
        _soft, hard = resource.getrlimit(resource.RLIMIT_DATA)
        want = int(mb) * 1024 * 1024
        if hard != resource.RLIM_INFINITY:
            want = min(want, hard)
        resource.setrlimit(resource.RLIMIT_DATA, (want, hard))
        return True
    except (ImportError, ValueError, OSError):
        return False


def _child_argv(thumb_file: Path | None, memory_mb: int | None) -> list[str]:
    argv = [sys.executable, "-m", "scripts.sync.crawl_pdf", "--analyze"]
    if thumb_file is not None:
        argv += ["--thumb", str(thumb_file)]
    if memory_mb:
        argv += ["--memory-mb", str(int(memory_mb))]
    return argv


def analyze_pdf_isolated(data: bytes, thumb_file: Path | None, *, timeout: float = PARSE_TIMEOUT_S,
                         memory_mb: int | None = PARSE_MEMORY_MB) -> dict:
    """analyze_pdf() in a child process (the file goes in on stdin, the result comes back as JSON), so
    a document that crashes the PDF reader, hangs it or eats all memory never takes the crawl with it.
    Same result as analyze_pdf(); when the child gives none, `error` is "parse: no result after 60 s",
    "parse: crashed (out of memory)", "parse: crashed (exit code -11)"… and `final` False (tried again
    after the crawler's back-off). The child is killed at `timeout` — also when the crawl itself is
    stopped meanwhile (subprocess.run kills it on any exception)."""
    out: dict = {"title": None, "pages": None, "text": "", "page_texts": [], "error": None, "final": False,
                 "thumb_written": False}
    try:
        p = subprocess.run(_child_argv(thumb_file, memory_mb), input=data, capture_output=True,
                           timeout=max(1.0, timeout), cwd=str(ROOT))
    except subprocess.TimeoutExpired:
        out["error"] = f"parse: no result after {timeout:.0f} s"
        return out
    except OSError as e:          # could not start the child at all
        out["error"] = f"parse: {type(e).__name__}"
        return out
    if p.returncode != 0:
        tail = (p.stderr or b"")[-2000:].decode("utf-8", "replace")
        why = "out of memory" if "MemoryError" in tail else f"exit code {p.returncode}"
        out["error"] = f"parse: crashed ({why})"
        return out
    try:
        res = json.loads((p.stdout or b"").decode("utf-8", "replace").strip().splitlines()[-1])
        if not isinstance(res, dict):
            raise ValueError("not an object")
    except (ValueError, IndexError):
        out["error"] = "parse: no result"
        return out
    return {**out, **res}


def _child_main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m scripts.sync.crawl_pdf",
                                 description="Read one PDF from stdin; print analyze_pdf()'s result as JSON.")
    ap.add_argument("--analyze", action="store_true", required=True)
    ap.add_argument("--thumb", default=None, help="write the page-1 thumbnail here (WebP)")
    ap.add_argument("--memory-mb", type=int, default=None, help="memory cap (Linux)")
    args = ap.parse_args(argv)
    if args.memory_mb:
        limit_memory(args.memory_mb)      # before the file is read: it counts too
    data = sys.stdin.buffer.read()
    res = analyze_pdf(data, Path(args.thumb) if args.thumb else None)
    # one ASCII line, last on stdout (anything printed before it is ignored)
    sys.stdout.buffer.write(b"\n" + json.dumps(res, ensure_ascii=True).encode("ascii") + b"\n")
    sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(_child_main())
