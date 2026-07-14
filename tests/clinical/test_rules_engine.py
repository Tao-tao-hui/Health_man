"""风险预警规则引擎测试"""

import pytest
from scripts.clinical.rules_engine import RulesEngine
from scripts.hardware.models import ProcessedData


def test_visceral_fat_high_risk():
    """测试内脏脂肪高危预警"""
    engine = RulesEngine()

    data = ProcessedData(
        visceral_fat_level=16,
        age=45,
        sex="M"
    )

    alerts = engine.evaluate(data)

    assert len(alerts) >= 1
    visceral_alerts = [a for a in alerts if a['id'] == 'rule_001']
    assert len(visceral_alerts) == 1
    assert visceral_alerts[0]['severity'] == 'high'


def test_spo2_low_alert():
    """测试血氧偏低预警"""
    engine = RulesEngine()

    data = ProcessedData(
        spo2=93.0,
        pi=1.5
    )

    alerts = engine.evaluate(data)

    spo2_alerts = [a for a in alerts if a['id'] == 'rule_002']
    assert len(spo2_alerts) == 1
    assert spo2_alerts[0]['severity'] == 'medium'


def test_no_alerts():
    """测试无预警情况"""
    engine = RulesEngine()

    data = ProcessedData(
        body_fat_rate=18.0,
        bmi=22.0,
        visceral_fat_level=8,
        spo2=97.0,
        heart_rate=70.0,
        age=35,
        sex="M"
    )

    alerts = engine.evaluate(data)

    assert len(alerts) == 0


def test_obesity_risk():
    """测试肥胖风险预警"""
    engine = RulesEngine()

    data = ProcessedData(
        bmi=28.5,
        body_fat_rate=28.0,
        age=35,
        sex="M"
    )

    alerts = engine.evaluate(data)

    obesity_alerts = [a for a in alerts if a['id'] == 'rule_004']
    assert len(obesity_alerts) == 1


def test_heart_rate_abnormal_high():
    """测试心率过高预警"""
    engine = RulesEngine()

    data = ProcessedData(
        heart_rate=110.0
    )

    alerts = engine.evaluate(data)

    hr_alerts = [a for a in alerts if a['id'] == 'rule_003']
    assert len(hr_alerts) == 1


def test_heart_rate_abnormal_low():
    """测试心率过低预警"""
    engine = RulesEngine()

    data = ProcessedData(
        heart_rate=45.0
    )

    alerts = engine.evaluate(data)

    hr_alerts = [a for a in alerts if a['id'] == 'rule_003']
    assert len(hr_alerts) == 1


def test_multiple_alerts():
    """测试多个预警同时触发"""
    engine = RulesEngine()

    data = ProcessedData(
        visceral_fat_level=16,
        spo2=92.0,
        heart_rate=105.0,
        age=45,
        sex="M"
    )

    alerts = engine.evaluate(data)

    assert len(alerts) >= 2