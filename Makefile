# IntentGuard — Developer Workflow Makefile

.PHONY: setup dev test evaluate seed smoke audit clean

setup:
	python -m pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	@echo "Starting IntentGuard backend and frontend servers..."
	python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
	cd frontend && npm run dev

test:
	python -m pytest

evaluate:
	python scripts/evaluate.py --dataset backend/data/synthetic_dataset.json --output docs/reports/evaluation_report.json --provider mock

seed:
	python scripts/generate_dataset.py --seed 42 --count 500 --output backend/data/synthetic_dataset.json

smoke:
	python scripts/smoke_test.py

audit:
	python scripts/repo_audit.py --output docs/reports/repo_audit_report.json

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
