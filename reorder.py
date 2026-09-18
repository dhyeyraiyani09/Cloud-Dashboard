import re

with open('app.py', 'r') as f:
    lines = f.readlines()

def get_section(start_marker, end_marker):
    start_idx = -1
    end_idx = -1
    for i, line in enumerate(lines):
        if start_marker in line:
            start_idx = i
        if end_marker and end_marker in line:
            end_idx = i
    if end_marker is None:
        return lines[start_idx:]
    return lines[start_idx:end_idx]

s1_to_1b = get_section("# Section 1 — Cloud Resources", "# Section 2")
s2 = get_section("# Section 2 — Performance Metrics", "# Section 3")
s3 = get_section("# Section 3 — VM Status", "# Section 4")
s4 = get_section("# Section 4 — Task Distribution", "# Section 5")
s5 = get_section("# Section 5 — Scaling & Failover", "# Section 6")
s6 = get_section("# Section 6 — Algorithm Comparison", "# Section 7")
s7 = get_section("# Section 7 — Workload & Scalability", "# Section 8")
s8 = get_section("# Section 8 — VM Failure & Failover", "# About / Project Information")
about_footer = get_section("# About / Project Information", None)
header_etc = lines[:lines.index(s1_to_1b[0])]

new_lines = (
    header_etc +
    s1_to_1b +
    s3 +
    s4 +
    s2 +
    s6 +
    s5 +
    s8 +
    s7 +
    about_footer
)

with open('app.py', 'w') as f:
    f.writelines(new_lines)
