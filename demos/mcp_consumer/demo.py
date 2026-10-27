"""Demo 2: an agent consuming three MCP servers at once, behind an allowlist with read-only scopes.

- hotel-tools-mcp (stage 7, guest role) for policy,
- the official filesystem server (@modelcontextprotocol/server-filesystem 1.0.0), whose only root is a fresh folder
  inside the lab (`.mcp-sandbox/run-<id>`) holding copies of the synthetic brochures, deleted after the run,
- Microsoft's Playwright server (@playwright/mcp 0.0.83), headless, `--isolated` (a fresh in-memory profile: no
  saved logins or cookies), allowed to open only a synthetic page served on 127.0.0.1.

Each server's own settings are the first fence (the filesystem root, Playwright's --allowed-origins). The gateway
is the second: it exposes only allowlisted tools from each server (no write_file, no browser_run_code_unsafe), checks
every URL against an origin allowlist, and audits every call with the run's trace ID, allowed or refused. The
"agent" here follows a fixed plan (prepare tomorrow's activity brief) so the demo needs no API key.

    python -m demos.mcp_consumer.demo          (needs Node.js for npx; Playwright uses the installed Chrome)
"""

import asyncio
import functools
import http.server
import json
import shutil
import sys
import tempfile
import threading
import uuid
from contextlib import AsyncExitStack
from pathlib import Path
from urllib.parse import urlparse

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from demos.mcp_server.demo import make_keys, server_params
from protolab.audit import Audit

ROOT = Path(__file__).resolve().parents[2]
BROCHURES = ROOT / "data" / "brochures"  # the synthetic originals; the server only ever sees copies
SANDBOX_PARENT = ROOT / ".mcp-sandbox"  # git-ignored; one fresh folder per run, removed afterwards
SITE = ROOT / "data" / "site"
FILESYSTEM_PKG = "@modelcontextprotocol/server-filesystem@1.0.0"  # pinned: published 2026-10-11
PLAYWRIGHT_PKG = "@playwright/mcp@0.0.83"  # pinned: published 2026-09-28

ALLOWLIST = {
    "hotel": {"search_policy", "list_activities"},
    "files": {"list_allowed_directories", "list_directory", "read_text_file"},  # read-only: no write/edit/move
    "browser": {"browser_navigate", "browser_snapshot"},  # no evaluate, no run_code_unsafe, no file upload
}


class Refused(PermissionError):
    pass


class Gateway:
    """Allowlisted tools across several MCP sessions, with an origin allowlist for URLs and an audit of every call."""

    def __init__(self, sessions: dict, allowlist: dict, allowed_origins: set[str], audit: Audit):
        self.sessions, self.allowlist, self.origins, self.audit = sessions, allowlist, allowed_origins, audit
        self.offered: dict[str, list[str]] = {}

    async def discover(self) -> dict[str, list[str]]:
        for name, session in self.sessions.items():
            listed = sorted(t.name for t in (await session.list_tools()).tools)
            self.offered[name] = [t for t in listed if t in self.allowlist[name]]
            hidden = sorted(set(listed) - set(self.offered[name]))
            self.audit.record("gateway", "tools_discovered", server=name, exposed=self.offered[name], hidden=hidden)
        return self.offered

    def check(self, server: str, tool: str, args: dict) -> None:
        if tool not in self.allowlist.get(server, set()):
            raise Refused(f"{server}.{tool} is not on the allowlist")
        url = args.get("url")
        if url is not None:
            u = urlparse(url)
            if f"{u.scheme}://{u.netloc}" not in self.origins:
                raise Refused(f"{u.scheme}://{u.netloc} is not an allowed origin")

    async def call(self, server: str, tool: str, args: dict) -> str:
        try:
            self.check(server, tool, args)
        except Refused as exc:
            self.audit.record("gateway", "refused", server=server, tool=tool, why=str(exc))
            raise
        result = await self.sessions[server].call_tool(tool, args)
        text = "".join(getattr(c, "text", "") for c in result.content)
        self.audit.record("gateway", "called", server=server, tool=tool, ok=not result.is_error, chars=len(text))
        return text


