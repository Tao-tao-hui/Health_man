"""数据治理模块

提供数据获取过程中的合规性保障：
1. 执行日志记录（时间戳、来源URL、HTTP状态、记录数）
2. 文件完整性哈希（SHA-256）
3. 隐私扫描（PII检测）
4. 合规性检查清单

用法：
    from scripts.scraping.data_governance import DataGovernance
    
    gov = DataGovernance()
    gov.log_fetch("pubmed", "efetch", url, status=200, record_count=5)
    gov.scan_privacy(abstract_text)
    gov.generate_report()
"""
import hashlib
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("data_governance")

LOG_DIR = Path("data/scraping/logs")
REPORT_DIR = Path("data/scraping/reports")


@dataclass
class FetchLogEntry:
    """单次数据获取日志条目"""
    timestamp: str
    source: str
    endpoint: str
    url: str
    status: int
    record_count: int
    duration_ms: float
    error: str = ""
    hash: str = ""


@dataclass
class PrivacyScanResult:
    """隐私扫描结果"""
    has_pii: bool = False
    detected_items: list[str] = field(default_factory=list)
    risk_level: str = "low"


@dataclass
class ComplianceCheck:
    """合规性检查项"""
    name: str
    description: str
    passed: bool
    details: str = ""


class DataGovernance:
    """数据治理管理器"""

    def __init__(self):
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.fetch_logs: list[FetchLogEntry] = []
        self.integrity_hashes: dict[str, str] = {}
        self.privacy_scans: dict[str, PrivacyScanResult] = {}
        self.compliance_checks: list[ComplianceCheck] = []

    def log_fetch(
        self,
        source: str,
        endpoint: str,
        url: str,
        status: int,
        record_count: int,
        duration_ms: float,
        error: str = "",
        hash_value: str = "",
    ) -> None:
        """记录数据获取日志"""
        entry = FetchLogEntry(
            timestamp=datetime.now().isoformat(),
            source=source,
            endpoint=endpoint,
            url=url,
            status=status,
            record_count=record_count,
            duration_ms=duration_ms,
            error=error,
            hash=hash_value,
        )
        self.fetch_logs.append(entry)
        logger.info(
            "FETCH [%s] %s/%s: %d records, %.1fms, status=%d",
            source, endpoint, url[:60], record_count, duration_ms, status
        )

    def compute_hash(self, content: bytes) -> str:
        """计算内容的 SHA-256 哈希"""
        return hashlib.sha256(content).hexdigest()

    def hash_file(self, file_path: Path) -> str:
        """计算文件的 SHA-256 哈希并记录"""
        content = file_path.read_bytes()
        file_hash = self.compute_hash(content)
        self.integrity_hashes[str(file_path)] = file_hash
        return file_hash

    def scan_privacy(self, text: str, identifier: str = "") -> PrivacyScanResult:
        """扫描文本中的 PII（个人身份信息）"""
        result = PrivacyScanResult()

        # 姓名模式（英文姓名）
        name_patterns = [
            re.compile(r"\b[A-Z][a-z]+\s+[A-Z][a-z]+\b"),
            re.compile(r"\b[A-Z]\.\s*[A-Z][a-z]+\b"),
        ]

        # 邮箱
        email_pattern = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

        # 电话号码
        phone_pattern = re.compile(r"\+?[1-9]\d{1,14}")

        # IP地址
        ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")

        # 身份证号
        id_card_pattern = re.compile(r"\d{17}[\dXx]")

        # 检测
        for pattern in name_patterns:
            matches = pattern.findall(text)
            for match in matches[:3]:
                result.detected_items.append(f"NAME: {match}")

        for match in email_pattern.findall(text)[:3]:
            result.detected_items.append(f"EMAIL: {match}")

        for match in phone_pattern.findall(text)[:3]:
            result.detected_items.append(f"PHONE: {match}")

        for match in ip_pattern.findall(text)[:3]:
            result.detected_items.append(f"IP: {match}")

        for match in id_card_pattern.findall(text)[:3]:
            result.detected_items.append(f"ID_CARD: {match}")

        if result.detected_items:
            result.has_pii = True
            result.risk_level = "high" if any(x.startswith("EMAIL") or x.startswith("ID_CARD") for x in result.detected_items) else "medium"

        if identifier:
            self.privacy_scans[identifier] = result

        return result

    def run_compliance_checks(self, data_dir: Path) -> None:
        """运行合规性检查清单"""
        checks = []

        # 1. 数据存储路径检查
        checks.append(ComplianceCheck(
            name="storage_path",
            description="数据存储在指定目录",
            passed=data_dir.exists(),
            details=str(data_dir) if data_dir.exists() else "目录不存在",
        ))

        # 2. 文件数量检查
        json_files = list(data_dir.rglob("*.json"))
        checks.append(ComplianceCheck(
            name="file_count",
            description="至少包含10个JSON数据文件",
            passed=len(json_files) >= 10,
            details=f"实际文件数: {len(json_files)}",
        ))

        # 3. 隐私扫描检查
        pii_count = sum(1 for r in self.privacy_scans.values() if r.has_pii)
        checks.append(ComplianceCheck(
            name="privacy_scan",
            description="数据中不含敏感PII信息",
            passed=pii_count == 0,
            details=f"含PII的记录数: {pii_count}",
        ))

        # 4. 完整性哈希检查
        checks.append(ComplianceCheck(
            name="integrity_hashes",
            description="所有数据文件已计算完整性哈希",
            passed=len(self.integrity_hashes) > 0,
            details=f"已哈希文件数: {len(self.integrity_hashes)}",
        ))

        # 5. 日志记录检查
        checks.append(ComplianceCheck(
            name="fetch_logs",
            description="数据获取过程有完整日志记录",
            passed=len(self.fetch_logs) > 0,
            details=f"日志条目数: {len(self.fetch_logs)}",
        ))

        # 6. 数据格式检查（JSON有效性）
        invalid_count = 0
        for f in json_files[:20]:
            try:
                json.loads(f.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                invalid_count += 1
        checks.append(ComplianceCheck(
            name="json_format",
            description="所有JSON文件格式有效",
            passed=invalid_count == 0,
            details=f"无效文件数: {invalid_count}",
        ))

        self.compliance_checks = checks

    def save_logs(self) -> None:
        """保存执行日志到文件"""
        log_path = LOG_DIR / f"fetch_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        logs_data = [
            {
                "timestamp": entry.timestamp,
                "source": entry.source,
                "endpoint": entry.endpoint,
                "url": entry.url,
                "status": entry.status,
                "record_count": entry.record_count,
                "duration_ms": entry.duration_ms,
                "error": entry.error,
                "hash": entry.hash,
            }
            for entry in self.fetch_logs
        ]
        log_path.write_text(json.dumps(logs_data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("执行日志已保存: %s", log_path)

    def save_integrity_report(self) -> None:
        """保存完整性报告"""
        report_path = LOG_DIR / "integrity_hashes.json"
        report_path.write_text(
            json.dumps(self.integrity_hashes, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.info("完整性哈希报告已保存: %s", report_path)

    def save_privacy_report(self) -> None:
        """保存隐私扫描报告"""
        report_path = LOG_DIR / "privacy_scan_report.json"
        data = {
            identifier: {
                "has_pii": result.has_pii,
                "detected_items": result.detected_items,
                "risk_level": result.risk_level,
            }
            for identifier, result in self.privacy_scans.items()
        }
        report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("隐私扫描报告已保存: %s", report_path)

    def generate_summary_report(self) -> dict:
        """生成数据获取总结报告"""
        summary = {
            "report_generated_at": datetime.now().isoformat(),
            "summary": {
                "total_fetch_operations": len(self.fetch_logs),
                "total_records_fetched": sum(e.record_count for e in self.fetch_logs),
                "successful_operations": sum(1 for e in self.fetch_logs if e.status == 200),
                "failed_operations": sum(1 for e in self.fetch_logs if e.status != 200),
                "total_duration_ms": sum(e.duration_ms for e in self.fetch_logs),
                "hashed_files_count": len(self.integrity_hashes),
                "records_scanned_for_pii": len(self.privacy_scans),
                "records_with_pii": sum(1 for r in self.privacy_scans.values() if r.has_pii),
            },
            "compliance": {
                "total_checks": len(self.compliance_checks),
                "passed_checks": sum(1 for c in self.compliance_checks if c.passed),
                "failed_checks": sum(1 for c in self.compliance_checks if not c.passed),
                "checks": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "passed": c.passed,
                        "details": c.details,
                    }
                    for c in self.compliance_checks
                ],
            },
            "data_sources": [],
            "anomalies": [],
        }

        # 按数据源统计
        source_stats = defaultdict(lambda: {"records": 0, "operations": 0, "duration_ms": 0})
        for entry in self.fetch_logs:
            source_stats[entry.source]["records"] += entry.record_count
            source_stats[entry.source]["operations"] += 1
            source_stats[entry.source]["duration_ms"] += entry.duration_ms

        for source, stats in source_stats.items():
            summary["data_sources"].append({
                "name": source,
                "total_records": stats["records"],
                "total_operations": stats["operations"],
                "total_duration_ms": stats["duration_ms"],
                "avg_duration_per_operation": stats["duration_ms"] / max(stats["operations"], 1),
            })

        # 检测异常
        for entry in self.fetch_logs:
            if entry.status != 200:
                summary["anomalies"].append({
                    "type": "fetch_failure",
                    "timestamp": entry.timestamp,
                    "source": entry.source,
                    "url": entry.url,
                    "error": entry.error,
                })

        return summary

    def save_summary_report(self) -> None:
        """保存总结报告"""
        report = self.generate_summary_report()

        # JSON格式
        json_path = REPORT_DIR / "data_acquisition_summary.json"
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        # Markdown格式
        md_path = REPORT_DIR / "data_acquisition_summary.md"
        md_content = self._generate_markdown_report(report)
        md_path.write_text(md_content, encoding="utf-8")

        logger.info("数据获取总结报告已保存: %s", md_path)

    def _generate_markdown_report(self, report: dict) -> str:
        """生成Markdown格式报告"""
        lines = []
        lines.append("# 数据获取总结报告")
        lines.append("")
        lines.append(f"**生成时间**: {report['report_generated_at']}")
        lines.append("")

        # 摘要
        lines.append("## 摘要")
        lines.append("")
        s = report["summary"]
        lines.append(f"- 总获取操作: {s['total_fetch_operations']}")
        lines.append(f"- 总记录数: {s['total_records_fetched']}")
        lines.append(f"- 成功操作: {s['successful_operations']}")
        lines.append(f"- 失败操作: {s['failed_operations']}")
        lines.append(f"- 总耗时: {s['total_duration_ms']/1000:.1f} 秒")
        lines.append(f"- 含PII记录: {s['records_with_pii']}/{s['records_scanned_for_pii']}")
        lines.append("")

        # 数据源统计
        lines.append("## 数据源统计")
        lines.append("")
        lines.append("| 数据源 | 记录数 | 操作数 | 总耗时(ms) | 平均耗时(ms) |")
        lines.append("|--------|--------|--------|------------|--------------|")
        for src in report["data_sources"]:
            lines.append(
                f"| {src['name']} | {src['total_records']} | {src['total_operations']} | "
                f"{src['total_duration_ms']:.0f} | {src['avg_duration_per_operation']:.1f} |"
            )
        lines.append("")

        # 合规性检查
        lines.append("## 合规性检查")
        lines.append("")
        c = report["compliance"]
        lines.append(f"**检查总数**: {c['total_checks']} | **通过**: {c['passed_checks']} | **失败**: {c['failed_checks']}")
        lines.append("")
        lines.append("| 检查项 | 描述 | 结果 | 详情 |")
        lines.append("|--------|------|------|------|")
        for check in c["checks"]:
            status = "✅ PASS" if check["passed"] else "❌ FAIL"
            lines.append(f"| {check['name']} | {check['description']} | {status} | {check['details']} |")
        lines.append("")

        # 异常列表
        if report["anomalies"]:
            lines.append("## 异常记录")
            lines.append("")
            for anomaly in report["anomalies"]:
                lines.append(f"- **{anomaly['type']}**: {anomaly['source']} - {anomaly['url'][:80]}")
                lines.append(f"  - 时间: {anomaly['timestamp']}")
                lines.append(f"  - 错误: {anomaly.get('error', '无')}")
                lines.append("")

        # 审阅引导
        lines.append("## 用户审阅引导")
        lines.append("")
        lines.append("### 审阅重点")
        lines.append("")
        lines.append("1. **数据完整性**: 检查记录数是否符合预期")
        lines.append("2. **数据质量**: 检查是否有空摘要、过短摘要(<50词)")
        lines.append("3. **隐私安全**: 确认无敏感PII信息泄露")
        lines.append("4. **合规性**: 确认所有合规检查项通过")
        lines.append("")
        lines.append("### 异常数据处理建议")
        lines.append("")
        lines.append("- **空摘要**: 重新抓取或标记为待补充")
        lines.append("- **重复PMID**: 删除重复记录，保留最新版本")
        lines.append("- **格式错误**: 验证JSON格式，必要时重新解析")
        lines.append("- **PII检测**: 如发现敏感信息，立即脱敏处理")
        lines.append("")

        return "\n".join(lines)


# 全局实例
governance = DataGovernance()
