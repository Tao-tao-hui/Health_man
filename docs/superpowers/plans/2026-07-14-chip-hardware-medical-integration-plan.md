# 芯片硬件医疗赋能系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现芯片硬件（S3008T体脂测量芯片 + BMH08002血氧测量模组）与临床知识的集成系统，构建大健康领域的智能健康监测平台。

**Architecture:** 采用四层架构：硬件感知层（芯片通信协议）→ 数据处理层（数据解析与算法计算）→ 临床知识层（标准知识库与评分算法）→ 应用服务层（健康评估输出）。各层通过定义良好的接口解耦，支持独立演进。

**Tech Stack:** Python 3.10+, pytest, UART/IIC通信, CRC-8校验, HTTP/Web API

## Global Constraints

- 所有输出均为保健级参考值，不可用于临床诊断
- S3008T协议与现有代码不兼容，需按权威协议规范重写
- BMH08002需确认V1.6版本固件
- SpO₂范围以性能指标70~99%为准，PI范围以通信字节0~20.0%为准
- 综合健康评分 = 体成分评分(50%) + 心血管评分(50%)

---

## 文件结构规划

```
scripts/hardware/
├── __init__.py
├── s3008t/
│   ├── __init__.py
│   ├── protocol.py          # S3008T通信协议实现
│   ├── crc8.py              # CRC-8校验算法
│   └── transport.py         # UART通信传输层
├── bmh08002/
│   ├── __init__.py
│   ├── protocol.py          # BMH08002通信协议实现
│   ├── uart_protocol.py     # UART协议实现
│   └── i2c_protocol.py      # IIC协议实现
├── models.py                # 数据模型定义
└── factory.py               # 硬件设备工厂

scripts/data_processing/
├── __init__.py
├── bia_processor.py         # 体成分数据处理
├── spo2_processor.py        # 血氧数据处理
├── quality_assessment.py    # 信号质量评估
└── time_series.py           # 时间序列数据处理

scripts/clinical/
├── __init__.py
├── standards.py             # 临床标准知识库
├── scoring.py               # 健康评分算法
└── rules_engine.py          # 风险预警规则引擎

scripts/application/
├── __init__.py
├── health_assessment.py     # 健康评估服务
└── recommendations.py       # 健康建议生成

tests/hardware/
├── __init__.py
├── test_s3008t_protocol.py
├── test_s3008t_crc8.py
├── test_bmh08002_protocol.py
├── test_models.py
└── conftest.py

tests/data_processing/
├── __init__.py
├── test_bia_processor.py
├── test_spo2_processor.py
├── test_quality_assessment.py
└── test_time_series.py

tests/clinical/
├── __init__.py
├── test_standards.py
├── test_scoring.py
└── test_rules_engine.py

tests/application/
├── __init__.py
├── test_health_assessment.py
└── test_recommendations.py
```

---

## Task 1: S3008T CRC-8校验算法

**Files:**
- Create: `scripts/hardware/s3008t/crc8.py`
- Test: `tests/hardware/test_s3008t_crc8.py`

**Interfaces:**
- Produces: `calculate_crc8(data: bytes) -> int`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.hardware.s3008t.crc8 import calculate_crc8


def test_crc8_basic():
    """测试CRC-8基本计算"""
    data = bytes([0x01, 0x00, 0x01])
    result = calculate_crc8(data)
    assert isinstance(result, int)
    assert 0 <= result <= 255


def test_crc8_empty_data():
    """测试空数据CRC-8计算"""
    result = calculate_crc8(bytes())
    assert result == 0


