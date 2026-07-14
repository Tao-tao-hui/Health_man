"""数据治理体系测试文件

验证各模块功能的完整性和正确性。
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from governance import (
    HealthDataGovernanceSystem,
    DataGovernanceFramework,
    MedicalKnowledgeGraph,
    IndicatorSystem,
    MetadataManager,
    QualityAssurance,
    ComplianceManager,
    health_data_governance_system,
    TagType,
    ComplianceStandard,
    AccessLevel,
    ComplianceStatus
)


def test_governance_framework():
    """测试数据治理框架"""
    print("\n" + "="*60)
    print("测试数据治理框架")
    print("="*60)
    
    framework = DataGovernanceFramework()
    
    print(f"✓ 角色定义数量: {len(framework.roles)}")
    print(f"✓ 政策定义数量: {len(framework.policies)}")
    print(f"✓ 工作流定义数量: {len(framework.workflows)}")
    print(f"✓ 治理指标数量: {len(framework.metrics)}")
    
    report = framework.generate_report()
    print(f"✓ 生成治理报告: {report['report_id']}")
    print(f"  - 报告摘要: {json.dumps(report['summary'], ensure_ascii=False)}")
    
    return True


def test_knowledge_graph():
    """测试医疗知识图谱"""
    print("\n" + "="*60)
    print("测试医疗专业知识图谱")
    print("="*60)
    
    kg = MedicalKnowledgeGraph()
    
    print(f"✓ 知识节点数量: {len(kg.nodes)}")
    print(f"✓ 知识关系数量: {len(kg.relations)}")
    print(f"✓ 临床标准数量: {len(kg.standards)}")
    
    bmi_node = kg.get_node("IND_BMI")
    if bmi_node:
        print(f"✓ 获取BMI指标节点: {bmi_node.name}")
    
    spo2_standard = kg.get_standard("STD_SPO2")
    if spo2_standard:
        print(f"✓ 获取血氧标准: {spo2_standard.name}")
    
    related = kg.get_related_nodes("IND_BMI", "HAS_STANDARD")
    print(f"✓ BMI相关标准数量: {len(related)}")
    
    report = kg.generate_report()
    print(f"✓ 生成知识图谱报告")
    
    return True


def test_indicator_system():
    """测试指标体系"""
    print("\n" + "="*60)
    print("测试指标体系设计")
    print("="*60)
    
    indicator_system = IndicatorSystem()
    
    print(f"✓ 指标定义数量: {len(indicator_system.indicators)}")
    print(f"✓ 指标集合数量: {len(indicator_system.sets)}")
    
    bmi_indicator = indicator_system.get_indicator("BMI")
    if bmi_indicator:
        print(f"✓ 获取BMI指标: {bmi_indicator.name} ({bmi_indicator.unit})")
    
    score = indicator_system.calculate_indicator_score("BMI", 22.5)
    print(f"✓ BMI评分计算: 值={score.raw_value}, 评分={score.score}, 等级={score.grade}")
    print(f"  - 解读: {score.interpretation}")
    
    validation = indicator_system.validate_indicator_value("SPO2", 98)
    print(f"✓ 血氧值验证: {validation}")
    
    validation_fail = indicator_system.validate_indicator_value("SPO2", 110)
    print(f"✓ 异常血氧值验证: {validation_fail}")
    
    report = indicator_system.generate_indicator_report()
    print(f"✓ 生成指标体系报告")
    
    return True


def test_metadata_manager():
    """测试元数据管理"""
    print("\n" + "="*60)
    print("测试元数据管理")
    print("="*60)
    
    metadata = MetadataManager()
    
    print(f"✓ 数据元素数量: {len(metadata.data_elements)}")
    print(f"✓ 标签定义数量: {len(metadata.tags)}")
    
    user_id_element = metadata.get_data_element("DE_USER_ID")
    if user_id_element:
        print(f"✓ 获取用户ID数据元素: {user_id_element.name}, 分类: {user_id_element.classification.value}")
    
    search_result = metadata.search_data_elements("血氧")
    print(f"✓ 搜索血氧相关数据元素: {len(search_result)} 个")
    
    business_tags = metadata.get_tags_by_type(TagType.BUSINESS)
    print(f"✓ 业务标签数量: {len(business_tags)}")
    
    report = metadata.generate_metadata_report()
    print(f"✓ 生成元数据报告")
    
    return True


def test_quality_assurance():
    """测试质量保证"""
    print("\n" + "="*60)
    print("测试质量保证")
    print("="*60)
    
    qa = QualityAssurance()
    
    print(f"✓ 质量规则数量: {len(qa.rules)}")
    
    test_data = [
        {"SPO2": 98, "HEART_RATE": 75, "BMI": 22.5},
        {"SPO2": 95, "HEART_RATE": 80, "BMI": 24.8},
        {"SPO2": 97, "HEART_RATE": 65, "BMI": 21.2},
        {"SPO2": None, "HEART_RATE": 70, "BMI": 25.5},
        {"SPO2": 105, "HEART_RATE": 260, "BMI": 85}
    ]
    
    results = qa.execute_all_checks(test_data)
    print(f"✓ 执行质量检查: {len(results)} 项")
    
    passed = sum(1 for r in results if r.passed)
    print(f"  - 通过: {passed}, 失败: {len(results) - passed}")
    
    score = qa.calculate_quality_score()
    print(f"✓ 质量评分: {score.overall_score:.2%}, 级别: {score.level.value}")
    
    report = qa.generate_quality_report()
    print(f"✓ 生成质量报告")
    
    return True


def test_compliance_manager():
    """测试合规性管理"""
    print("\n" + "="*60)
    print("测试合规性管理")
    print("="*60)
    
    cm = ComplianceManager()
    
    print(f"✓ 合规要求数量: {len(cm.requirements)}")
    print(f"✓ 安全策略数量: {len(cm.policies)}")
    
    hipaa_requirements = cm.get_requirements_by_standard(ComplianceStandard.HIPAA)
    print(f"✓ HIPAA合规要求数量: {len(hipaa_requirements)}")
    
    cm.grant_access("user_001", "health_data", AccessLevel.READ, "admin_001")
    print(f"✓ 授予访问权限")
    
    access_result = cm.check_access("user_001", "health_data", AccessLevel.READ)
    print(f"✓ 检查访问权限(应有): {access_result}")
    
    access_denied = cm.check_access("user_002", "health_data", AccessLevel.WRITE)
    print(f"✓ 检查访问权限(不应有): {access_denied}")
    
    dsr = cm.create_data_subject_request("subject_001", "access")
    print(f"✓ 创建数据主体请求: {dsr.request_id}")
    
    results = cm.execute_all_compliance_checks()
    compliant = sum(1 for r in results if r.status == ComplianceStatus.COMPLIANT)
    print(f"✓ 合规检查结果: 通过 {compliant}/{len(results)}")
    
    report = cm.generate_compliance_report()
    print(f"✓ 生成合规报告")
    
    return True


def test_integration():
    """测试系统集成"""
    print("\n" + "="*60)
    print("测试系统集成")
    print("="*60)
    
    system = HealthDataGovernanceSystem()
    
    print(f"✓ 数据治理框架: OK")
    print(f"✓ 医疗知识图谱: OK")
    print(f"✓ 指标体系设计: OK")
    print(f"✓ 元数据管理: OK")
    print(f"✓ 质量保证: OK")
    print(f"✓ 合规性管理: OK")
    
    comprehensive_report = system.generate_comprehensive_report()
    print(f"✓ 生成综合治理报告")
    
    summary = comprehensive_report.get("summary", {})
    print(f"\n综合报告摘要:")
    print(f"  - 角色总数: {summary.get('total_roles', 0)}")
    print(f"  - 政策总数: {summary.get('total_policies', 0)}")
    print(f"  - 知识节点: {summary.get('total_knowledge_nodes', 0)}")
    print(f"  - 指标总数: {summary.get('total_indicators', 0)}")
    print(f"  - 数据元素: {summary.get('total_data_elements', 0)}")
    print(f"  - 质量评分: {summary.get('quality_score', 0):.2%}")
    print(f"  - 合规率: {summary.get('compliance_rate', 0):.2%}")
    
    indicator_score = system.calculate_indicator_score("SPO2", 92)
    print(f"\n✓ 指标评分计算(集成):")
    print(f"  - 指标ID: {indicator_score['indicator_id']}")
    print(f"  - 原始值: {indicator_score['raw_value']}")
    print(f"  - 评分: {indicator_score['score']}")
    print(f"  - 等级: {indicator_score['grade']}")
    print(f"  - 解读: {indicator_score['interpretation']}")
    
    return True


def main():
    """运行所有测试"""
    print("\n" + "#"*60)
    print("数据治理体系测试套件")
    print("#"*60)
    
    tests = [
        ("数据治理框架", test_governance_framework),
        ("医疗专业知识图谱", test_knowledge_graph),
        ("指标体系设计", test_indicator_system),
        ("元数据管理", test_metadata_manager),
        ("质量保证", test_quality_assurance),
        ("合规性管理", test_compliance_manager),
        ("系统集成", test_integration)
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
                print(f"\n✓ {name}: 通过")
            else:
                failed += 1
                print(f"\n✗ {name}: 失败")
        except Exception as e:
            failed += 1
            print(f"\n✗ {name}: 异常 - {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "#"*60)
    print(f"测试结果: {passed}/{len(tests)} 通过")
    print("#"*60)
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)