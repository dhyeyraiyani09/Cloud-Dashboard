with open('app.py', 'r') as f:
    text = f.read()

marker = '# ─────────────────────────────────────────────────────────────────────────────\n# Section 4 — Task Distribution'

parts = text.split(marker)
print(f"Found {len(parts)} parts.")
if len(parts) == 3:
    # First part is everything before the first Section 4
    # Second part is the content of the first Section 4
    # Third part is the content of the second Section 4 (and the rest of the file)
    # The content should be identical for the Section 4 part.
    # We just need to remove the first duplication.
    # Actually, parts[1] is the content of Section 4 up to the next marker (which is the duplicate marker)
    # Wait, parts[1] might contain Section 3? No, it starts with the marker.
    
    new_text = parts[0] + marker + parts[2]
    with open('app.py', 'w') as f:
        f.write(new_text)
    print("Fixed!")

