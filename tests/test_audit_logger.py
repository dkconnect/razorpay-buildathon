import json
import pytest
from audit.logger import AuditTrailLogger, GENESIS_HASH


@pytest.fixture
def logger(tmp_path):
    return AuditTrailLogger(tmp_path / "audit.jsonl")


def _fake_record(decision="MONITOR", risk=0.1):
    return {
        "alert_id": "ALT_TEST",
        "decision": decision,
        "risk_assessment": {"overall_risk_score": risk},
    }


def test_log_appends_and_returns_record(logger):
    record = logger.log(_fake_record())
    assert record["sequence_number"] == 0
    assert record["prev_hash"] == GENESIS_HASH
    assert record["payload"]["decision"] == "MONITOR"
    assert len(logger) == 1


def test_chain_links_sequential_records(logger):
    r0 = logger.log(_fake_record(decision="MONITOR"))
    r1 = logger.log(_fake_record(decision="FLAG_FOR_REVIEW"))
    r2 = logger.log(_fake_record(decision="HOLD_FOR_REVIEW"))

    assert r1["prev_hash"] == r0["record_hash"]
    assert r2["prev_hash"] == r1["record_hash"]
    assert len(logger) == 3


def test_verify_integrity_clean_log(logger):
    for i in range(5):
        logger.log(_fake_record(decision=f"D{i}"))
    report = logger.verify_integrity()
    assert report.ok
    assert report.record_count == 5
    assert report.broken_at_sequence is None


def test_verify_integrity_detects_content_tamper(logger):
    logger.log(_fake_record(decision="MONITOR"))
    logger.log(_fake_record(decision="HOLD_FOR_REVIEW"))
    logger.log(_fake_record(decision="MONITOR"))

    # tamper with record 1's content without recomputing its hash
    lines = logger.log_path.read_text().splitlines()
    tampered = json.loads(lines[1])
    tampered["payload"]["decision"] = "MONITOR"  # attacker downgrades a real alert
    lines[1] = json.dumps(tampered)
    logger.log_path.write_text("\n".join(lines) + "\n")

    report = logger.verify_integrity()
    assert not report.ok
    assert report.broken_at_sequence == 1
    assert "modified" in report.reason


def test_verify_integrity_detects_deleted_record(logger):
    for i in range(4):
        logger.log(_fake_record(decision=f"D{i}"))

    lines = logger.log_path.read_text().splitlines()
    del lines[1]  # remove a record from the middle of the chain
    logger.log_path.write_text("\n".join(lines) + "\n")

    report = logger.verify_integrity()
    assert not report.ok
    assert report.broken_at_sequence == 1


def test_read_all_matches_logged_order(logger):
    decisions = ["MONITOR", "FLAG_FOR_REVIEW", "HOLD_FOR_REVIEW"]
    for d in decisions:
        logger.log(_fake_record(decision=d))

    records = logger.read_all()
    assert [r["payload"]["decision"] for r in records] == decisions


def test_logs_real_pipeline_output_unmodified(logger):
    """The logger must not reshape the pipeline's own output schema."""
    from detection.sentinel_pipeline import FraudSentinelPipeline
    import json as _json

    pipeline = FraudSentinelPipeline()
    with open("data/generated/mixed_fraud.json") as f:
        data = _json.load(f)
    txs = data if isinstance(data, list) else data.get("transactions", [])

    result = pipeline.process_window(txs[:150], baseline_stats={"mean_velocity": 1.0})
    record = logger.log(result)

    assert record["payload"] == result
    assert record["payload"].keys() == result.keys()