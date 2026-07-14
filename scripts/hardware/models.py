"""数据模型定义

定义芯片原始数据、处理后数据和健康评估结果的数据结构
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict


@dataclass
class HardwareData:
    """芯片原始数据"""

    bia_impedance: Optional[int] = None      # S3008T阻抗值(Ω)
    spo2: Optional[int] = None               # BMH08002血氧值(%)
    heart_rate: Optional[int] = None         # BMH08002心率(BPM)
    pi: Optional[float] = None               # BMH08002灌注指数(%)
    hrv: Optional[int] = None                # BMH08002心率变异性(ms)
    ppg_waveform: Optional[List[int]] = None # BMH08002脉搏波数据
    timestamp: Optional[datetime] = None     # 采样时间戳
    signal_quality: Optional[float] = None   # 信号质量评分(0~1)
    device_id: Optional[str] = None          # 设备标识符


@dataclass
class ProcessedData:
    """处理后的健康数据"""

    body_fat_rate: Optional[float] = None    # 体脂率(%)
    bmi: Optional[float] = None              # BMI
    visceral_fat_level: Optional[int] = None # 内脏脂肪等级
    muscle_mass: Optional[float] = None      # 肌肉量(kg)
    skeletal_muscle: Optional[float] = None  # 骨骼肌量(kg)
    bone_mass: Optional[float] = None        # 骨量(kg)
    water_rate: Optional[float] = None       # 水分率(%)
    bmr: Optional[int] = None                # 基础代谢(Kcal)
    protein_rate: Optional[float] = None     # 蛋白质率(%)

    spo2: Optional[float] = None             # 血氧(%)
    heart_rate: Optional[float] = None       # 心率(BPM)
    pi: Optional[float] = None               # 灌注指数(%)
    hrv: Optional[float] = None              # 心率变异性(ms)

    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    user_type: str = "Normal"

    data_quality: Optional[float] = None     # 数据质量评分(0~1)
    measurement_time: Optional[datetime] = None


@dataclass
class HealthAssessment:
    """健康评估结果"""

    overall_score: Optional[int] = None              # 综合健康评分(0~100)
    component_scores: Optional[Dict[str, int]] = None # 各维度评分
    alerts: Optional[List[Dict]] = field(default_factory=list)       # 风险预警列表
    recommendations: Optional[List[str]] = field(default_factory=list) # 改善建议列表
    trend_analysis: Optional[Dict] = None            # 趋势分析
    evidence_level: Optional[str] = None             # 证据等级
    disclaimer: str = "本评估结果为保健级参考值，不可用于临床诊断。"