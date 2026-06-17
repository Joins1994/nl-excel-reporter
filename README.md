# NL Excel Reporter 📊

自然语言驱动的 Excel 报表生成工具。上传 Excel 文件，用自然语言描述需求，自动生成个性化报表和图表。

## 功能特性

- 📁 **Excel 导入** - 支持 .xlsx, .xls, .csv 格式，拖放上传
- 💬 **自然语言查询** - 用中文描述分析需求，自动生成报表
- 📊 **智能图表** - 自动选择柱状图/折线图/饼图/散点图
- 📋 **数据表格** - 支持表格和图表双视图切换
- 📥 **报表导出** - 一键导出 CSV 格式
- 🔧 **代码展示** - 可查看底层 pandas 分析代码
- 📜 **查询历史** - 保存查询记录，支持一键回看
- 🤖 **LLM 驱动** - 接入 OpenAI 兼容 API 处理复杂查询
- ⚡ **内置引擎** - 无 LLM 也能处理常见查询（概览、统计、分布）

## 快速启动

### Windows
```bash
双击 start.bat
```

### 命令行
```bash
pip install -r requirements.txt
python app.py
```

然后打开 http://localhost:5000

## 配置 LLM (可选)

设置环境变量即可接入 LLM：

```bash
# OpenAI
set LLM_API_KEY=sk-xxx
set LLM_API_BASE=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini

# 兼容 API (DeepSeek, Moonshot, 等)
set LLM_API_KEY=your-***
set LLM_API_BASE=https://api.deepseek.com/v1
set LLM_MODEL=deepseek-chat

python app.py
```

不配置 LLM 时，工具使用内置规则引擎处理常见查询。

## 使用示例

| 自然语言输入 | 输出 |
|---|---|
| "数据概览" | 各列的统计信息表 |
| "前20行数据" | 数据预览表格 |
| "按部门统计销售额" | 柱状图 + 汇总表 |
| "销售额最高的10个产品" | TOP10 排行榜 |
| "各地区的占比分布" | 饼图 + 百分比表 |
| "月销售趋势" | 折线图 |
| "A和B的相关性" | 散点图 |

## 技术栈

- **后端**: Python Flask + pandas + numpy
- **前端**: 原生 HTML/CSS/JS (无框架依赖)
- **图表**: ECharts 5
- **LLM**: OpenAI 兼容 API (可选)

## 项目结构

```
nl-excel-reporter/
├── app.py              # Flask 后端主程序
├── templates/
│   └── index.html      # 前端页面 (单文件应用)
├── uploads/            # 上传文件存储
├── requirements.txt    # Python 依赖
├── start.bat          # Windows 启动脚本
└── README.md
```