def test_crc8_single_byte():
    """测试单字节CRC-8计算"""
    result = calculate_crc8(bytes([0x55]))
    # 多项式0x07,初值0x00: 0x55 -> 0x55
    assert result == 0x55
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/hardware/test_s3008t_crc8.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
def calculate_crc8(data: bytes) -> int:
    """
    CRC-8校验计算
    多项式: x^8 + x^2 + x + 1 (0x07)
    初值: 0x00
    
    Args:
        data: 需要计算CRC的数据
        
    Returns:
        CRC-8校验值(0~255)
    """
    crc = 0x00
    polynomial = 0x07
    
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ polynomial
            else:
                crc <<= 1
            crc &= 0xFF
    
    return crc
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/hardware/test_s3008t_crc8.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/hardware/s3008t/crc8.py tests/hardware/test_s3008t_crc8.py
git commit -m "feat: add S3008T CRC-8 checksum algorithm"
```

---

## Task 2: S3008T通信协议实现

**Files:**
- Create: `scripts/hardware/s3008t/protocol.py`
- Test: `tests/hardware/test_s3008t_protocol.py`

**Interfaces:**
- Consumes: `calculate_crc8(data: bytes) -> int` from Task 1
- Produces: `S3008TProtocol` class with methods: `build_command`, `parse_response`

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.hardware.s3008t.protocol import S3008TProtocol


def test_build_command():
    """测试构建命令帧"""
    protocol = S3008TProtocol()
    
    cmd = protocol.build_command(0x01, [0x01])  # 设置测量模式
    assert len(cmd) == 4  # Length + CMD + Data + CRC
    assert cmd[0] == 3    # CMD(1) + Data(1) + CRC(1) = 3
    assert cmd[1] == 0x01
    assert cmd[2] == 0x01


def test_build_set_weight_command():
    """测试构建设置体重命令"""
    protocol = S3008TProtocol()
    
    cmd = protocol.build_command(0x03, [0x02, 0x58])  # 60.8kg = 608 = 0x0258
    assert len(cmd) == 5  # Length + CMD + Data(2) + CRC
    assert cmd[0] == 4
    assert cmd[1] == 0x03
    assert cmd[2] == 0x02
    assert cmd[3] == 0x58


def test_parse_response():
    """测试解析响应帧"""
    protocol = S3008TProtocol()
    
    response = bytes([0x03, 0x08, 0x01, 0xC8])  # 阻抗值456Ω = 0x01C8
    result = protocol.parse_response(response)
    
    assert result['cmd'] == 0x08
    assert result['data'] == [0x01, 0xC8]
    assert result['impedance'] == 456
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/hardware/test_s3008t_protocol.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
from .crc8 import calculate_crc8


class S3008TProtocol:
    """
    S3008T体脂芯片通信协议实现
    
    帧格式: [Length] [CMD] [DataN] [CRC-8]
    Length = CMD(1) + DataN(N) + CRC(1)
    """
    
    def build_command(self, cmd: int, data: list = None) -> bytes:
        """
        构建命令帧
        
        Args:
            cmd: 命令号(0x01~0x08)
            data: 数据字节列表
            
        Returns:
            完整的命令帧字节
        """
        if data is None:
            data = []
        
        data_bytes = bytes([cmd] + data)
        length = len(data_bytes) + 1  # +1 for CRC
        crc = calculate_crc8(data_bytes)
        
        return bytes([length]) + data_bytes + bytes([crc])
    
    def parse_response(self, response: bytes) -> dict:
        """
        解析响应帧
        
        Args:
            response: 响应帧字节
            
        Returns:
            解析后的字典，包含cmd, data, impedance等字段
        """
        if len(response) < 3:
            raise ValueError("Invalid response length")
        
        length = response[0]
        cmd = response[1]
        data = list(response[2:-1])
        crc = response[-1]
        
        # 验证CRC
        expected_crc = calculate_crc8(response[1:-1])
        if crc != expected_crc:
            raise ValueError(f"CRC mismatch: expected {expected_crc}, got {crc}")
        
        result = {
            'length': length,
            'cmd': cmd,
            'data': data
        }
        
        # 如果是读取阻抗命令(0x08)，计算阻抗值
        if cmd == 0x08 and len(data) >= 2:
            result['impedance'] = (data[0] << 8) | data[1]
        
        return result
    
    def build_set_weight(self, weight_kg: float) -> bytes:
        """构建设置体重命令"""
        weight_scaled = int(weight_kg * 10)  # 体重×10
        data = [(weight_scaled >> 8) & 0xFF, weight_scaled & 0xFF]
        return self.build_command(0x03, data)
    
    def build_set_height(self, height_cm: int) -> bytes:
        """构建设置身高命令"""
        return self.build_command(0x04, [height_cm])
    
    def build_set_age(self, age: int) -> bytes:
        """构建设置年龄命令"""
        return self.build_command(0x05, [age])
    
    def build_set_gender(self, gender: int) -> bytes:
        """构建设置性别命令"""
        return self.build_command(0x06, [gender])
    
    def build_set_user_type(self, user_type: int) -> bytes:
        """构建设置用户类型命令"""
        return self.build_command(0x07, [user_type])
    
    def build_read_result(self) -> bytes:
        """构建读取测量结果命令"""
        return self.build_command(0x08)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/hardware/test_s3008t_protocol.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/hardware/s3008t/protocol.py tests/hardware/test_s3008t_protocol.py
git commit -m "feat: add S3008T communication protocol implementation"
```

---

## Task 3: BMH08002通信协议实现

**Files:**
- Create: `scripts/hardware/bmh08002/protocol.py`
- Create: `scripts/hardware/bmh08002/uart_protocol.py`
- Test: `tests/hardware/test_bmh08002_protocol.py`

**Interfaces:**
- Produces: `BMH08002Protocol`, `UARTProtocol` classes

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.hardware.bmh08002.uart_protocol import UARTProtocol


def test_build_uart_command():
    """测试构建UART命令帧"""
    protocol = UARTProtocol()
    
    cmd = protocol.build_command(0x01, 0x00, 0x00, 0x00)  # 开始测量
    assert len(cmd) == 8
    assert cmd[0] == 0x55  # Head
    assert cmd[1] == 0xB1  # CMD
    assert cmd[2] == 0x01  # OP_Code
    assert cmd[7] == 0xAA  # Tail


def test_parse_uart_data_frame():
    """测试解析UART数据帧"""
    protocol = UARTProtocol()
    
    data_frame = bytes([
        0x55, 0xB0, 0x02,  # Head, CMD, Status
        0x62,              # SpO2 = 98%
        0x4B,              # HR = 75 BPM
        0x3E,              # PI = 62 × 0.1 = 6.2%
        0x0A,              # HRV = 10 ms
        0x20,              # 脉搏高度
        0x05,              # 收缩时间
        0x00, 0x00,        # ADC1
        0x00, 0x00,        # ADC2
        0x9D,              # CheckSum
        0xAA               # Tail
    ])
    
    result = protocol.parse_data_frame(data_frame)
    
    assert result['status'] == 0x02
    assert result['spo2'] == 98
    assert result['heart_rate'] == 75
    assert result['pi'] == 6.2
    assert result['hrv'] == 10
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/hardware/test_bmh08002_protocol.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
class BMH08002Protocol:
    """
    BMH08002血氧模块通信协议基类
    
    支持UART和IIC两种通信方式
    """
    
    HEAD = 0x55
    CMD_DATA = 0xB0
    CMD_COMMAND = 0xB1
    TAIL = 0xAA
    
    def calculate_checksum(self, data: bytes) -> int:
        """计算校验和"""
        return sum(data) & 0xFF


