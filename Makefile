.DEFAULT_GOAL := help

VENV_DIR ?= ./venv
DATA_DIR ?= ./data
SCRIPTS_DIR ?= ./scripts
NOTEBOOKS_DIR ?= ./notebooks

FILES_TO_FORMAT_PYTHON=scripts src tests setup.py doc/conf.py

ECR_REGISTRY ?= 652601739724.dkr.ecr.ap-southeast-2.amazonaws.com
WORKFLOW_IMAGE ?= $(ECR_REGISTRY)/climate_assessment

SR15_EMISSIONS_SCRAPER = $(SCRIPTS_DIR)/get_test_sr15_data.py
SR15_EMISSIONS_DIR = $(DATA_DIR)/sr15
SR15_EMISSIONS_FILE = $(SR15_EMISSIONS_DIR)/sr15_test_data.csv

define PRINT_HELP_PYSCRIPT
import re, sys

for line in sys.stdin:
	match = re.match(r'^([0-9a-zA-Z_-]+):.*?## (.*)$$', line)
	if match:
		target, help = match.groups()
		print("%-20s %s" % (target, help))
endef
export PRINT_HELP_PYSCRIPT

.PHONY: help
help:
	@python -c "$$PRINT_HELP_PYSCRIPT" < $(MAKEFILE_LIST)

.PHONY: test
test: $(VENV_DIR)  ## run all the tests
	$(VENV_DIR)/bin/pytest tests -r a

.PHONY: checks
checks: $(VENV_DIR)  ## run all the checks
	@echo "=== bandit ==="; $(VENV_DIR)/bin/bandit -c .bandit.yml -r src/climate_assessment || echo "--- bandit failed ---" >&2; \
		echo "\n\n=== black ==="; $(VENV_DIR)/bin/black --check $(FILES_TO_FORMAT_PYTHON) || echo "--- black failed ---" >&2; \
		echo "\n\n=== isort ==="; $(VENV_DIR)/bin/isort --check-only --quiet $(FILES_TO_FORMAT_PYTHON) || echo "--- isort failed ---" >&2; \
		echo "\n\n=== flake8 ==="; $(VENV_DIR)/bin/flake8 $(FILES_TO_FORMAT_PYTHON) || echo "--- flake8 failed ---" >&2; \
		echo

.PHONY: format-notebooks
format-notebooks: $(VENV_DIR)  ## format the notebooks
	@status=$$(git status --porcelain $(NOTEBOOKS_DIR)); \
	if test ${FORCE} || test "x$${status}" = x; then \
		$(VENV_DIR)/bin/black-nb $(NOTEBOOKS_DIR); \
	else \
		echo Not trying any formatting. Working directory is dirty ... >&2; \
	fi;

.PHONY: format
format:  ## re-format files
	make isort
	make black

.PHONY: black
black: $(VENV_DIR)  ## use black to autoformat code
	@status=$$(git status --porcelain); \
	if test ${FORCE} ||test "x$${status}" = x; then \
		$(VENV_DIR)/bin/black --target-version py37 $(FILES_TO_FORMAT_PYTHON); \
	else \
		echo Not trying any formatting, working directory is dirty... >&2; \
	fi;

isort: $(VENV_DIR)  ## format the code
	@status=$$(git status --porcelain src tests); \
	if test ${FORCE} || test "x$${status}" = x; then \
		$(VENV_DIR)/bin/isort $(FILES_TO_FORMAT_PYTHON); \
	else \
		echo Not trying any formatting. Working directory is dirty ... >&2; \
	fi;

.PHONY: docs
docs: $(VENV_DIR)  ## build the docs
	$(VENV_DIR)/bin/sphinx-build -M html doc doc/build

sr15-test-data: $(VENV_DIR) $(DATA_DIR) $(SR15_EMISSIONS_SCRAPER)  ## download test SR1.5 emissions data
	mkdir -p $(SR15_EMISSIONS_DIR)
	$(VENV_DIR)/bin/python $(SR15_EMISSIONS_SCRAPER) $(SR15_EMISSIONS_FILE)

$(DATA_DIR):
	mkdir -p $(DATA_DIR)

virtual-environment: $(VENV_DIR)  ## update venv, create a new venv if it doesn't exist
$(VENV_DIR): setup.py setup.cfg
	[ -d $(VENV_DIR) ] || python3 -m venv $(VENV_DIR)

	$(VENV_DIR)/bin/pip install --upgrade 'pip>=20.3'
	$(VENV_DIR)/bin/pip install wheel
	$(VENV_DIR)/bin/pip install -e .[dev]
	$(VENV_DIR)/bin/jupyter nbextension enable --py widgetsnbextension --sys-prefix

	touch $(VENV_DIR)

first-venv: ## create a new virtual environment for the very first repo setup
	python3 -m venv $(VENV_DIR)

	$(VENV_DIR)/bin/pip install --upgrade pip
	# don't touch here as we don't want this venv to persist anyway


.PHONY: build_and_push_image
build_and_push_image:  ## build and push docker image
	docker build -f Dockerfile.workflow -t $(WORKFLOW_IMAGE) .
	aws ecr get-login-password | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker push $(WORKFLOW_IMAGE)
