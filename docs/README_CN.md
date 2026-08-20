# 中文安装、配置与复现指南

本项目是一套可完整复现的数据科学分析链路，用公开随机实验数据回答两个问题：

1. 营销触达是否带来了平均增量效果？
2. 哪些用户会因为触达而改变行为，应该优先触达？

公开仓库只包含代码、SQL、数据说明、方法文档、汇总结果、图表和运行配置。
简历话术、面试问答及岗位匹配分析不属于项目源码，不放入公开仓库。

## 1. 环境要求

- Python 3.10 或更高版本，推荐 3.11
- 首次真实数据运行需要联网
- 不需要安装数据库服务器，DuckDB 在本地文件中运行
- Windows、macOS 和 Linux 均可运行

## 2. Windows 快速开始

在 PowerShell 中执行：

```powershell
git clone https://github.com/Jacob-Zjy/growth-experimentation-uplift.git
cd growth-experimentation-uplift
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\setup.ps1
.\.venv\Scripts\python.exe scripts\run_pipeline.py
```

启动交互式看板：

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

浏览器打开 Streamlit 输出的本地地址，通常是 `http://localhost:8501`。

如果不希望运行脚本，也可以手动配置：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

## 3. macOS/Linux 快速开始

```bash
git clone https://github.com/Jacob-Zjy/growth-experimentation-uplift.git
cd growth-experimentation-uplift
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python scripts/run_pipeline.py
streamlit run app/streamlit_app.py
```

Conda 用户可使用：

```bash
conda env create -f environment.yml
conda activate growth-experimentation-uplift
python scripts/run_pipeline.py
```

## 4. 流水线做了什么

一次完整运行会依次完成：

1. 下载公开 Hillstrom 数据并执行 MD5 校验；
2. 检查字段、类型、缺失值、唯一键和取值范围；
3. 用 SQL 构建 DuckDB 数据集市与业务指标；
4. 执行 SRM、实验前协变量平衡、Z/Welch 检验及 BH 校正；
5. 计算功效、MDE 与 CUPED；
6. 按 60/20/20 严格划分训练集、验证集和测试集；
7. 独立训练 S/T/X-Learner；
8. 仅在验证集选择模型和触达比例；
9. 在独立测试集报告 Qini、AUUC、Top-k uplift 与固定策略价值；
10. 生成 CSV、图表、决策备忘录、模型文件和运行清单。

## 5. 参数配置

查看完整帮助：

```bash
python scripts/run_pipeline.py --help
```

| 参数 | 默认值 | 作用 |
|---|---:|---|
| `--synthetic` | 关闭 | 使用固定随机种子的合成数据做离线冒烟测试 |
| `--force-download` | 关闭 | 重新下载公开数据并校验 MD5 |
| `--value-per-incremental-visit` | `5.0` | 每次增量访问的情景价值 |
| `--contact-cost` | `0.50` | 每位触达用户的渠道与机会成本 |

修改价值与成本假设：

```bash
python scripts/run_pipeline.py --value-per-incremental-visit 8 --contact-cost 0.75
```

无网络冒烟测试：

```bash
python scripts/run_pipeline.py --synthetic
```

合成模式只用于验证代码能否运行，不能当作正式实验结论。
每次运行的 `artifacts/run_manifest.json` 都会记录 `synthetic`、样本量、模型、
触达比例、增量访问价值和触达成本。

## 6. 输出文件

可公开提交的汇总产物：

- `artifacts/experiment_decision_memo.md`：自动生成的决策备忘录
- `artifacts/run_manifest.json`：运行时间、数据模式与核心配置
- `artifacts/metrics/*.csv`：实验、功效、CUPED、异质性和策略汇总表
- `artifacts/figures/*.png`：实验结果、平衡性、MDE、Qini 与策略价值图

只在本地生成、不会提交到 GitHub 的文件：

- `data/raw/*`：原始公开数据副本
- `data/processed/*`：清洗数据与 DuckDB 数据库
- `artifacts/metrics/scored_*_sample.csv`：用户级评分
- `models/*.joblib`：序列化模型
- `.env` 与 `.streamlit/secrets.toml`：本地秘密配置

这些规则已经写入 `.gitignore`。

## 7. 测试与代码质量

```bash
ruff check src tests scripts app
pytest
```

GitHub Actions 会在 push 和 pull request 时运行相同检查。集成测试使用合成数据，
因此 CI 不依赖外部下载站点。

## 8. 主要代码入口

- `scripts/run_pipeline.py`：命令行入口
- `src/growth_lab/pipeline.py`：全流程编排
- `src/growth_lab/data.py`：下载、MD5 与数据质量检查
- `sql/01_build_mart.sql`：分析数据集市
- `sql/02_business_queries.sql`：业务指标查询
- `src/growth_lab/experiment.py`：实验审计与统计推断
- `src/growth_lab/uplift.py`：S/T/X-Learner、Qini、AUUC 与策略评估
- `app/streamlit_app.py`：交互式决策看板

公开方法文档：

- `docs/experiment_design.md`：实验设计与预分析约定
- `docs/methodology.md`：统计和因果方法说明
- `docs/data_dictionary.md`：字段与指标口径
- `NOTICE.md`：数据来源及再分发声明

## 9. 已核验的公开数据结果

真实数据运行清单中 `synthetic=false`，核心结果为：

- 64,000 名用户三组随机分流；
- SRM p=0.9037，最大绝对 SMD=0.016；
- 男性主题邮件相对对照组：访问率 +7.66 个百分点、转化率 +0.68 个百分点、
  每位符合条件用户收入 +0.770 美元；
- 80% 功效下访问率 MDE 为 0.85 个百分点，转化率 MDE 为 0.22 个百分点；
- CUPED 方差缩减仅 0.05%-0.06%，如实说明实验前变量预测力较弱；
- 验证集选择 X-Learner，独立测试集 Top 10% 用户访问 uplift 为 12.85 个百分点；
- 默认 $5/$0.50 情景下，验证集选择触达 2%，固定策略在测试集的离线净值估计为
  $44.55。

最后一项是离线模型估计，不是已上线利润；上线前仍需新的随机 holdout 验证。

## 10. 数据与因果边界

- 数据来自公开历史零售邮件实验，不是任何目标公司的内部数据；
- 结论对应 14 天观察窗口，不能推断长期效果；
- 随机实验能识别总体 ITT，但个体 uplift 仍是模型估计；
- Qini/AUUC 衡量排序能力，不等于个体因果效应已被准确观测；
- 触达策略依赖明确的价值与成本假设；
- 看板是分析原型，不是生产投放系统。

## 11. 常见问题

**首次下载失败**

检查网络连接，再运行：

```bash
python scripts/run_pipeline.py --force-download
```

**MD5 校验失败**

只删除 `data/raw/` 中已经下载的 CSV，然后重新运行；不要修改代码中的校验值来
绕过错误。

**找不到 Streamlit**

确认已安装开发依赖，或直接调用虚拟环境中的可执行文件：

```powershell
.\.venv\Scripts\streamlit.exe run app\streamlit_app.py
```

**结果与仓库不一致**

先检查 `artifacts/run_manifest.json` 是否为真实数据模式，以及价值、成本参数是否为
默认值；然后确认 Python 与依赖版本。

**可以上传原始数据或用户级评分吗**

不建议。仓库只提交聚合结果；原始数据受上游声明约束，用户级评分也没有公开展示的
必要。
