#!/usr/bin/env python3
import csv
import glob
import os
import re
import argparse


def get_price(row):
    price_str = row.get("Pricing", "")
    match = re.search(r"\$?([\d\.]+)", price_str)
    return float(match.group(1)) if match else float('inf')


def is_mcu(part_num):
    """Check if the part is an MCU rather than a discrete memory IC."""
    mcu_keywords = ["pic", "dspic", "stm32", "mkl", "samd", "rp2", "attiny", "atmega", "avr"]
    return any(kw in part_num.lower() for kw in mcu_keywords)


def get_interface_target(rows, filename):
    return os.path.splitext(filename)[0].title().replace('_', ' ')


def build_spec(row):
    """Ensures the Density/Spec description is NEVER empty by using fallback fields."""
    memory_size = row.get("Memory Size", "").strip()
    interface_type = row.get("Interface Type", "").strip()
    clock = row.get("Maximum Clock Frequency", "").strip()

    # Primary spec fields
    spec_parts = [p for p in [memory_size, interface_type, clock] if p]
    if spec_parts:
        return " | ".join(spec_parts)

    # Fallback fields if primary ones are empty
    fallback_fields = [
        "Organization",
        "Data Bus Width",
        "Supply Voltage - Min",
        "Series",
        "Mounting Style",
        "Timing Type"
    ]

    fallback_parts = []
    for field in fallback_fields:
        val = row.get(field, "").strip()
        if val:
            fallback_parts.append(val)

    if fallback_parts:
        return " | ".join(fallback_parts)

    # Ultimate fallback: Use the Part Number so it's never truly blank
    return row.get("Mfr Part Number", "Unknown Spec")


def main():
    parser = argparse.ArgumentParser(description="Extract cheapest memory ICs from Mouser CSVs.")
    parser.add_argument("-n", "--top", type=int, default=3, help="Number of top parts to show per interface (default: 3). Use -1 for all.")
    args = parser.parse_args()

    csv_files = sorted(glob.glob("output/*.csv"))
    if not csv_files:
        print("No CSV files found in output/")
        return

    for filepath in csv_files:
        with open(filepath, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

            if not rows:
                continue

            rows.sort(key=get_price)

            limit = len(rows) if args.top == -1 else min(args.top, len(rows))

            label = get_interface_target(rows, os.path.basename(filepath))
            print(f"\n--- {label} ---")

            for i, row in enumerate(rows[:limit]):
                mfr = row.get("Mfr.", "").strip() or "Unknown Mfr"
                part = row.get("Mfr Part Number", "").strip() or row.get("Mouser Part Number", "Unknown Part")
                url = row.get("Product Detail", "").strip()

                price_str = row.get("Pricing", "")
                match = re.search(r"\$?([\d\.]+)", price_str)
                price = f"${match.group(1)}" if match else "N/A"

                pkg = row.get("Package / Case", "").strip() or row.get("Mounting Style", "").strip() or "N/A"
                spec = build_spec(row)

                mcu_flag = " ⚠️ MCU?" if is_mcu(part) else ""

                if is_mcu(part): continue # Skip MCU

                print(f"  {i+1}. {mfr} {part}{mcu_flag}")
                print(f"     Density/Spec: {spec}")
                print(f"     Package: {pkg}")
                print(f"     Price: {price}")
                print(f"     URL: {url}")
                print()

if __name__ == "__main__":
    main()
