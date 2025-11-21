.PHONY: help install install-dev test lint format clean run-server

help: ## Mostra esta mensagem de ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências do projeto
	pip install -r requirements.txt

install-dev: ## Instala dependências de desenvolvimento
	pip install -r requirements-dev.txt
	pre-commit install

test: ## Executa testes
	pytest tests/ -v

test-cov: ## Executa testes com cobertura
	pytest tests/ -v --cov=. --cov-report=html --cov-report=term

lint: ## Verifica estilo de código
	flake8 . --max-line-length=100 --extend-ignore=E203,W503
	black --check .
	isort --check-only .

format: ## Formata código automaticamente
	black .
	isort .

clean: ## Remove arquivos gerados
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type d -name "*.egg-info" -exec rm -r {} +
	find . -type d -name ".pytest_cache" -exec rm -r {} +
	find . -type d -name ".mypy_cache" -exec rm -r {} +
	rm -rf build/ dist/ .coverage htmlcov/

run-server: ## Inicia o servidor web
	cd web && python3 server.py

run-game: ## Executa jogo no terminal
	python3 -m game.game

run-game-advanced: ## Executa jogo avançado
	python3 -m game.game_advanced

run-console: ## Executa jogo console interativo
	python3 -m game.play_console