class UARTProtocol(BMH08002Protocol):
    """
    BMH08002 UART通信协议实现
    
    命令帧格式(8字节): 0x55 [CMD] [OP_Code] [Addr] [Data_H] [Data_L] [CheckSum] 0xAA
    数据帧格式(15字节): 0x55 [CMD=0xB0] [Status] [SpO2] [HR] [PI] [HRV] [...] [CheckSum] 0xAA
    """
    
    def build_command(self, op_code: int, addr: int, data_h: int, data_l: int) -> bytes:
        """
        构建UART命令帧
        
        Args:
            op_code: 操作码(0x01~0x06)
            addr: 寄存器地址
            data_h: 数据高字节
            data_l: 数据低字节
            
        Returns:
            完整的命令帧字节
        """
        cmd_bytes = bytes([self.CMD_COMMAND, op_code, addr, data_h, data_l])
        checksum = self.calculate_checksum(cmd_bytes)
        
        return bytes([self.HEAD]) + cmd_bytes + bytes([checksum, self.TAIL])
    
    def parse_data_frame(self, frame: bytes) -> dict:
        """
        解析UART数据帧(15字节)
        
        Args:
            frame: 数据帧字节
            
        Returns:
            解析后的测量数据字典
        """
        if len(frame) != 15:
            raise ValueError(f"Invalid frame length: expected 15, got {len(frame)}")
        
        if frame[0] != self.HEAD or frame[14] != self.TAIL:
            raise ValueError("Invalid frame head or tail")
        
        # 验证校验和
        checksum = self.calculate_checksum(frame[1:13])
        if frame[13] != checksum:
            raise ValueError(f"Checksum mismatch: expected {checksum}, got {frame[13]}")
        
        return {
            'status': frame[2],
            'spo2': frame[3],
            'heart_rate': frame[4],
            'pi': frame[5] * 0.1,
            'hrv': frame[6],
            'pulse_height': frame[7],
            'systolic_time': frame[8],
            'ppg_adc1': (frame[9] << 8) | frame[10],
            'ppg_adc2': (frame[11] << 8) | frame[12]
        }
    
    def build_start_measurement(self) -> bytes:
        """构建开始测量命令"""
        return self.build_command(0x01, 0x00, 0x00, 0x00)
    
    def build_stop_measurement(self) -> bytes:
        """构建结束测量命令"""
        return self.build_command(0x01, 0x00, 0x00, 0x01)
    
    def build_enter_sleep(self) -> bytes:
        """构建进入休眠命令"""
        return self.build_command(0x01, 0x00, 0x00, 0x02)
    
    def build_get_result(self) -> bytes:
        """构建获取测量结果命令"""
        return self.build_command(0x03, 0x00, 0x00, 0x00)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/hardware/test_bmh08002_protocol.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/hardware/bmh08002/protocol.py scripts/hardware/bmh08002/uart_protocol.py tests/hardware/test_bmh08002_protocol.py
git commit -m "feat: add BMH08002 UART communication protocol"
```

---

## Task 4: 数据模型定义

**Files:**
- Create: `scripts/hardware/models.py`
- Test: `tests/hardware/test_models.py`

**Interfaces:**
- Produces: `HardwareData`, `ProcessedData`, `HealthAssessment` data classes

- [ ] **Step 1: Write the failing test**

```python
import pytest
from datetime import datetime
from scripts.hardware.models import HardwareData, ProcessedData, HealthAssessment


def test_hardware_data_initialization():
    """测试硬件数据模型初始化"""
    data = HardwareData(
        bia_impedance=450,
        spo2=98,
        heart_rate=75,
        pi=6.2,
        hrv=10,
        timestamp=datetime.now()
    )
    
    assert data.bia_impedance == 450
    assert data.spo2 == 98
    assert data.heart_rate == 75
    assert data.pi == 6.2
    assert data.hrv == 10
    assert data.signal_quality is None


def test_processed_data_initialization():
    """测试处理后数据模型初始化"""
    data = ProcessedData(
        body_fat_rate=22.5,
        bmi=24.8,
        visceral_fat_level=8,
        muscle_mass=55.0,
        spo2=98.0,
        heart_rate=75.0,
        age=35,
        sex="M",
        height_cm=175.0,
        weight_kg=70.0
    )
    
    assert data.body_fat_rate == 22.5
    assert data.bmi == 24.8
    assert data.visceral_fat_level == 8
    assert data.user_type == "Normal"


