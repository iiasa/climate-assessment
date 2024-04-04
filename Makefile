.DEFAULT_GOAL := help

DATA_DIR ?= ./data
SCRIPTS_DIR ?= ./scripts

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
test:  ## run all the tests
	poetry run pytest src tests -r a -v --doctest-modules --cov=src

.PHONY: checks
checks:  ## run all the linting checks of the codebase
	@echo "=== pre-commit ==="; poetry run pre-commit run --all-files || echo "--- pre-commit failed ---" >&2; \
		echo "======"

.PHONY: docs
docs:  ## build the docs
	poetry run sphinx-build -T -b html docs/source docs/build/html

sr15-test-data: $(DATA_DIR) $(SR15_EMISSIONS_SCRAPER)  ## download test SR1.5 emissions data
	mkdir -p $(SR15_EMISSIONS_DIR)
	poetry run python $(SR15_EMISSIONS_SCRAPER) $(SR15_EMISSIONS_FILE)

$(DATA_DIR):
	mkdir -p $(DATA_DIR)

.PHONY: virtual-environment
virtual-environment:  ## update virtual environment, create a new one if it doesn't already exist
	poetry lock --no-update
	# Put virtual environments in the project
	poetry config virtualenvs.in-project true
	poetry install --all-extras
	poetry run pre-commit install
	# Also export a requirements.txt file
	poetry export -f requirements.txt --output requirements.txt


.PHONY: build_and_push_image
build_and_push_image:  ## build and push docker image
	docker build -f Dockerfile.workflow -t $(WORKFLOW_IMAGE) .
	aws ecr get-login-password | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker push $(WORKFLOW_IMAGE)