def serve_site() -> tuple[http.server.ThreadingHTTPServer, str]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def make_sandbox() -> Path:
    """A fresh folder inside the lab, holding copies of the synthetic brochures: the filesystem server's only root."""
    sandbox = SANDBOX_PARENT / f"run-{uuid.uuid4().hex[:8]}"
    sandbox.mkdir(parents=True)
    for f in BROCHURES.glob("*.md"):
        shutil.copy2(f, sandbox / f.name)
    return sandbox


async def open_sessions(stack: AsyncExitStack, runtime: Path, origin: str, sandbox: Path) -> dict:
    npx = shutil.which("npx")
    if not npx:
        raise RuntimeError("npx not found: install Node.js to run the filesystem and Playwright servers")
    key = make_keys(runtime)["guest"]
    params = {
        "hotel": server_params(key, runtime),
        "files": StdioServerParameters(command=npx, args=["-y", FILESYSTEM_PKG, str(sandbox)]),
        "browser": StdioServerParameters(command=npx, args=["-y", PLAYWRIGHT_PKG, "--headless", "--isolated",
                                                            "--browser", "chrome", "--allowed-origins", origin]),
    }  # fmt: skip
    sessions = {}
    for name, p in params.items():
        read, write = await stack.enter_async_context(stdio_client(p))
        sessions[name] = await stack.enter_async_context(ClientSession(read, write))
        await sessions[name].initialize()
    return sessions


async def main_async() -> dict:
    audit = Audit()
    httpd, origin = serve_site()
    sandbox = make_sandbox()
    try:
        with tempfile.TemporaryDirectory(prefix="mcp-consumer-") as tmp:  # the hotel server's keys, not the files
            async with AsyncExitStack() as stack:
                gw = Gateway(await open_sessions(stack, Path(tmp), origin, sandbox), ALLOWLIST, {origin}, audit)
                offered = await gw.discover()
                brief = {
                    "allowed_directories": await gw.call("files", "list_allowed_directories", {}),
                    "files": await gw.call("files", "list_directory", {"path": str(sandbox)}),
                    "brochure": await gw.call("files", "read_text_file",
                                              {"path": str(sandbox / "beach-resort-activities.md")}),
                    "policy": json.loads(await gw.call("hotel", "search_policy",
                                                       {"question": "kids club ages", "property": "beach-resort"})),
                }  # fmt: skip
                # The server's own fence: an allowlisted read tool, but a path outside its root (the lab's README).
                brief["outside_root"] = await gw.call("files", "read_text_file", {"path": str(ROOT / "README.md")})
                await gw.call("browser", "browser_navigate", {"url": f"{origin}/events.html"})
                brief["events_page"] = await gw.call("browser", "browser_snapshot", {})
                refused = []
                for server, tool, args in (
                    ("files", "write_file", {"path": str(sandbox / "x.md"), "content": "planted"}),
                    ("browser", "browser_run_code_unsafe", {"code": "1+1"}),
                    ("browser", "browser_navigate", {"url": "https://example.com/"}),
                ):
                    try:
                        await gw.call(server, tool, args)
                    except Refused as exc:
                        refused.append(str(exc))
                brief["sandbox_files_after"] = sorted(p.name for p in sandbox.iterdir())
    finally:
        httpd.shutdown()
        shutil.rmtree(sandbox, ignore_errors=True)
    return {"offered": offered, "brief": brief, "refused": refused, "sandbox": str(sandbox),
            "sandbox_removed": not sandbox.exists(), "audit": audit.events}  # fmt: skip


def main() -> int:
    out = asyncio.run(main_async())
    for server, tools in out["offered"].items():
        print(f"{server}: exposing {tools}")
    print("filesystem root (server's own answer):", " ".join(out["brief"]["allowed_directories"].split()))
    print("brochure:", out["brief"]["brochure"].splitlines()[2])
    print("read outside the root (server's answer):", out["brief"]["outside_root"].strip()[:120])
    print("policy:", out["brief"]["policy"]["passages"][0]["section"])
    print("events page:", "turtle talk" in out["brief"]["events_page"].lower())
    for why in out["refused"]:
        print("refused:", why)
    after, removed = out["brief"]["sandbox_files_after"], out["sandbox_removed"]
    print("files in the sandbox after the run:", after, "| sandbox removed:", removed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