def test_health_assessment_initialization():
    """测试健康评估模型初始化"""
    assessment = HealthAssessment(
        overall_score=85,
        component_scores={'body_composition': 88, 'cardiovascular': 82},
        alerts=[],
        recommendations=['建议每周运动3次'],
        evidence_level='C'
    )
    
    assert assessment.overall_score == 85
    assert assessment.disclaimer == "本评估结果为保健级参考值，不可用于临床诊断。"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/hardware/test_models.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
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
    
    # 体成分数据
    body_fat_rate: Optional[float] = None    # 体脂率(%)
    bmi: Optional[float] = None              # BMI
    visceral_fat_level: Optional[int] = None # 内脏脂肪等级
    muscle_mass: Optional[float] = None      # 肌肉量(kg)
    skeletal_muscle: Optional[float] = None  # 骨骼肌量(kg)
    bone_mass: Optional[float] = None        # 骨量(kg)
    water_rate: Optional[float] = None       # 水分率(%)
    bmr: Optional[int] = None                # 基础代谢(Kcal)
    protein_rate: Optional[float] = None     # 蛋白质率(%)
    
    # 血氧数据
    spo2: Optional[float] = None             # 血氧(%)
    heart_rate: Optional[float] = None       # 心率(BPM)
    pi: Optional[float] = None               # 灌注指数(%)
    hrv: Optional[float] = None              # 心率变异性(ms)
    
    # 用户信息
    age: Optional[int] = None
    sex: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    user_type: str = "Normal"
    
    # 数据质量
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/hardware/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/hardware/models.py tests/hardware/test_models.py
git commit -m "feat: add data models for hardware and health assessment"
```

---

## Task 5: 体成分数据处理器

**Files:**
- Create: `scripts/data_processing/bia_processor.py`
- Test: `tests/data_processing/test_bia_processor.py`

**Interfaces:**
- Consumes: `HardwareData`, `ProcessedData` from Task 4
- Produces: `BIAProcessor` class

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.data_processing.bia_processor import BIAProcessor
from scripts.hardware.models import HardwareData, ProcessedData


def test_bia_processor_basic():
    """测试体成分处理器基本功能"""
    processor = BIAProcessor()
    
    hardware_data = HardwareData(
        bia_impedance=450,
        timestamp=None
    )
    
    result = processor.process(
        hardware_data=hardware_data,
        height_cm=175,
        weight_kg=70.0,
        age=35,
        sex="M",
        user_type="Normal"
    )
    
    assert isinstance(result, ProcessedData)
    assert result.bia_impedance == 450
    assert result.height_cm == 175
    assert result.weight_kg == 70.0


def test_impedance_validation():
    """测试阻抗值验证"""
    processor = BIAProcessor()
    
    # 正常阻抗值
    assert processor.validate_impedance(450) is True
    
    # 超出范围
    assert processor.validate_impedance(200) is False
    assert processor.validate_impedance(1100) is False


def test_bmi_calculation():
    """测试BMI计算"""
    processor = BIAProcessor()
    
    bmi = processor.calculate_bmi(70.0, 175)
    assert abs(bmi - 22.86) < 0.01
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_processing/test_bia_processor.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Optional
from scripts.hardware.models import HardwareData, ProcessedData


class BIAProcessor:
    """
    体成分数据处理器
    
    负责处理S3008T芯片采集的阻抗数据，计算体成分指标
    """
    
    IMPEDANCE_MIN = 300
    IMPEDANCE_MAX = 1000
    
    def validate_impedance(self, impedance: int) -> bool:
        """
        验证阻抗值是否在有效范围内
        
        Args:
            impedance: 阻抗值(Ω)
            
        Returns:
            True表示有效，False表示无效
        """
        return self.IMPEDANCE_MIN <= impedance <= self.IMPEDANCE_MAX
    
    def validate_height(self, height_cm: float) -> bool:
        """验证身高是否在有效范围内"""
        return 90 <= height_cm <= 220
    
    def validate_weight(self, weight_kg: float) -> bool:
        """验证体重是否在有效范围内"""
        return 20 <= weight_kg <= 300
    
    def calculate_bmi(self, weight_kg: float, height_cm: float) -> float:
        """
        计算BMI
        
        Args:
            weight_kg: 体重(kg)
            height_cm: 身高(cm)
            
        Returns:
            BMI值
        """
        height_m = height_cm / 100
        return weight_kg / (height_m ** 2)
    
    def process(self, 
                hardware_data: HardwareData,
                height_cm: float,
                weight_kg: float,
                age: int,
                sex: str,
                user_type: str = "Normal") -> ProcessedData:
        """
        处理体成分数据
        
        Args:
            hardware_data: 硬件原始数据
            height_cm: 身高(cm)
            weight_kg: 体重(kg)
            age: 年龄
            sex: 性别(M/F)
            user_type: 用户类型(Normal/Athlete)
            
        Returns:
            处理后的健康数据
        """
        processed = ProcessedData()
        
        # 设置用户信息
        processed.age = age
        processed.sex = sex
        processed.height_cm = height_cm
        processed.weight_kg = weight_kg
        processed.user_type = user_type
        processed.measurement_time = hardware_data.timestamp
        
        # 设置BMI
        processed.bmi = self.calculate_bmi(weight_kg, height_cm)
        
        # 设置数据质量评分
        quality_score = self._calculate_data_quality(hardware_data, height_cm, weight_kg)
        processed.data_quality = quality_score
        
        # 注意：体脂率等指标需要调用BestHealth TwoLegs API计算
        # 此处预留接口，实际计算需调用外部API
        
        return processed
    
    def _calculate_data_quality(self, 
                                hardware_data: HardwareData,
                                height_cm: float,
                                weight_kg: float) -> float:
        """
        计算数据质量评分
        
        Returns:
            数据质量评分(0~1)
        """
        score = 1.0
        
        # 验证阻抗值
        if hardware_data.bia_impedance is not None:
            if not self.validate_impedance(hardware_data.bia_impedance):
                score -= 0.3
        
        # 验证身高
        if not self.validate_height(height_cm):
            score -= 0.3
        
        # 验证体重
        if not self.validate_weight(weight_kg):
            score -= 0.3
        
        # 验证信号质量
        if hardware_data.signal_quality is not None:
            score = min(score, hardware_data.signal_quality)
        
        return max(0.0, score)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_processing/test_bia_processor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/data_processing/bia_processor.py tests/data_processing/test_bia_processor.py
git commit -m "feat: add BIA body composition data processor"
```

---

## Task 6: 血氧数据处理器

**Files:**
- Create: `scripts/data_processing/spo2_processor.py`
- Test: `tests/data_processing/test_spo2_processor.py`

**Interfaces:**
- Consumes: `HardwareData`, `ProcessedData` from Task 4
- Produces: `SpO2Processor` class

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.data_processing.spo2_processor import SpO2Processor
from scripts.hardware.models import HardwareData, ProcessedData


def test_spo2_processor_basic():
    """测试血氧处理器基本功能"""
    processor = SpO2Processor()
    
    hardware_data = HardwareData(
        spo2=98,
        heart_rate=75,
        pi=6.2,
        hrv=10,
        timestamp=None
    )
    
    result = processor.process(hardware_data)
    
    assert isinstance(result, ProcessedData)
    assert result.spo2 == 98.0
    assert result.heart_rate == 75.0
    assert result.pi == 6.2
    assert result.hrv == 10.0


