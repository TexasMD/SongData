import re

with open("scripts/scrape_metadata.py", "r") as f:
    content = f.read()

replacement = """    # Write to CSV
    os.makedirs(os.path.dirname(os.path.abspath(output_csv)), exist_ok=True)
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"Successfully scraped {len(results)} files to {output_csv}")
    except OSError as e:
        print(f"Error: Could not write to output file '{output_csv}'.")
        print(f"Details: {e}")
        print("Please ensure you have write permissions and the file is not open in another program.")
        import sys
        sys.exit(1)"""

pattern = r"    # Write to CSV\n    os\.makedirs\(os\.path\.dirname\(os\.path\.abspath\(output_csv\)\), exist_ok=True\)\n    with open\(output_csv, 'w', newline='', encoding='utf-8'\) as f:\n        writer = csv\.DictWriter\(f, fieldnames=fieldnames\)\n        writer\.writeheader\(\)\n        for row in results:\n            writer\.writerow\(row\)\n            \n    print\(f\"Successfully scraped \{len\(results\)\} files to \{output_csv\}\"\)"

new_content = re.sub(pattern, replacement, content)

with open("scripts/scrape_metadata.py", "w") as f:
    f.write(new_content)
