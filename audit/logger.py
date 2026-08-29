"""
Audit Trail Logger

Append-only, tamper-evident log of every decision the Sentinel pipeline makes.
This is the literal "show the audit trail" requirement from the track brief:
every money-affecting decision must be traceable back to the exact inputs
(risk components, exposure numbers, reason codes) that produced it, and that
record must not be silently editable after the fact.

Design choices, and why:

1. JSONL, one record per line, opened in append ("a") mode only.
   No update/delete method is exposed on purpose - an audit trail that can be
   edited in place isn't an audit trail. If a record is wrong, you log a new
   corrective record; you don't rewrite history.

2. Hash-chained records (like a minimal blockchain ledger). Each record
   stores a SHA-256 hash of its own content plus the previous record's hash.
   verify_integrity() walks the chain and recomputes every hash - if a single
   byte of any past record changes (or a record is deleted from the middle
   of the file), the chain breaks at that point and verify_integrity() tells
   you exactly where. This turns "we have a log file" into "we can prove
   this log hasn't been tampered with," which is a meaningfully stronger
   claim for a risk/compliance audience.

3. The logger does NOT reshape the pipeline's output. It logs
   FraudSentinelPipeline.process_window()'s return value as-is, wrapped with
   a sequence number, a wall-clock logged_at timestamp, and the hash chain
   fields. Keeping the schema untouched means the dashboard (Day 7) and the
   eval harness (Day 6, Step 2+) can consume audit records and live pipeline
   output interchangeably.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


GENESIS_HASH = "0" * 64


def _canonical_json(obj: Any) -> str:
    """Deterministic JSON serialization so the same content always hashes
    the same way, regardless of dict key insertion order."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _hash_record(sequence_number: int, logged_at: str, prev_hash: str, payload: Dict[str, Any]) -> str:
    material = _canonical_json(
        {
            "sequence_number": sequence_number,
            "logged_at": logged_at,
            "prev_hash": prev_hash,
            "payload": payload,
        }
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


@dataclass
class IntegrityReport:
    ok: bool
    record_count: int
    broken_at_sequence: Optional[int] = None
    reason: Optional[str] = None


class AuditTrailLogger:
    """Append-only, hash-chained JSONL logger for pipeline decision records."""

    def __init__(self, log_path: str | Path):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    # -- writing -----------------------------------------------------------

    def _last_hash(self) -> str:
        """Read just the last line to get the current chain tip. Cheap even
        for large logs since we only need the final line."""
        last_line = None
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    last_line = line
        if last_line is None:
            return GENESIS_HASH
        return json.loads(last_line)["record_hash"]

    def log(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Append one pipeline output (e.g. FraudSentinelPipeline.process_window's
        return value) as a new, hash-chained record. Returns the full record
        that was written, including its sequence number and hash.
        """
        prev_hash = self._last_hash()
        sequence_number = self._count_records()
        logged_at = datetime.now(timezone.utc).isoformat()

        record_hash = _hash_record(sequence_number, logged_at, prev_hash, payload)

        record = {
            "sequence_number": sequence_number,
            "logged_at": logged_at,
            "prev_hash": prev_hash,
            "record_hash": record_hash,
            "payload": payload,
        }

        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(_canonical_json(record) + "\n")

        return record

    # -- reading -------------------------------------------------------------

    def _count_records(self) -> int:
        count = 0
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count

    def __len__(self) -> int:
        return self._count_records()

    def read_all(self) -> List[Dict[str, Any]]:
        """Return every record in the log, in order. Read-only - there is
        deliberately no update/delete counterpart."""
        records: List[Dict[str, Any]] = []
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records

    def iter_records(self) -> Iterator[Dict[str, Any]]:
        """Streaming variant of read_all, for logs too large to hold in memory."""
        with self.log_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    # -- integrity -----------------------------------------------------------

    def verify_integrity(self) -> IntegrityReport:
        """
        Walk the full chain and recompute every hash. Returns ok=True only if
        every record's stored hash matches a fresh recomputation AND every
        record's prev_hash matches the previous record's actual hash.

        This catches: a record edited in place, a record deleted from the
        middle of the file, records reordered, or a record inserted out of
        band (e.g. someone hand-editing the JSONL file).
        """
        records = self.read_all()
        expected_prev = GENESIS_HASH

        for idx, record in enumerate(records):
            if record.get("sequence_number") != idx:
                return IntegrityReport(
                    ok=False,
                    record_count=len(records),
                    broken_at_sequence=idx,
                    reason=(
                        f"expected sequence_number={idx}, found "
                        f"{record.get('sequence_number')} (record reordered or "
                        f"deleted)"
                    ),
                )

            if record.get("prev_hash") != expected_prev:
                return IntegrityReport(
                    ok=False,
                    record_count=len(records),
                    broken_at_sequence=idx,
                    reason=(
                        f"prev_hash mismatch at sequence {idx}: chain link to "
                        f"prior record is broken"
                    ),
                )

            recomputed = _hash_record(
                record["sequence_number"],
                record["logged_at"],
                record["prev_hash"],
                record["payload"],
            )
            if recomputed != record.get("record_hash"):
                return IntegrityReport(
                    ok=False,
                    record_count=len(records),
                    broken_at_sequence=idx,
                    reason=(
                        f"record_hash mismatch at sequence {idx}: content was "
                        f"modified after logging"
                    ),
                )

            expected_prev = record["record_hash"]

        return IntegrityReport(ok=True, record_count=len(records))