def test_spo2_range_validation():
    """测试血氧范围验证"""
    processor = SpO2Processor()
    
    assert processor.validate_spo2(95) is True
    assert processor.validate_spo2(70) is True
    assert processor.validate_spo2(69) is False
    assert processor.validate_spo2(100) is False


def test_pi_signal_quality():
    """测试PI值信号质量评估"""
    processor = SpO2Processor()
    
    # PI >= 0.5%，信号质量良好
    assert processor.evaluate_signal_quality(pi=1.0) >= 0.8
    
    # PI < 0.5%，信号质量较差
    assert processor.evaluate_signal_quality(pi=0.3) < 0.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/data_processing/test_spo2_processor.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Optional
from scripts.hardware.models import HardwareData, ProcessedData


class SpO2Processor:
    """
    血氧数据处理器
    
    负责处理BMH08002模块采集的血氧、心率、PI等数据
    """
    
    # 性能指标范围
    SPO2_MIN = 70
    SPO2_MAX = 99
    HR_MIN = 30
    HR_MAX = 250
    PI_MIN = 0.5
    PI_MAX = 20.0  # 通信字节允许范围，性能指标为0.5~25%
    
    def validate_spo2(self, spo2: int) -> bool:
        """
        验证血氧值是否在有效范围内
        
        注意：性能指标标注70~99%，通信字节允许35~99%
        实际使用以性能指标70~99%为准
        
        Args:
            spo2: 血氧值(%)
            
        Returns:
            True表示有效，False表示无效
        """
        return self.SPO2_MIN <= spo2 <= self.SPO2_MAX
    
    def validate_heart_rate(self, hr: int) -> bool:
        """验证心率是否在有效范围内"""
        return self.HR_MIN <= hr <= self.HR_MAX
    
    def validate_pi(self, pi: float) -> bool:
        """
        验证PI值是否在有效范围内
        
        注意：性能指标标注0.5~25%，通信字节允许0~20.0%
        实际使用以通信字节0~20.0%为准
        
        Args:
            pi: 灌注指数(%)
            
        Returns:
            True表示有效，False表示无效
        """
        return 0 <= pi <= self.PI_MAX
    
    def evaluate_signal_quality(self, pi: Optional[float] = None) -> float:
        """
        评估信号质量
        
        PI值越大，信号质量越好
        PI < 0.5%时精度下降
        
        Args:
            pi: 灌注指数(%)
            
        Returns:
            信号质量评分(0~1)
        """
        if pi is None:
            return 0.5
        
        if pi < 0.5:
            return min(0.5, pi * 2)
        elif pi < 2.0:
            return 0.5 + (pi - 0.5) * 0.2
        else:
            return min(1.0, 0.8 + (pi - 2.0) * 0.01)
    
    def process(self, hardware_data: HardwareData) -> ProcessedData:
        """
        处理血氧数据
        
        Args:
            hardware_data: 硬件原始数据
            
        Returns:
            处理后的健康数据
        """
        processed = ProcessedData()
        
        # 设置血氧数据
        if hardware_data.spo2 is not None:
            processed.spo2 = float(hardware_data.spo2)
        
        if hardware_data.heart_rate is not None:
            processed.heart_rate = float(hardware_data.heart_rate)
        
        if hardware_data.pi is not None:
            processed.pi = hardware_data.pi
        
        if hardware_data.hrv is not None:
            processed.hrv = float(hardware_data.hrv)
        
        processed.measurement_time = hardware_data.timestamp
        
        # 计算数据质量评分
        quality_score = self._calculate_data_quality(hardware_data)
        processed.data_quality = quality_score
        
        return processed
    
    def _calculate_data_quality(self, hardware_data: HardwareData) -> float:
        """
        计算数据质量评分
        
        Returns:
            数据质量评分(0~1)
        """
        score = 1.0
        
        # 验证血氧值
        if hardware_data.spo2 is not None:
            if not self.validate_spo2(hardware_data.spo2):
                score -= 0.4
        
        # 验证心率
        if hardware_data.heart_rate is not None:
            if not self.validate_heart_rate(hardware_data.heart_rate):
                score -= 0.3
        
        # 评估信号质量(PI值)
        pi_quality = self.evaluate_signal_quality(hardware_data.pi)
        score = min(score, pi_quality)
        
        # 验证信号质量字段
        if hardware_data.signal_quality is not None:
            score = min(score, hardware_data.signal_quality)
        
        return max(0.0, score)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/data_processing/test_spo2_processor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/data_processing/spo2_processor.py tests/data_processing/test_spo2_processor.py
