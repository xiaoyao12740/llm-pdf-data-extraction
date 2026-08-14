# 基于 LLM 增强的 PDF 非结构化数据智能抽取系统

[![CI](https://github.com/xiaoyao12740/llm-pdf-data-extraction/actions/workflows/ci.yml/badge.svg)](https://github.com/xiaoyao12740/llm-pdf-data-extraction/actions/workflows/ci.yml) · [中文](README_zh-CN.md) | [English](README.md)

一个可审计、规则优先、本地 LLM 选择性语义恢复、带类型化证据校验和 MySQL 数据血缘的 PDF 抽取工程原型。

![系统架构](reports/figures/01_system_architecture.png)

## 架构原则

项目不采用难以审计的“整份 PDF → LLM → JSON”，而是：

`PDF → 保留页码的解析 → 确定性候选 → 选择性 LLM 恢复 → 标准化 → Schema/业务校验 → MySQL → 可选评估`

规则负责明确值；LLM 只处理缺失或低置信字段；程序校验类型、声明页码、逐字证据和业务一致性。LLM 不能仅凭自报置信度覆盖确定性候选。

## 核心能力

- PyMuPDF 文本解析和 pdfplumber 表格解析，全程保留页码。
- 五种固定 seed 布局：键值对、别名、跨行、表格、语义叙述。
- 字段溯源：原始值、标准值、页码、原文、方法、置信度、状态和运行批次。
- Pydantic 类型化 Ollama 响应与“页码 + 原文逐字 quote”绑定。
- 字段相关上下文检索；程序插入的 page marker 不能充当 PDF 证据。
- Ollama 不可用时支持默认 `fallback_rules` 或显式 `fail_fast`。
- source truth、canonical truth 与异常 Precision/Recall/F1 分开计算。
- MySQL 单文档事务和 GitHub Actions MySQL 8.0 集成测试。

## 可复现 benchmark

![PDF 模板](reports/figures/02_pdf_templates.png)

生成器创建 100 份无隐私数据报告，每种模板 20 份。20 份 narrative 报告包含 60 个“原文明示、但确定性规则无法识别”的字段；另外注入日期反转、比率不一致和真正缺失的比率。

每条真值同时保存：

- `source_truth`：PDF 实际展示值；
- `canonical_truth`：业务正确值；
- `anomaly_type`：期望检测出的异常。

```bash
python -m src.generators.generate_sample_pdfs --count 100 --seed 42
```

## LLM 安全契约

![可追溯流水线](reports/figures/03_extraction_pipeline.png)

模型只接收检索出的文本片段，不接收 PDF 二进制或 ground truth。响应必须包含字段、值、置信度、页码、证据和理由。非空值只有在证据逐字存在于声明页时才能采用。非法 JSON、数组/标量、错误字段或页码、虚假 quote、类型错误、超时和 HTTP 故障都会被拒绝或按策略降级。

## 实测结果

以下指标来自 seed 42、100 份 PDF、700 个字段的真实运行：

| 方法 | Source 抽取准确率 | Canonical 匹配率 | Source 整份匹配 | Canonical 整份匹配 | 异常 F1 |
|---|---:|---:|---:|---:|---:|
| Rules Only | 91.57% | 89.29% | 80/100 | 70/100 | 54.55% |
| Rules + Ollama (`qwen2.5:7b`) | **100.00%** | **97.57%** | **100/100** | **87/100** | **100.00%** |

本地 CPU 实验耗时 868.25 秒，共 63 次字段调用：59 次通过页码和证据门禁的语义恢复，4 次对真正缺失值 abstain，0 个被接受的幻觉值。剩余 canonical 差异来自异常源数据；系统正确报告 4 个日期反转、5 个比率不一致和 4 个缺失比率。

![字段准确率](reports/figures/05_field_accuracy.png)

![规则与 LLM 对比](reports/figures/06_method_comparison.png)

![校验异常](reports/figures/07_validation_issues.png)

## 生产抽取与评估已解耦

没有 ground truth 也可以正常抽取：

```bash
python -m src.pipeline --llm disabled --database disabled
python -m src.pipeline --llm ollama --model qwen2.5:7b --llm-failure-policy fallback_rules
```

只有 benchmark 才显式开启评估：

```bash
python -m src.pipeline --llm disabled --evaluate
python -m src.evaluation.evaluate_extraction \
  --results data/processed/extraction_details.json \
  --ground-truth data/ground_truth/ground_truth.json
```

## MySQL 数据血缘

![MySQL Schema](reports/figures/04_mysql_schema.png)

MySQL 8.0 使用 SHA-256 文档身份、单文档事务、`(run_id, field_name)` 唯一字段、每次运行一条业务记录，并保存 batch、pipeline/schema/prompt 版本、配置 hash 和 Git commit。旧版数据库可执行一次 `sql/06_upgrade_v2.sql`。

## 快速开始

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m src.generators.generate_sample_pdfs --count 100 --seed 42
.venv/Scripts/python -m src.pipeline --llm disabled
.venv/Scripts/python -m pytest -q
```

仓库的 `samples/` 内提供 3 份不含个人或生产数据的安全合成 PDF。若要让路径、校验容差、MySQL 和 Ollama 由 YAML 驱动，可复制并修改 `config/config.example.yaml`，再运行 `python -m src.pipeline --config config/config.yaml`；显式 CLI 参数优先于 YAML。

配置 MySQL 时复制 `.env.example` 为 `.env`，替换凭据，执行前三个 SQL，再使用 `--database mysql`。项目此前已在 MySQL 8.0.42 完成 100 文档真实写入；CI 现在会创建全新 MySQL 8.0 服务，测试 repository、重复 hash、唯一约束与事务回滚。

## 测试、局限与定位

本地测试覆盖多页、纯图像和损坏 PDF 行为、别名、表格 provenance、标准化、双真值指标、异常评分、YAML 配置、页码/证据绑定、非法 JSON、确定性 arbitration 和无 ground truth 抽取。CI 覆盖 Python 3.10/3.11/3.12、MySQL 8.0 和 Ruff。

这是工程原型而不是“通用 PDF 准确率”声明；扫描 PDF 需要 OCR，复杂合并表格需要更强版面模型，本地 CPU 推理较慢，证据绑定可降低幻觉风险但不等于彻底解决提示词注入，置信度仍是未校准 heuristic。

技术栈：Python 3.10+、PyMuPDF、pdfplumber、reportlab、Pydantic、Ollama、SQLAlchemy、PyMySQL、MySQL 8.0、Matplotlib、pytest、Ruff、GitHub Actions。MIT License。
