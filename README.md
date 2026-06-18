# 📊 NL Excel Reporter

> 自然语言驱动的 Excel 报表生成工具

上传 Excel 文件，用自然语言描述需求，自动生成个性化报表和图表。

## ✨ 功能特性

- 📁 **Excel 导入** - 支持 .xlsx, .xls, .csv 格式，拖放上传
- 💬 **自然语言查询** - 用中文描述分析需求，自动生成报表
- 📊 **智能图表** - 自动选择柱状图/折线图/饼图/散点图/数字卡片
- 📋 **双视图** - 图表 + 表格可切换
- 📥 **CSV 导出** - 一键下载报表
- 🔧 **代码透明** - 可查看生成的 pandas 代码
- 📜 **查询历史** - 保存并可回看历史查询
- 🤖 **LLM 驱动** - 接入 OpenAI 兼容 API 处理复杂查询
- ⚡ **内置引擎** - 无 LLM 也能处理常见查询（概览、统计、分布）

## 🚀 快速开始

### Windows

```bash
# 双击 start.bat，或命令行：
cd nl-excel-reporter
pip install -r requirements.txt
python app.py
```

### Mac/Linux

```bash
cd nl-excel-reporter
pip install -r requirements.txt
python app.py
```

然后浏览器打开 **http://localhost:5000**

## 🔧 配置 LLM（可选）

默认使用内置规则引擎。配置 LLM API 可处理更复杂的查询：

**方式 1：网页配置（推荐）**
1. 打开 http://localhost:5000
2. 点击右上角 **⚙️ LLM 配置**
3. 选择预设（OpenAI/DeepSeek/Moonshot/SiliconFlow）
4. 输入 API Key → 测试连接 → 保存

**方式 2：环境变量**
```bash
# OpenAI
set LLM_API_KEY=***
set LLM_API_BASE=https://api.openai.com/v1
set LLM_MODEL=gpt-4o-mini

# DeepSeek
set LLM_API_KEY=***
set LLM_API_BASE=https://api.deepseek.com/v1
set LLM_MODEL=deepseek-chat

# Moonshot (Kimi)
set LLM_API_KEY=***
set LLM_API_BASE=https://api.moonshot.cn/v1
set LLM_MODEL=moonshot-v1-8k
```

## 💡 使用示例

| 自然语言输入 | 输出 |
|--------------|------|
| "数据概览" | 各列的统计信息表 |
| "前20行数据" | 数据预览表格 |
| "按部门统计销售额" | 柱状图 + 汇总表 |
| "销售额最高的10个产品" | TOP10 排行榜 |
| "各地区的占比分布" | 饼图 + 百分比表 |
| "月销售趋势" | 折线图 |
| "A和B的相关性" | 散点图 |

## 📁 项目结构

```
nl-excel-reporter/
├── app.py              # Flask 后端主程序
├── templates/
│   └── index.html      # 前端页面
├── uploads/            # 上传文件存储
├── config.json         # LLM 配置（自动生成）
├── requirements.txt    # Python 依赖
├── start.bat          # Windows 启动脚本
└── README.md
```

## 🛠 技术栈

- **后端**: Python Flask + pandas + numpy
- **前端**: 原生 HTML/CSS/JS (无框架依赖)
- **图表**: ECharts 5
- **LLM**: OpenAI 兼容 API (可选)

## 🔒 安全说明

- API Key 仅保存在本地 `config.json` 文件
- 上传的文件存储在本地 `uploads/` 目录
- 默认不配置 LLM 时，仅使用本地规则引擎

## 📝 开发说明

```bash
# 安装开发依赖
pip install -r requirements.txt

# 启动开发服务器
python app.py

# 访问
http://localhost:5000
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

MIT License

---

**作者**: Joins1994
**GitHub**: https://github.com/Joins1994/nl-excel-reporter