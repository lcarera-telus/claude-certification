def round_money(value):
    return (
        round(float(value) + 0.0, 2)
        if isinstance(value, (int, float, str)) and str(value).strip() != ""
        else round(0.0, 2)
    )


def slugify(text):
    s = str(text).strip().lower()
    out = "".join(
        [
            c if c.isalnum() else "-"
            for c in s
            if c.isalnum() or c == " " or c == "_" or c == "-" or c == "."
        ]
    )
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-")
