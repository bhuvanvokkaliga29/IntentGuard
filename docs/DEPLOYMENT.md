# Deployment & Operations Guide

## 1. Local Development Setup
```bash
# 1. Clone repository
git clone https://github.com/bhuvanvokkaliga29/IntentGuard.git
cd IntentGuard

# 2. Configure environment
cp .env.example .env
# Fill in GEMINI_API_KEY or XAI_API_KEY (or use LLM_PROVIDER=mock for offline development)

# 3. Setup backend dependencies
python -m pip install -r backend/requirements.txt

# 4. Setup frontend dependencies
cd frontend && npm install && cd ..

# 5. Launch development services
make dev
```

## 2. Docker Compose Deployment
```bash
docker-compose up --build
```
- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:3000`
- OpenAPI Docs: `http://localhost:8000/docs`

## 3. Verification & Benchmark Execution
```bash
# Run 102 automated unit & integration tests
make test

# Run End-to-End smoke test
make smoke

# Generate synthetic dataset and evaluate benchmark
make seed
make evaluate

# Run repository security audit
make audit
```
