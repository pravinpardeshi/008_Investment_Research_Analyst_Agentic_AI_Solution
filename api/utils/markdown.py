import re


def md_to_html(text: str) -> str:
    if not text:
        return ""
    html = _escape(text)
    html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
    html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
    html = re.sub(r"^# (.+)$", r"<h1>\1</h1>", html, flags=re.MULTILINE)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"\*(.+?)\*", r"<em>\1</em>", html)
    html = re.sub(r"`(.+?)`", r"<code>\1</code>", html)
    lines = html.split("\n")
    result: list[str] = []
    in_list = False
    in_para = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if not in_list:
                if in_para:
                    result.append("</p>")
                    in_para = False
                result.append("<ul>")
                in_list = True
            result.append(f"<li>{stripped[2:]}</li>")
        else:
            if in_list:
                result.append("</ul>")
                in_list = False
            if stripped == "":
                if in_para:
                    result.append("</p>")
                    in_para = False
            elif stripped.startswith("<h") or stripped.startswith("<ul") or stripped.startswith("</ul"):
                if in_para:
                    result.append("</p>")
                    in_para = False
                result.append(stripped)
            else:
                if not in_para:
                    result.append("<p>")
                    in_para = True
                else:
                    result.append("<br>")
                result.append(stripped)
    if in_list:
        result.append("</ul>")
    if in_para:
        result.append("</p>")
    return "".join(result)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
