# NovaTour — Project Instructions

## Project Structure
```
Nova/                            ← Git 仓库根
├── README.md
├── novatour/                    ← 【业务核心】
│   ├── backend/                 FastAPI + Strands Agents
│   │   ├── app/
│   │   │   ├── main.py          FastAPI entry
│   │   │   ├── config.py        Pydantic Settings
│   │   │   ├── voice/           Nova Sonic + WebSocket
│   │   │   ├── tools/           8 travel tools
│   │   │   ├── lod/             LOD adaptive system
│   │   │   ├── chat/            Text chat fallback
│   │   │   └── utils/           Audio utilities
│   │   └── tests/               pytest suite
│   └── frontend/                Next.js
│       └── src/
└── reference/                   ← 【开发参考】
    ├── docs/                    规划/研究文档
    ├── projects/                参考项目 (iMean_Piper_Prod, iMeanPiper, syntour1018)
    └── deps/                    SDK + 示例代码
        ├── sdk/                 sdk-python, nova-act, strands-tools
        └── samples/             6 sample repos
```

## Environment
- **Conda env**: `novatour` (Python 3.13) — always activate before running any Python
- **Node**: 18+ for frontend
- **Region**: us-east-1

## Key Commands
```bash
# Backend
conda activate novatour
cd novatour/backend
uvicorn app.main:app --reload --port 8000
python -m pytest tests/ -v

# Frontend
cd novatour/frontend
npm run dev

# Nova Act (separate install due to dep conflict)
pip install -r requirements-nova-act.txt --no-deps
```

## Code Conventions
- Backend: FastAPI + Pydantic, async/await, type hints
- Frontend: Next.js + TypeScript
- Tools: each in `novatour/backend/app/tools/`, return dict with `mock_mode` fallback
- Tests: pytest, mock mode by default

## Important Notes
- nova-act and strands-agents have version conflicts — never install together
- All reference/ content is read-only reference material, do not modify
- .env at project root contains all API credentials
