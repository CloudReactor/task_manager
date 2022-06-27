import re


def generate_clone_name(name):
    p = re.compile(r"(.+) \(Copy (\d+)\)", re.IGNORECASE)
    m = p.match(name)

    if m:
        return f"{m.group(1)} (Copy {int(m.group(2)) + 1})"
    else:
        return f"{name} (Copy 1)"
