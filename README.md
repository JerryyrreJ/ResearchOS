# ResearchOS Thesis Compiler（C 端）

基于冻结契约 `0.1.0-frozen` 的可独立运行后端，负责论点编译、证据语言上限、验证计划、不可变版本与任务事件流。

```powershell
.\.venv\Scripts\Activate.ps1
uvicorn apps.researchos_api.app.main:app --reload --port 8000
```

打开 `http://127.0.0.1:8000/docs` 调用 API。演示脚本：`powershell -ExecutionPolicy Bypass -File scripts/demo.ps1`。

