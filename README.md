# Mouser Scraper

Automates the sourcing, sorting, and analysis of discrete memory ICs (Flash, PSRAM, MRAM) across various interfaces (SPI, QSPI, xSPI/OSPI, HyperBus) from Mouser Electronics.

This tool bypasses Mouser's ephemeral export tokens by using anti-detection browser automation (`patchright`) to download raw CSVs, then parses and ranks them by 1-unit (MOQ) price to assist in component selection for silicon design.

## Prerequisites
- Python 3.8+
- `make`

## Setup
The setup is fully automated via the Makefile. It creates a local virtual environment, installs dependencies, and downloads the required browser binary.

```bash
make
```
*Note: The first run will download the Chromium browser binary for `patchright`. This may take a few minutes.*

## Usage

### Standard Workflow
Run the full pipeline (Fetch -> Sort -> Report):
```bash
make clean; make
# or
make clean; make all
```

### Individual Targets
- **`make fetch`**: Scrapes Mouser based on `external_memory_devices.txt` and saves raw CSVs to `output/`.
- **`make sort`**: Sorts all CSVs in `output/` by ascending 1-unit price, handling Mouser's Excel-formatted pricing strings (e.g., `="$1.23"`).
- **`make report`**: Prints the top 3 cheapest parts per interface to the console. 
  - *Tip: Change the count via `make report N=5` or `make report N=-1` (for all).*
- **`make debug`**: Opens the browser window visibly. **Use this if Akamai/CAPTCHA blocks the headless run;, causing it to hang.** Solve the CAPTCHA manually in the spawned browser, press Enter in the terminal, and the session will be saved to `mouser_auth.json`.
- **`make clean`**: Removes downloaded CSVs (forces re-fetch on next run).
- **`make distclean`**: Removes the virtual environment, session state, and all output.

## Configuration

### Search Keywords (The Source of Truth)
Edit `external_memory_devices.txt` to change the search criteria. 

The pipeline derives the CSV filename directly from these lines (spaces become underscores), which in turn drives the reporting headers dynamically. No hardcoded dictionaries or mappings are used in the Python scripts.

*Tip: Use Mouser's specific taxonomy (NOR, PSRAM, et cetera) to filter out microcontrollers and dev boards.*
```text
SPI NOR Flash
SPI PSRAM
Quad SPI NOR Flash
QSPI PSRAM
Octal SPI NOR Flash
Octal PSRAM
HyperFlash NOR
HyperRAM
```

### Session Management
Mouser uses Akamai Bot Manager. To avoid constant CAPTCHAs, the script saves your browser cookies and TLS fingerprint to `mouser_auth.json`. 
- If you get blocked or receive 403 errors, delete `mouser_auth.json` and run `make debug` to establish a fresh, human-verified session.

## Architecture
1. **Fetch (`search_mouser_components.py`)**: Uses `patchright` (an anti-detection fork of Playwright) to navigate Mouser, apply "In Stock" filters, and intercept the CSV download network request.
2. **Sort (`sort_mouser.py`)**: Reads the CSVs, strips Mouser's Excel formula wrappers, and sorts rows numerically by the `Pricing` column.
3. **Report (`extract_cheapest.py`)**: Parses the sorted CSVs, dynamically generates headers from the filenames, applies heuristics to build spec strings (falling back to Part Numbers if Mouser's metadata is sparse), and flags known microcontroller prefixes (e.g., `STM32`, `dsPIC`) that slip through search filters.
