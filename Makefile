.PHONY: setup fixture parse index graph test eval api ui sandbox
setup:
	python -m pip install -e '.[dev]'
fixture:
	python -m scripts.create_fixture_repo
parse:
	python -m scripts.parse_repository --repo data/fixture_repo
index:
	python -m scripts.build_index --repo data/fixture_repo --embedding hash
graph:
	python -m scripts.build_graph --repo data/fixture_repo
test:
	pytest -q
eval:
	python -m scripts.run_full_evaluation --fixture
api:
	uvicorn repoatlas.api.main:app --reload --port 8080
ui:
	python app/gradio_app.py
sandbox:
	docker build -t repoatlas-sandbox:latest sandbox
