import sys
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from storage.db import Database
from analyzer.scanner import FrameworkScanner
from generator.api_gen import APIGenerator
from generator.data_gen import DataGenerator
from generator.case_gen import CaseGenerator
from generator.lounger_gen import LoungerGenerator
from generator.lounger_python_gen import LoungerPythonGenerator


class SelectRequest(BaseModel):
    ids: list
    selected: bool


class ScanRequest(BaseModel):
    path: str


class GenerateRequest(BaseModel):
    scenario_name: str = "tm_core_flow"


def create_app(db_path: str) -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(title="API Capture Review")
    db = Database(db_path)
    scanner = FrameworkScanner()

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return """
<!DOCTYPE html>
<html>
<head>
<title>API Capture</title>
<style>
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; color: #1f2937; }
.toolbar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 16px; }
input, select, button { box-sizing: border-box; height: 34px; padding: 0 10px; }
#keyword { width: 260px; }
#domain { min-width: 260px; }
.summary { margin: 8px 0; color: #64748b; }
.request { display: grid; grid-template-columns: 24px 62px minmax(240px, 1fr) 56px 150px; gap: 8px; align-items: center; padding: 7px 8px; border-bottom: 1px solid #e5e7eb; }
.request:hover { background: #f8fafc; }
.method { font-weight: 600; }
.host { color: #64748b; margin-right: 6px; }
.path { overflow-wrap: anywhere; }
.status-ok { color: #15803d; }
.status-error { color: #b91c1c; }
</style>
</head>
<body>
<h1>API Capture Review</h1>
<div class="toolbar">
  <label>场景名称 <input id="scenario-name" value="tm_core_flow"></label>
  <input id="keyword" placeholder="搜索接口路径" oninput="render()">
  <select id="domain" onchange="render()"><option value="ALL">所有域名</option></select>
  <select id="method" onchange="render()">
    <option value="ALL">所有方法</option>
    <option>POST</option><option>GET</option><option>PUT</option><option>PATCH</option><option>DELETE</option>
  </select>
  <button onclick="selectVisible(true)">勾选当前结果</button>
  <button onclick="selectVisible(false)">取消当前结果</button>
  <button onclick="generate()">生成用例</button>
</div>
<div id="summary" class="summary"></div>
<div id="list"></div>
<script>
let requests = [];

function rootDomain(host) {
    const parts = host.split('.');
    return parts.length >= 2 ? parts.slice(-2).join('.') : host;
}

function hostOf(request) {
    try { return new URL(request.url).hostname; } catch (_) { return ''; }
}

function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    })[char]);
}

async function load() {
    const r = await fetch('/api/requests');
    requests = await r.json();

    const domainCounts = {};
    requests.forEach(item => {
        const domain = rootDomain(hostOf(item));
        if (domain) domainCounts[domain] = (domainCounts[domain] || 0) + 1;
    });
    const domains = Object.entries(domainCounts).sort((a, b) => b[1] - a[1]);
    const domainSelect = document.getElementById('domain');
    domainSelect.innerHTML = '<option value="ALL">所有域名</option>' + domains.map(
        ([domain, count]) => `<option value="${escapeHtml(domain)}">*.${escapeHtml(domain)} (${count})</option>`
    ).join('');
    if (domains.length) domainSelect.value = domains[0][0];
    render();
}

function visibleRequests() {
    const keyword = document.getElementById('keyword').value.trim().toLowerCase();
    const domain = document.getElementById('domain').value;
    const method = document.getElementById('method').value;
    return requests.filter(item => {
        const host = hostOf(item);
        if (domain !== 'ALL' && host !== domain && !host.endsWith(`.${domain}`)) return false;
        if (method !== 'ALL' && item.method !== method) return false;
        if (keyword && !`${host}${item.path}`.toLowerCase().includes(keyword)) return false;
        return true;
    });
}

function render() {
    const visible = visibleRequests();
    document.getElementById('summary').textContent = `显示 ${visible.length} / ${requests.length} 条；默认选择请求数最多的业务域，可切换“所有域名”。`;
    document.getElementById('list').innerHTML = visible.map(item => {
        const host = hostOf(item);
        const statusClass = item.response_code >= 400 ? 'status-error' : 'status-ok';
        return `<div class="request">
          <input type="checkbox" data-id="${item.id}" ${item.selected ? 'checked' : ''} onchange="selectRequest(this)">
          <span class="method">${item.method}</span>
          <span><span class="host">${escapeHtml(host)}</span><span class="path">${escapeHtml(item.path)}</span></span>
          <span class="${statusClass}">${item.response_code ?? '-'}</span>
          <span>${escapeHtml(item.timestamp)}</span>
        </div>`;
    }).join('') || '<p>没有符合条件的接口</p>';
}
async function selectRequest(checkbox) {
    const r = await fetch('/api/select', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ids: [Number(checkbox.dataset.id)], selected: checkbox.checked})
    });
    if (!r.ok) {
        checkbox.checked = !checkbox.checked;
        alert('选择接口失败');
        return;
    }
    const item = requests.find(item => item.id === Number(checkbox.dataset.id));
    if (item) item.selected = checkbox.checked ? 1 : 0;
}
async function selectVisible(selected) {
    const visible = visibleRequests();
    if (!visible.length) return;
    const r = await fetch('/api/select', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ids: visible.map(item => item.id), selected})
    });
    if (!r.ok) {
        alert('批量选择接口失败');
        return;
    }
    visible.forEach(item => item.selected = selected ? 1 : 0);
    render();
}
async function generate() {
    const scenarioName = document.getElementById('scenario-name').value || 'tm_core_flow';
    const r = await fetch('/api/generate', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({scenario_name: scenarioName})
    });
    const data = await r.json();
    if (data.error) {
        alert(data.error);
        return;
    }
    alert(`生成完成：Python 场景 ${data.python_count} 个文件，YAML/Lounger ${data.lounger_count} 个文件\n${data.python_case_path}`);
}
load();
</script>
</body>
</html>
"""

    @app.get("/api/requests")
    async def get_requests(method: Optional[str] = None):
        filters = {}
        if method and method != 'ALL':
            filters['method'] = method
        # Review 列表只返回选择所需的摘要，避免把 Token、Cookie、请求体等
        # 敏感数据暴露给页面脚本。生成器仍直接从本地数据库读取完整记录。
        fields = ('id', 'timestamp', 'method', 'url', 'path', 'response_code', 'selected')
        return [
            {field: record.get(field) for field in fields}
            for record in db.get_all(filters)
        ]

    @app.post("/api/select")
    async def update_selected(req: SelectRequest):
        if req.ids == 'all':
            records = db.get_all()
            ids = [r['id'] for r in records]
        else:
            ids = req.ids
        db.update_selected(ids, req.selected)
        return {"success": True}

    @app.post("/api/scan")
    async def scan_framework(req: ScanRequest):
        pattern = scanner.scan(req.path)
        return pattern.to_dict() if pattern else {}

    @app.post("/api/generate")
    async def generate_code(req: Optional[GenerateRequest] = None):
        selected = db.get_selected()
        if not selected:
            return {"error": "没有选中的接口"}

        pattern = scanner.last_pattern or FrameworkScanner().scan(".")
        from config import API_OUTPUT_DIR, DATA_OUTPUT_DIR, CASE_OUTPUT_DIR, LOUNGER_OUTPUT_DIR

        api_gen = APIGenerator(pattern)
        data_gen = DataGenerator(pattern)
        case_gen = CaseGenerator(pattern)
        lounger_gen = LoungerGenerator(pattern)
        lounger_python_gen = LoungerPythonGenerator(pattern)

        api_files = api_gen.generate(selected, API_OUTPUT_DIR)
        data_files = data_gen.generate(selected, DATA_OUTPUT_DIR)
        case_files = case_gen.generate(selected, CASE_OUTPUT_DIR)
        lounger_files = lounger_gen.generate(
            selected,
            LOUNGER_OUTPUT_DIR,
            scenario_name=req.scenario_name if req else "tm_core_flow",
        )
        python_files = lounger_python_gen.generate(
            selected,
            LOUNGER_OUTPUT_DIR,
            scenario_name=req.scenario_name if req else "tm_core_flow",
        )
        python_case_path = next(
            (path for path in python_files if path.name.startswith("test_")),
            None,
        )

        return {
            "success": True,
            "api_count": len(api_files),
            "data_count": len(data_files),
            "case_count": len(case_files),
            "lounger_count": len(lounger_files),
            "python_count": 1 if python_case_path else 0,
            "python_case_path": str(python_case_path) if python_case_path else "",
            "lounger_output_dir": str(LOUNGER_OUTPUT_DIR),
            "output_dir": str(Path(__file__).parent.parent / "output")
        }

    return app
