.PHONY: all fetch debug sort report clean distclean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
SYS_PYTHON ?= python3
N ?= 3  # Default number of items to show in the report

LIST_OF_COMPONENTS := external_memory_devices.txt

all: fetch sort report

$(PYTHON):
	@echo "=== Creating Virtual Environment ==="
	$(SYS_PYTHON) -m venv $(VENV)
	@echo "=== Installing Dependencies ==="
	$(PIP) install --upgrade pip
	$(PIP) install patchright
	@echo "=== Installing Patchright Chromium Browser ==="
	$(PYTHON) -m patchright install chromium

fetch: $(PYTHON)
	@echo "=== Sourcing parts (Silent Background) ==="
	@$(PYTHON) search_mouser_components.py

debug: $(PYTHON)
	@echo "=== Sourcing parts (Visible Debug) ==="
	@$(PYTHON) search_mouser_components.py --debug

sort: $(PYTHON)
	@echo "=== Sorting CSVs by Price ==="
	@$(PYTHON) sort_mouser.py

report: $(PYTHON)
	@echo "=== Top $(N) Cheapest Parts ==="
	@$(PYTHON) extract_cheapest.py -n $(N)

clean:
	@echo "=== Cleaning output folder ==="
	@rm -rf output/
	@rm -f *.html *.png

distclean: clean
	@echo "=== Removing Virtual Environment & Auth State ==="
	@rm -rf $(VENV) mouser_auth.json
