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


class SelectRequest(BaseModel):
    ids: list
    selected: bool


class ScanRequest(BaseModel):
    path: str


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
<head><title>API Capture</title></head>
<body>
<h1>API Capture Review</h1>
<button onclick="generate()">生成用例</button>
<div id="list"></div>
<script>
async function load() {
    const r = await fetch('/api/requests');
    const data = await r.json();
    document.getElementById('list').innerHTML = data.map(d =>
        `<div><input type="checkbox" data-id="${d.id}"> ${d.method} ${d.path}</div>`
    ).join('');
}
async function generate() {
    await fetch('/api/generate', {method: 'POST'});
    alert('生成完成');
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
        return db.get_all(filters)

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
    async def generate_code():
        selected = db.get_selected()
        if not selected:
            return {"error": "没有选中的接口"}

        pattern = scanner.last_pattern or FrameworkScanner().scan(".")
        from config import API_OUTPUT_DIR, DATA_OUTPUT_DIR, CASE_OUTPUT_DIR

        api_gen = APIGenerator(pattern)
        data_gen = DataGenerator(pattern)
        case_gen = CaseGenerator(pattern)

        api_files = api_gen.generate(selected, API_OUTPUT_DIR)
        data_files = data_gen.generate(selected, DATA_OUTPUT_DIR)
        case_files = case_gen.generate(selected, CASE_OUTPUT_DIR)

        return {
            "success": True,
            "api_count": len(api_files),
            "data_count": len(data_files),
            "case_count": len(case_files),
            "output_dir": str(Path(__file__).parent.parent / "output")
        }

    return app