git commit -m "feat: add SpO2 blood oxygen data processor"
```

---

## Task 7: 临床标准知识库

**Files:**
- Create: `scripts/clinical/standards.py`
- Test: `tests/clinical/test_standards.py`

**Interfaces:**
- Produces: `ClinicalStandards` class with BMI, body fat, SpO2, visceral fat standards

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.clinical.standards import ClinicalStandards


def test_bmi_classification():
    """测试BMI分类"""
    standards = ClinicalStandards()
    
    assert standards.classify_bmi(17.5) == "underweight"
    assert standards.classify_bmi(22.0) == "normal"
    assert standards.classify_bmi(26.5) == "overweight"
    assert standards.classify_bmi(31.0) == "obese"


def test_body_fat_classification():
    """测试体脂率分类"""
    standards = ClinicalStandards()
    
    # 男性18~39岁
    assert standards.classify_body_fat(10.0, "M", 30) == "underweight"
    assert standards.classify_body_fat(14.0, "M", 30) == "normal"
    assert standards.classify_body_fat(18.0, "M", 30) == "warning"
    assert standards.classify_body_fat(23.0, "M", 30) == "overweight"
    assert standards.classify_body_fat(28.0, "M", 30) == "obese"
    
    # 女性18~39岁
    assert standards.classify_body_fat(20.0, "F", 30) == "underweight"
    assert standards.classify_body_fat(24.0, "F", 30) == "normal"


def test_spo2_classification():
    """测试血氧分类"""
    standards = ClinicalStandards()
    
    assert standards.classify_spo2(97) == "normal"
    assert standards.classify_spo2(92) == "mild_hypoxemia"
    assert standards.classify_spo2(88) == "moderate"
    assert standards.classify_spo2(84) == "severe"


def test_visceral_fat_classification():
    """测试内脏脂肪等级分类"""
    standards = ClinicalStandards()
    
    assert standards.classify_visceral_fat(8) == "normal"
    assert standards.classify_visceral_fat(12) == "warning"
    assert standards.classify_visceral_fat(16) == "danger"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/clinical/test_standards.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Dict, Optional


class ClinicalStandards:
    """
    临床标准知识库
    
    包含WHO BMI标准、BestHealth体脂率标准、血氧标准、内脏脂肪等级标准等
    """
    
    # WHO BMI标准
    BMI_STANDARDS = {
        "underweight": {"max": 18.5},
        "normal": {"min": 18.5, "max": 25.0},
        "overweight": {"min": 25.0, "max": 30.0},
        "obese": {"min": 30.0}
    }
    
    # BestHealth体脂率标准(制造商标准，非官方临床标准)
    BODY_FAT_STANDARDS = {
        "male": {
            (6, 13): {"under": 7.0, "normal": (7.0, 15.9), "warning": (16.0, 24.9), "over": (25.0, 29.9), "obese": 30.0},
            (14, 14): {"under": 7.0, "normal": (7.0, 14.9), "warning": (15.0, 24.9), "over": (25.0, 28.9), "obese": 29.0},
            (15, 15): {"under": 8.0, "normal": (8.0, 14.9), "warning": (15.0, 23.9), "over": (24.0, 28.9), "obese": 29.0},
            (16, 16): {"under": 8.0, "normal": (8.0, 15.9), "warning": (16.0, 23.9), "over": (24.0, 27.9), "obese": 28.0},
            (17, 17): {"under": 9.0, "normal": (9.0, 15.9), "warning": (16.0, 22.9), "over": (23.0, 27.9), "obese": 28.0},
            (18, 39): {"under": 11.0, "normal": (11.0, 16.9), "warning": (17.0, 21.9), "over": (22.0, 26.9), "obese": 27.0},
            (40, 59): {"under": 12.0, "normal": (12.0, 17.9), "warning": (18.0, 22.9), "over": (23.0, 27.9), "obese": 28.0},
            (60, 99): {"under": 14.0, "normal": (14.0, 19.9), "warning": (20.0, 24.9), "over": (25.0, 29.9), "obese": 30.0}
        },
        "female": {
            (18, 39): {"under": 21.0, "normal": (21.0, 27.9), "warning": (28.0, 34.9), "over": (35.0, 39.9), "obese": 40.0},
            (40, 59): {"under": 22.0, "normal": (22.0, 28.9), "warning": (29.0, 35.9), "over": (36.0, 40.9), "obese": 41.0},
            (60, 99): {"under": 23.0, "normal": (23.0, 29.9), "warning": (30.0, 36.9), "over": (37.0, 41.9), "obese": 42.0}
        }
    }
    
    # 血氧标准
    SPO2_STANDARDS = {
        "normal": {"min": 95, "max": 100},
        "mild_hypoxemia": {"min": 91, "max": 94},
        "moderate": {"min": 86, "max": 90},
        "severe": {"max": 85}
    }
    
    # 内脏脂肪等级标准
    VISCERAL_FAT_STANDARDS = {
        "normal": {"max": 9},
        "warning": {"min": 10, "max": 14},
        "danger": {"min": 15}
    }
    
    def classify_bmi(self, bmi: float) -> str:
        """
        根据BMI值分类
        
        Args:
            bmi: BMI值
            
        Returns:
            分类结果: underweight/normal/overweight/obese
        """
        if bmi < self.BMI_STANDARDS["underweight"]["max"]:
            return "underweight"
        elif bmi < self.BMI_STANDARDS["overweight"]["min"]:
            return "normal"
        elif bmi < self.BMI_STANDARDS["obese"]["min"]:
            return "overweight"
        else:
            return "obese"
    
    def _find_age_group(self, age: int, sex: str) -> Optional[tuple]:
        """找到年龄对应的分组"""
        age_groups = self.BODY_FAT_STANDARDS.get(sex.lower())
        if not age_groups:
            return None
        
        for (min_age, max_age) in age_groups:
            if min_age <= age <= max_age:
                return (min_age, max_age)
        
        return None
    
    def classify_body_fat(self, body_fat_rate: float, sex: str, age: int) -> str:
        """
        根据体脂率分类
        
        Args:
            body_fat_rate: 体脂率(%)
            sex: 性别(M/F)
            age: 年龄
            
        Returns:
            分类结果: underweight/normal/warning/overweight/obese
        """
        age_group = self._find_age_group(age, sex)
        if not age_group:
            return "normal"
        
        standards = self.BODY_FAT_STANDARDS[sex.lower()][age_group]
        
        if body_fat_rate < standards["under"]:
            return "underweight"
        elif body_fat_rate <= standards["normal"][1]:
            return "normal"
        elif body_fat_rate <= standards["warning"][1]:
            return "warning"
        elif body_fat_rate <= standards["over"][1]:
            return "overweight"
        else:
            return "obese"
    
    def classify_spo2(self, spo2: int) -> str:
        """
        根据血氧值分类
        
        Args:
            spo2: 血氧值(%)
            
        Returns:
            分类结果: normal/mild_hypoxemia/moderate/severe
        """
        if spo2 >= self.SPO2_STANDARDS["normal"]["min"]:
            return "normal"
        elif spo2 >= self.SPO2_STANDARDS["mild_hypoxemia"]["min"]:
            return "mild_hypoxemia"
        elif spo2 >= self.SPO2_STANDARDS["moderate"]["min"]:
            return "moderate"
        else:
            return "severe"
    
    def classify_visceral_fat(self, level: int) -> str:
        """
        根据内脏脂肪等级分类
        
        Args:
            level: 内脏脂肪等级(1~50)
            
        Returns:
            分类结果: normal/warning/danger
        """
        if level <= self.VISCERAL_FAT_STANDARDS["normal"]["max"]:
            return "normal"
        elif level <= self.VISCERAL_FAT_STANDARDS["warning"]["max"]:
            return "warning"
        else:
            return "danger"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/clinical/test_standards.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/clinical/standards.py tests/clinical/test_standards.py
git commit -m "feat: add clinical standards knowledge base"
```

