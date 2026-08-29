import json
import pytest
from detection.sentinel_pipeline import FraudSentinelPipeline


def test_pipeline_normal_day():
    pipeline = FraudSentinelPipeline()
    with open("data/generated/normal_day.json", "r") as f:
        data = json.load(f)
    
    txs = data if isinstance(data, list) else data.get("transactions", [])
    res = pipeline.process_window(txs[:100], baseline_stats={"mean_velocity": 4.0})
    
    assert res["decision"] in ["MONITOR", "FLAG_FOR_REVIEW"]
    assert res["risk_assessment"]["overall_risk_score"] < 0.50


def test_pipeline_flash_sale_differentiation():
    pipeline = FraudSentinelPipeline()
    with open("data/generated/flash_sale.json", "r") as f:
        data = json.load(f)
    
    txs = data if isinstance(data, list) else data.get("transactions", [])
    res = pipeline.process_window(txs[:150], baseline_stats={"mean_velocity": 1.0})
    
    # Flash sale has high velocity, but low ring score
    assert res["risk_assessment"]["components"]["ring_score"] < 0.65
    # Should never execute an unwarranted permanent HOLD on a legitimate promotion
    assert res["decision"] != "HOLD_FOR_REVIEW"


def test_pipeline_fraud_ring_escalation():
    pipeline = FraudSentinelPipeline()
    with open("data/generated/mixed_fraud.json", "r") as f:
        data = json.load(f)
        
    txs = data if isinstance(data, list) else data.get("transactions", [])
    res = pipeline.process_window(txs, baseline_stats={"mean_velocity": 2.0})
    
    # Must catch high-risk coordinated fraud ring
    assert res["risk_assessment"]["overall_risk_score"] >= 0.70
    assert res["exposure_metrics"]["expected_fraud_exposure"] > 0
    assert res["decision"] in ["FLAG_FOR_REVIEW", "HOLD_FOR_REVIEW"]
    assert len(res["risk_assessment"]["reason_codes"]) > 0