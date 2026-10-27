"""The parts of Agora this lab uses: the protocol document, its metadata and its hash.

Copied from agora-protocol 0.2.0 (`agora/common/core.py` and `agora/utils.py`, MIT License, Copyright (c) 2024 Agora
Protocol), with only the network fetch left out. The package itself can't be imported without its whole stack:
`import agora` loads its LangChain, LangGraph and RestrictedPython integrations, and on 2026-10-27 pip-audit listed 18
known vulnerabilities in the versions it pins (langchain 0.3, langgraph 0.2, restrictedpython 7.4). This demo needs
none of that, so it carries these few functions instead (docs/DECISIONS.md, decision 8).

MIT License text for this file's copied parts: https://opensource.org/license/mit
"""

import base64
import hashlib

import yaml


def extract_substring(text: str, start_tag: str, end_tag: str, include_tags: bool = True) -> str | None:
    start_position = text.lower().find(start_tag.lower())
    end_position = text.lower().find(end_tag.lower(), start_position + len(start_tag))
    if start_position == -1 or end_position == -1:
        return None
    if include_tags:
        return text[start_position : end_position + len(end_tag)].strip()
    return text[start_position + len(start_tag) : end_position].strip()


def compute_hash(s: str) -> str:
    """Agora's protocol identity: SHA-1 of the document, base64."""
    return base64.b64encode(hashlib.sha1(s.encode()).digest()).decode("ascii")  # noqa: S324 - Agora's identifier


def extract_metadata(text: str) -> dict:
    metadata = yaml.safe_load(extract_substring(text, "---", "---", include_tags=False) or "") or {}
    return {
        "name": metadata.get("name", "Unnamed protocol"),
        "description": metadata.get("description", "No description provided"),
        "multiround": metadata.get("multiround", False),
    }


class Protocol:
    """A protocol document with its sources and metadata (front matter)."""

    def __init__(self, protocol_document: str, sources: list[str], metadata: dict | None):
        self.protocol_document = protocol_document
        self.sources = sources
        self.metadata = metadata if metadata is not None else extract_metadata(protocol_document)

    @property
    def hash(self) -> str:
        return compute_hash(self.protocol_document)
