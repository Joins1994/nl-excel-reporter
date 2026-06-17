"""
NL Excel Reporter - 自然语言驱动的 Excel 报表生成工具
上传 Excel，用自然语言描述需求，自动生成个性化报表。
"""

import os
import json
import re
import traceback
import uuid
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, render_template, send_from_directory

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = os.path.join(os.path.dirname(__file__), "uploads")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ---------------------------------------------------------------------------
# 全局数据存储 (单用户简化方案)
# ---------------------------------------------------------------------------
_data_store: dict[str, dict] = {}
# key = dataset_id, value = {"df": DataFrame, "filename": str, "columns": [...], "shape": (r,c), "dtypes": {...}}


def _serialize_value(v):
    """让 JSON 可序列化"""
    if pd.isna(v):
        return None
    if isinstance(v, (pd.Timestamp, pd.DatetimeTZDtype)):
        return str(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def df_to_records(df: pd.DataFrame, max_rows: int = 5000) -> list[dict]:
    """DataFrame -> JSON records, 安全序列化"""
    df = df.head(max_rows)
    records = []
    for _, row in df.iterrows():
        records.append({k: _serialize_value(v) for k, v in row.items()})
    return records


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# LLM 配置 (支持文件持久化)
# ---------------------------------------------------------------------------
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    defaults = {
        "llm_api_base": "https://api.openai.com/v1",
        "llm_api_key": "",
        "llm_model": "gpt-4o-mini",
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            saved = json.load(f)
            defaults.update(saved)
    return defaults

_config = load_config()
LLM_API_BASE = _config.get("llm_api_base", "https://api.openai.com/v1")
LLM_API_KEY = _config.get("llm_api_key", "")
LLM_MODEL = _config.get("llm_model", "gpt-4o-mini")


def call_llm(system_prompt: str, user_prompt: str) -> str:
    """调用 LLM API 生成 pandas 代码"""
    import urllib.request

    headers = {
        "Content-Type": "application/json",
    }
    if LLM_API_KEY:
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"

    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.1,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{LLM_API_BASE}/chat/completions",
        data=payload,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def generate_pandas_code(df_info: dict, user_query: str) -> dict:
    """
    让 LLM 根据数据结构和用户需求生成 pandas 代码。
    返回 {"code": str, "chart_type": str, "title": str, "description": str}
    """
    system_prompt = """你是一个数据分析专家。用户有一个 pandas DataFrame 变量名叫 `df`，你需要根据用户的自然语言需求生成 Python 代码来处理数据。

规则：
1. 只生成纯 Python 代码，不要写 markdown 标记。
2. 变量 `df` 已经存在，不要重新加载数据。
3. 最终结果必须赋值给变量 `result`，它是一个 pandas DataFrame。
4. 如果需要分组统计，确保结果包含有意义的列名。
5. 结果 DataFrame 的行数不要超过 50 行。
6. 如果用户要求排序，按合理的列排序。
7. 处理中文列名时直接使用原始列名。

同时，你需要在代码后面用 JSON 格式输出图表建议（用 --- 分隔）：
{
  "chart_type": "bar|line|pie|scatter|table|number",
  "title": "报表标题",
  "description": "简短描述",
  "x_column": "X轴列名(可选)",
  "y_column": "Y轴列名(可选)"
}

chart_type 选择规则：
- 比较不同类别 -> bar
- 时间趋势 -> line  
- 占比分布 -> pie
- 两个数值关系 -> scatter
- 纯数据展示 -> table
- 单个汇总数字 -> number

完整输出格式示例：
result = df.groupby('部门')['销售额'].sum().reset_index()
result = result.sort_values('销售额', ascending=False).head(10)
---
{"chart_type": "bar", "title": "各部门销售额TOP10", "description": "按部门汇总销售额排名", "x_column": "部门", "y_column": "销售额"}"""

    columns_info = []
    for col, dtype in df_info["dtypes"].items():
        sample = ""
        if col in df_info.get("samples", {}):
            sample = f" (示例: {df_info['samples'][col]})"
        columns_info.append(f"  - {col} ({dtype}){sample}")

    user_prompt = f"""数据表: {df_info['filename']}
行数: {df_info['shape'][0]}, 列数: {df_info['shape'][1]}

列信息:
{chr(10).join(columns_info)}

用户需求: {user_query}

请生成处理代码和图表建议。"""

    response = call_llm(system_prompt, user_prompt)

    # 解析响应
    code = response
    chart_config = {"chart_type": "table", "title": user_query, "description": ""}

    if "---" in response:
        parts = response.split("---", 1)
        code = parts[0].strip()
        try:
            chart_config = json.loads(parts[1].strip())
        except json.JSONDecodeError:
            pass

    # 清理可能的 markdown 标记
    code = re.sub(r"^```python\s*", "", code)
    code = re.sub(r"\s*```$", "", code)
    code = code.strip()

    return {"code": code, **chart_config}


def execute_code_safely(df: pd.DataFrame, code: str) -> pd.DataFrame:
    """在受限环境中执行生成的代码"""
    safe_builtins = {
        "abs": abs, "all": all, "any": any, "bool": bool,
        "dict": dict, "enumerate": enumerate, "filter": filter,
        "float": float, "format": format, "frozenset": frozenset,
        "int": int, "isinstance": isinstance, "len": len, "list": list,
        "map": map, "max": max, "min": min, "print": print,
        "range": range, "reversed": reversed, "round": round,
        "set": set, "slice": slice, "sorted": sorted, "str": str,
        "sum": sum, "tuple": tuple, "type": type, "zip": zip,
        "True": True, "False": False, "None": None,
    }

    exec_globals = {
        "__builtins__": safe_builtins,
        "df": df.copy(),
        "pd": pd,
        "np": np,
    }

    exec(code, exec_globals)

    result = exec_globals.get("result")
    if result is None:
        raise ValueError("代码未生成 result 变量")
    if isinstance(result, pd.Series):
        result = result.reset_index()
        result.columns = [str(c) for c in result.columns]
    if not isinstance(result, pd.DataFrame):
        result = pd.DataFrame({"result": [result]})

    return result


# ---------------------------------------------------------------------------
# 本地规则引擎 (不需要 LLM 的简单查询)
# ---------------------------------------------------------------------------
def try_local_analysis(df: pd.DataFrame, query: str) -> dict | None:
    """尝试用规则匹配处理常见查询，避免调用 LLM"""
    q = query.lower().strip()
    columns = list(df.columns)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    
    # 数据概览
    if any(kw in q for kw in ["概览", "概况", "基本信息", "数据预览", "overview", "summary"]):
        desc = df.describe().round(2)
        info_rows = []
        for col in columns:
            info_rows.append({
                "列名": col,
                "类型": str(df[col].dtype),
                "非空数": int(df[col].notna().sum()),
                "空值数": int(df[col].isna().sum()),
                "唯一值": int(df[col].nunique()),
            })
        return {
            "result": pd.DataFrame(info_rows),
            "chart_type": "table",
            "title": "数据概览",
            "description": f"共 {len(df)} 行, {len(columns)} 列",
            "code": "# 内置: 数据概览分析",
        }

    # 前N行
    match = re.search(r"前\s*(\d+)\s*[行条]", q)
    if match:
        n = int(match.group(1))
        return {
            "result": df.head(n),
            "chart_type": "table",
            "title": f"前 {n} 行数据",
            "description": f"显示数据表前 {n} 行",
            "code": f"result = df.head({n})",
        }

    # 统计某列
    for col in columns:
        if col.lower() in q and any(kw in q for kw in ["分布", "统计", "计数", "count"]):
            vc = df[col].value_counts().head(20).reset_index()
            vc.columns = [col, "数量"]
            return {
                "result": vc,
                "chart_type": "bar",
                "title": f"{col} 分布统计",
                "description": f"{col} 列各值的出现次数",
                "code": f"result = df['{col}'].value_counts().head(20).reset_index()",
                "x_column": col,
                "y_column": "数量",
            }

    return None


# ---------------------------------------------------------------------------
# Flask 路由
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/upload", methods=["POST"])
def upload():
    """上传 Excel 文件"""
    if "file" not in request.files:
        return jsonify({"error": "未找到文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "文件名为空"}), 400

    ext = Path(file.filename).suffix.lower()
    if ext not in (".xlsx", ".xls", ".csv"):
        return jsonify({"error": "仅支持 .xlsx, .xls, .csv 文件"}), 400

    # 保存文件
    dataset_id = str(uuid.uuid4())[:8]
    safe_name = f"{dataset_id}{ext}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
    file.save(filepath)

    # 读取数据
    try:
        if ext == ".csv":
            df = pd.read_csv(filepath)
        else:
            # 尝试读取所有 sheet
            xls = pd.ExcelFile(filepath)
            sheet_name = request.form.get("sheet", xls.sheet_names[0])
            df = pd.read_excel(filepath, sheet_name=sheet_name)
    except Exception as e:
        return jsonify({"error": f"读取文件失败: {str(e)}"}), 400

    # 清理列名
    df.columns = [str(c).strip() for c in df.columns]

    # 存储数据
    samples = {}
    for col in df.columns[:10]:
        try:
            vals = df[col].dropna().head(3).tolist()
            samples[col] = ", ".join(str(v) for v in vals)
        except Exception:
            samples[col] = ""

    sheets = []
    if ext != ".csv":
        try:
            xls = pd.ExcelFile(filepath)
            sheets = xls.sheet_names
        except Exception:
            pass

    _data_store[dataset_id] = {
        "df": df,
        "filename": file.filename,
        "filepath": filepath,
        "columns": list(df.columns),
        "shape": df.shape,
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "samples": samples,
        "sheets": sheets,
    }

    return jsonify({
        "dataset_id": dataset_id,
        "filename": file.filename,
        "rows": df.shape[0],
        "cols": df.shape[1],
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "preview": df_to_records(df.head(10)),
        "sheets": sheets,
    })


@app.route("/api/datasets", methods=["GET"])
def list_datasets():
    """列出已上传的数据集"""
    return jsonify({
        id: {
            "filename": info["filename"],
            "rows": info["shape"][0],
            "cols": info["shape"][1],
            "columns": info["columns"],
        }
        for id, info in _data_store.items()
    })


@app.route("/api/config", methods=["GET"])
def get_config():
    """获取当前 LLM 配置"""
    return jsonify({
        "llm_api_base": LLM_API_BASE,
        "llm_api_key_masked": "******" + LLM_API_KEY[-4:] if len(LLM_API_KEY) > 4 else "未配置",
        "llm_model": LLM_MODEL,
        "has_key": bool(LLM_API_KEY),
    })


@app.route("/api/config", methods=["POST"])
def save_config():
    """保存 LLM 配置到 config.json"""
    global LLM_API_BASE, LLM_API_KEY, LLM_MODEL

    data = request.get_json()
    LLM_API_BASE = data.get("llm_api_base", "").strip()
    LLM_API_KEY = data.get("llm_api_key", "").strip()
    LLM_MODEL = data.get("llm_model", "").strip()

    if not LLM_API_BASE:
        return jsonify({"error": "API 地址不能为空"}), 400
    if not LLM_API_KEY:
        return jsonify({"error": "API Key 不能为空"}), 400
    if not LLM_MODEL:
        return jsonify({"error": "模型名不能为空"}), 400

    # 保存到文件
    config = {
        "llm_api_base": LLM_API_BASE,
        "llm_api_key": LLM_API_KEY,
        "llm_model": LLM_MODEL,
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

    return jsonify({"ok": True, "message": "配置已保存"})


@app.route("/api/config/test", methods=["POST"])
def test_config():
    """测试 LLM 连接"""
    data = request.get_json()
    test_base = data.get("llm_api_base", "").strip()
    test_key = data.get("llm_api_key", "").strip()
    test_model = data.get("llm_model", "").strip()

    if not all([test_base, test_key, test_model]):
        return jsonify({"error": "请填写完整信息"}), 400

    try:
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {test_key}"}
        payload = json.dumps({
            "model": test_model,
            "messages": [{"role": "user", "content": "Say 'OK' in one word."}],
            "max_tokens": 10,
        }).encode()

        import urllib.request
        req = urllib.request.Request(f"{test_base}/chat/completions", data=payload, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        reply = result["choices"][0]["message"]["content"]
        return jsonify({"ok": True, "reply": reply})
    except Exception as e:
        return jsonify({"error": f"连接失败: {str(e)}"}), 500


@app.route("/api/query", methods=["POST"])
def query():
    """自然语言查询"""
    data = request.get_json()
    dataset_id = data.get("dataset_id")
    user_query = data.get("query", "").strip()

    if not dataset_id or dataset_id not in _data_store:
        return jsonify({"error": "请先上传数据文件"}), 400
    if not user_query:
        return jsonify({"error": "请输入查询内容"}), 400

    store = _data_store[dataset_id]
    df = store["df"]

    # 1. 先尝试本地规则引擎
    local_result = try_local_analysis(df, user_query)
    if local_result and not LLM_API_KEY:
        result_df = local_result["result"]
        return jsonify({
            "success": True,
            "data": df_to_records(result_df),
            "columns": list(result_df.columns),
            "chart_type": local_result.get("chart_type", "table"),
            "title": local_result.get("title", ""),
            "description": local_result.get("description", ""),
            "x_column": local_result.get("x_column", ""),
            "y_column": local_result.get("y_column", ""),
            "code": local_result.get("code", ""),
            "source": "local",
        })

    # 2. 有 LLM API 时，使用 LLM 生成代码
    if not LLM_API_KEY:
        # 没有 LLM 也没匹配到本地规则
        if local_result:
            result_df = local_result["result"]
            return jsonify({
                "success": True,
                "data": df_to_records(result_df),
                "columns": list(result_df.columns),
                "chart_type": local_result.get("chart_type", "table"),
                "title": local_result.get("title", ""),
                "description": local_result.get("description", ""),
                "x_column": local_result.get("x_column", ""),
                "y_column": local_result.get("y_column", ""),
                "code": local_result.get("code", ""),
                "source": "local",
            })
        return jsonify({
            "error": "未配置 LLM API。请设置环境变量 LLM_API_KEY 和 LLM_API_BASE。\n"
                     "目前仅支持内置查询: 数据概览、前N行、列分布统计。"
        }), 400

    try:
        # 调用 LLM 生成代码
        llm_result = generate_pandas_code(
            {
                "filename": store["filename"],
                "shape": store["shape"],
                "dtypes": store["dtypes"],
                "samples": store["samples"],
                "columns": store["columns"],
            },
            user_query,
        )

        code = llm_result["code"]
        chart_type = llm_result.get("chart_type", "table")
        title = llm_result.get("title", user_query)
        description = llm_result.get("description", "")
        x_column = llm_result.get("x_column", "")
        y_column = llm_result.get("y_column", "")

        # 执行代码
        result_df = execute_code_safely(df, code)

        return jsonify({
            "success": True,
            "data": df_to_records(result_df),
            "columns": list(result_df.columns),
            "chart_type": chart_type,
            "title": title,
            "description": description,
            "x_column": x_column,
            "y_column": y_column,
            "code": code,
            "source": "llm",
        })

    except Exception as e:
        return jsonify({
            "error": f"分析失败: {str(e)}",
            "traceback": traceback.format_exc(),
            "code": code if "code" in dir() else "",
        }), 500


@app.route("/api/export", methods=["POST"])
def export():
    """导出报表为 CSV"""
    data = request.get_json()
    records = data.get("data", [])
    title = data.get("title", "report")

    if not records:
        return jsonify({"error": "无数据可导出"}), 400

    df = pd.DataFrame(records)
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False, encoding="utf-8-sig")

    from flask import Response
    return Response(
        csv_buffer.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={title}.csv"},
    )


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  NL Excel Reporter - 自然语言报表工具")
    print("  http://localhost:5000")
    print("=" * 60)
    if LLM_API_KEY:
        print(f"  LLM: {LLM_MODEL} @ {LLM_API_BASE}")
    else:
        print("  LLM: 未配置 (仅内置查询)")
        print("  设置: export LLM_API_KEY=xxx LLM_API_BASE=xxx LLM_MODEL=xxx")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=5000, debug=True)
