.PHONY: help install install-dev test lint format clean run-server

# Detecta o Python correto (com pokerkit instalado)
# Tenta diferentes versões de Python até encontrar uma com pokerkit
PYTHON := $(shell \
	if python3.11 -c "import pokerkit" 2>/dev/null; then \
		echo "python3.11"; \
	elif python3.10 -c "import pokerkit" 2>/dev/null; then \
		echo "python3.10"; \
	elif python3.9 -c "import pokerkit" 2>/dev/null; then \
		echo "python3.9"; \
	elif python3 -c "import pokerkit" 2>/dev/null; then \
		echo "python3"; \
	else \
		echo "python3"; \
	fi \
)

help: ## Mostra esta mensagem de ajuda
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Instala dependências do projeto
	$(PYTHON) -m pip install -r requirements.txt

install-dev: ## Instala dependências de desenvolvimento
	$(PYTHON) -m pip install -r requirements-dev.txt
	pre-commit install

test: ## Executa testes
	$(PYTHON) -m pytest tests/ -v

test-cov: ## Executa testes com cobertura
	$(PYTHON) -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term

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
	cd web && $(PYTHON) server.py

run-game: ## Executa jogo no terminal
	$(PYTHON) -m game.game

run-game-advanced: ## Executa jogo avançado
	$(PYTHON) -m game.game_advanced

run-console: ## Executa jogo console interativo
	@echo "Usando Python: $(PYTHON)"
	@$(PYTHON) -c "import sys; print(f'Versão: {sys.version}')" 2>/dev/null || true
	@$(PYTHON) -c "import pokerkit; print('✓ pokerkit encontrado')" 2>/dev/null || echo "⚠ pokerkit não encontrado - o jogo pode não funcionar corretamente"
	@echo ""
	$(PYTHON) -m game.play_console