---

## Task 8: 健康评分算法

**Files:**
- Create: `scripts/clinical/scoring.py`
- Test: `tests/clinical/test_scoring.py`

**Interfaces:**
- Consumes: `ProcessedData` from Task 4, `ClinicalStandards` from Task 7
- Produces: `HealthScorer` class

- [ ] **Step 1: Write the failing test**

```python
import pytest
from scripts.clinical.scoring import HealthScorer
from scripts.hardware.models import ProcessedData


def test_body_composition_score():
    """测试体成分评分"""
    scorer = HealthScorer()
    
    data = ProcessedData(
        body_fat_rate=22.5,
        bmi=24.8,
        visceral_fat_level=8,
        muscle_mass=55.0,
        age=35,
        sex="M",
        height_cm=175.0,
        weight_kg=70.0
    )
    
    score = scorer.calculate_body_composition_score(data)
    assert 0 <= score <= 100


def test_cardiovascular_score():
    """测试心血管评分"""
    scorer = HealthScorer()
    
    data = ProcessedData(
        spo2=98.0,
        heart_rate=75.0,
        pi=6.2,
        hrv=10.0
    )
    
    score = scorer.calculate_cardiovascular_score(data)
    assert 0 <= score <= 100


def test_overall_score():
    """测试综合健康评分"""
    scorer = HealthScorer()
    
    data = ProcessedData(
        body_fat_rate=22.5,
        bmi=24.8,
        visceral_fat_level=8,
        muscle_mass=55.0,
        spo2=98.0,
        heart_rate=75.0,
        age=35,
        sex="M",
        height_cm=175.0,
        weight_kg=70.0
    )
    
    scores = scorer.calculate_overall_score(data)
    
    assert scores['overall'] == (scores['body_composition'] + scores['cardiovascular']) // 2
    assert 0 <= scores['overall'] <= 100
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/clinical/test_scoring.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
from typing import Dict
from scripts.hardware.models import ProcessedData
from scripts.clinical.standards import ClinicalStandards


class HealthScorer:
    """
    健康评分算法
    
    综合健康评分 = 体成分评分(50%) + 心血管评分(50%)
    
    注意: 当前权重分配基于专家共识(证据等级C)，后续需通过临床验证数据优化
    """
    
    def __init__(self):
        self.standards = ClinicalStandards()
    
    def _score_single_metric(self, value: float, normal_range: tuple) -> int:
        """
        计算单项指标评分
        
        Args:
            value: 指标值
            normal_range: 标准范围(min, max)
            
        Returns:
            评分(0~100)
        """
        if value is None:
            return 50
        
        min_val, max_val = normal_range
        
        if min_val <= value <= max_val:
            return 100
        elif value < min_val:
            deviation = min_val - value
            max_deviation = min_val * 0.2
            return max(0, 100 - int((deviation / max_deviation) * 100))
        else:
            deviation = value - max_val
            max_deviation = max_val * 0.2
            return max(0, 100 - int((deviation / max_deviation) * 100))
    
    def calculate_body_composition_score(self, data: ProcessedData) -> int:
        """
        计算体成分评分
        
        体成分评分 = Σ(单项指标评分 × 权重) / Σ(权重)
        其中:
        - 体脂率: 权重30%
        - BMI: 权重20%
        - 内脏脂肪等级: 权重25%
        - 肌肉量: 权重25%
        
        Args:
            data: 处理后的健康数据
            
        Returns:
            体成分评分(0~100)
        """
        scores = []
        weights = []
        
        # 体脂率评分(权重30%)
        if data.body_fat_rate is not None and data.age is not None and data.sex is not None:
            body_fat_class = self.standards.classify_body_fat(data.body_fat_rate, data.sex, data.age)
            if body_fat_class == "normal":
                scores.append(100)
            elif body_fat_class in ["underweight", "warning"]:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(30)
        
        # BMI评分(权重20%)
        if data.bmi is not None:
            bmi_class = self.standards.classify_bmi(data.bmi)
            if bmi_class == "normal":
                scores.append(100)
            elif bmi_class in ["underweight", "overweight"]:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(20)
        
        # 内脏脂肪评分(权重25%)
        if data.visceral_fat_level is not None:
            vf_class = self.standards.classify_visceral_fat(data.visceral_fat_level)
            if vf_class == "normal":
                scores.append(100)
            elif vf_class == "warning":
                scores.append(60)
            else:
                scores.append(30)
            weights.append(25)
        
        # 肌肉量评分(权重25%) - 简化处理
        if data.muscle_mass is not None and data.weight_kg is not None:
            muscle_ratio = data.muscle_mass / data.weight_kg
            if muscle_ratio >= 0.45:
                scores.append(100)
            elif muscle_ratio >= 0.35:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(25)
        
        if not weights:
            return 50
        
        total_score = sum(s * w for s, w in zip(scores, weights))
        return total_score // sum(weights)
    
    def calculate_cardiovascular_score(self, data: ProcessedData) -> int:
        """
        计算心血管评分
        
        基于血氧、心率、PI、HRV等指标
        
        Args:
            data: 处理后的健康数据
            
        Returns:
            心血管评分(0~100)
        """
        scores = []
        weights = []
        
        # 血氧评分(权重40%)
        if data.spo2 is not None:
            spo2_class = self.standards.classify_spo2(int(data.spo2))
            if spo2_class == "normal":
                scores.append(100)
            elif spo2_class == "mild_hypoxemia":
                scores.append(70)
            elif spo2_class == "moderate":
                scores.append(40)
            else:
                scores.append(20)
            weights.append(40)
        
        # 心率评分(权重30%) - 基于静息心率
        if data.heart_rate is not None:
            hr = data.heart_rate
            if 60 <= hr <= 80:
                scores.append(100)
            elif 50 <= hr < 60 or 80 < hr <= 100:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(30)
        
        # PI评分(权重30%)
        if data.pi is not None:
            if data.pi >= 1.0:
                scores.append(100)
            elif data.pi >= 0.5:
                scores.append(70)
            else:
                scores.append(40)
            weights.append(30)
        
        if not weights:
            return 50
        
        total_score = sum(s * w for s, w in zip(scores, weights))
        return total_score // sum(weights)
    
    def calculate_overall_score(self, data: ProcessedData) -> Dict[str, int]:
        """
        计算综合健康评分
        
        综合健康评分 = 体成分评分(50%) + 心血管评分(50%)
        
        Args:
            data: 处理后的健康数据
            
        Returns:
            包含各维度评分的字典
        """
        body_comp_score = self.calculate_body_composition_score(data)
        cardio_score = self.calculate_cardiovascular_score(data)
        overall_score = (body_comp_score + cardio_score) // 2
        
        return {
            'overall': overall_score,
            'body_composition': body_comp_score,
            'cardiovascular': cardio_score
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/clinical/test_scoring.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/clinical/scoring.py tests/clinical/test_scoring.py
git commit -m "feat: add health scoring algorithm"
```

