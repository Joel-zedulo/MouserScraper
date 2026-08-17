import csv
import glob
import os
import re

OUTPUT_DIR = "output"

def parse_price(price_str):
    """Extracts the first valid float price from a Mouser CSV pricing string."""
    if not price_str:
        return float('inf')

    # Remove commas to handle thousands separators (e.g., "1,234.56")
    cleaned = price_str.replace(',', '')

    # Find all floating point numbers
    matches = re.findall(r'\d+\.\d+', cleaned)
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            pass

    # Fallback for integers (e.g., "$17")
    matches = re.findall(r'\d+', cleaned)
    if matches:
        try:
            return float(matches[0])
        except ValueError:
            pass

    return float('inf')

def main():
    csv_files = glob.glob(os.path.join(OUTPUT_DIR, "*.csv"))

    if not csv_files:
        print("No CSV files found in output/ directory.")
        return

    for csv_file in csv_files:
        filename = os.path.basename(csv_file)
        print(f"Sorting {filename}...")

        rows = []
        header = None

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                print(f"  -> Warning: {filename} is empty. Skipping.")
                continue

            # Find the index of the 'Pricing' column
            pricing_idx = -1
            for i, col in enumerate(header):
                if 'Pricing' in col or 'Price' in col:
                    pricing_idx = i
                    break

            if pricing_idx == -1:
                print(f"  -> Warning: 'Pricing' column not found in {filename}. Skipping sort.")
                continue

            for row in reader:
                if len(row) > pricing_idx:
                    price_val = parse_price(row[pricing_idx])
                    rows.append((price_val, row))
                else:
                    rows.append((float('inf'), row))

        # Sort by price (low to high)
        rows.sort(key=lambda x: x[0])

        # Write back to the file
        with open(csv_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for _, row in rows:
                writer.writerow(row)

        print(f"  -> Sorted {len(rows)} rows by price.")

if __name__ == "__main__":
    main()
