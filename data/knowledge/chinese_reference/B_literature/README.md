# B_literature - Layer B 文献聚合数据

## 目录结构
- `_metadata/`：三层元数据（L0/L1/L2）
- `_standards/`：标准文档（如中医体质 ZYYXH/T157-2009）
- `_logs/`：提取日志（literature_extraction_log.csv）
- `pubmed/abstracts/`：PubMed 摘要 XML
- `pubmed/fulltext/`：PubMed 全文 PDF（仅开放获取）
- `openscience/`：figshare/Dryad/Zenodo 数据集
- `gasc_2025/`：GASC 2025 PDF 附录
- `tcm_constitution/`：中医体质 9 型数据

## 体量上限
500MB（预估实际 200MB）

## 数据来源
- PubMed Central（NCBI E-utilities API）
- figshare / Dryad / Zenodo（平台 API）
- GASC 2025（PMID:40620559 附录）
- 中医体质 ZYYXH/T157-2009 国标