---

## Task 9: 风险预警规则引擎

**Files:**
- Create: `scripts/clinical/rules_engine.py`
- Test: `tests/clinical/test_rules_engine.py`

**Interfaces:**
- Consumes: `ProcessedData` from Task 4, `ClinicalStandards` from Task 7
- Produces: `RulesEngine` class

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/clinical/test_rules_engine.py -v`
Expected: FAIL with "module not found"

- [ ] **Step 3: Write minimal implementation**

```python
from typing import List, Dict
from scripts.hardware.models import ProcessedData
from scripts.clinical.standards import ClinicalStandards


class RulesEngine:
    """
    风险预警规则引擎
    
    根据临床标准和检测数据，识别潜在的健康风险并生成预警
    """
    
    def __init__(self):
        self.standards = ClinicalStandards()
        self.rules = self._load_rules()
    
    def _load_rules(self) -> List[Dict]:
        """
        加载预警规则
        
        证据等级说明:
        - A: 有充分临床证据支持
        - B: 有中等临床证据支持
        - C: 基于专家共识或观察性研究
        """
        return [
            {
                "id": "rule_001",
                "name": "内脏脂肪高危预警",
                "condition": self._check_visceral_fat_high,
                "severity": "high",
                "action": "建议就医评估",
                "evidence_level": "B"
            },
            {
                "id": "rule_002",
                "name": "血氧偏低预警",
                "condition": self._check_spo2_low,
                "severity": "medium",
                "action": "建议观察并保持室内通风",
                "evidence_level": "C"
            },
            {
                "id": "rule_003",
                "name": "心率异常预警",
                "condition": self._check_heart_rate_abnormal,
                "severity": "medium",
                "action": "建议关注心率变化，如有不适请咨询医生",
                "evidence_level": "C"
            },
            {
                "id": "rule_004",
                "name": "肥胖风险预警",
                "condition": self._check_obesity_risk,
                "severity": "medium",
                "action": "建议控制饮食、增加运动",
                "evidence_level": "B"
            }
        ]
    
    def _check_visceral_fat_high(self, data: ProcessedData) -> bool:
        """检查内脏脂肪是否高危(VFAL >= 15)"""
        return data.visceral_fat_level is not None and data.visceral_fat_level >= 15
    
    def _check_spo2_low(self, data: ProcessedData) -> bool:
        """检查血氧是否偏低(< 95%)"""
        return data.spo2 is not None and data.spo2 < 95.0
    
    def _check_heart_rate_abnormal(self, data: ProcessedData) -> bool:
        """检查心率是否异常(静息心率 > 100 BPM 或 < 50 BPM)"""
        if data.heart_rate is None:
            return False
        return data.heart_rate > 100 or data.heart_rate < 50
    
    def _check_obesity_risk(self, data: ProcessedData) -> bool:
        """检查肥胖风险(BMI >= 28 或 体脂率超过标准上限)"""
        # 检查BMI
        if data.bmi is not None and data.bmi >= 28:
            return True
        
        # 检查体脂率
        if data.body_fat_rate is not None and data.age is not None and data.sex is not None:
            body_fat_class = self.standards.classify_body_fat(
                data.body_fat_rate, data.sex, data.age
            )
            if body_fat_class in ["overweight", "obese"]:
                return True
        
        return False
    
    def evaluate(self, data: ProcessedData) -> List[Dict]:
        """
        评估数据并生成预警
        
        Args:
            data: 处理后的健康数据
            
        Returns:
            预警列表
        """
        alerts = []
        
        for rule in self.rules:
            condition_func = rule["condition"]
            if condition_func(data):
                alerts.append({
                    "id": rule["id"],
                    "name": rule["name"],
                    "severity": rule["severity"],
                    "action": rule["action"],
                    "evidence_level": rule["evidence_level"]
                })
        
        return alerts
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/clinical/test_rules_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/clinical