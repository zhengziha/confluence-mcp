import logging
from html.parser import HTMLParser
from typing import List

from bs4 import BeautifulSoup

logger = logging.getLogger("confluence-mcp-server")


class ConfluenceToMarkdownParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.markdown = []
        self.indent = 0
        self.in_list = False
        self.list_type = None
        self.in_code_block = False
        self.code_lang = ""

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)

        if tag == "p":
            if self.markdown and self.markdown[-1] != "\n":
                self.markdown.append("\n")
        elif tag == "h1":
            self.markdown.append("\n# ")
        elif tag == "h2":
            self.markdown.append("\n## ")
        elif tag == "h3":
            self.markdown.append("\n### ")
        elif tag == "h4":
            self.markdown.append("\n#### ")
        elif tag == "h5":
            self.markdown.append("\n##### ")
        elif tag == "h6":
            self.markdown.append("\n###### ")
        elif tag == "strong" or tag == "b":
            self.markdown.append("**")
        elif tag == "em" or tag == "i":
            self.markdown.append("*")
        elif tag == "code":
            self.markdown.append("`")
        elif tag == "pre":
            self.in_code_block = True
            self.markdown.append("\n```")
            if "class" in attr_dict:
                for cls in attr_dict["class"].split():
                    if cls.startswith("language-"):
                        self.code_lang = cls[9:]
                        self.markdown.append(self.code_lang)
                        break
            self.markdown.append("\n")
        elif tag == "ul":
            self.in_list = True
            self.list_type = "unordered"
            self.markdown.append("\n")
        elif tag == "ol":
            self.in_list = True
            self.list_type = "ordered"
            self.markdown.append("\n")
            self.ol_counter = 1
        elif tag == "li":
            if self.list_type == "unordered":
                self.markdown.append("\n" + "  " * self.indent + "- ")
            else:
                self.markdown.append("\n" + "  " * self.indent + f"{self.ol_counter}. ")
                self.ol_counter += 1
            self.indent += 1
        elif tag == "a":
            self.current_link = attr_dict.get("href", "")
            self.markdown.append("[")
        elif tag == "br":
            self.markdown.append("\n")
        elif tag == "hr":
            self.markdown.append("\n---\n")

    def handle_endtag(self, tag):
        if tag == "h1" or tag == "h2" or tag == "h3" or tag == "h4" or tag == "h5" or tag == "h6":
            self.markdown.append("\n")
        elif tag == "strong" or tag == "b":
            self.markdown.append("**")
        elif tag == "em" or tag == "i":
            self.markdown.append("*")
        elif tag == "code":
            self.markdown.append("`")
        elif tag == "pre":
            self.in_code_block = False
            self.markdown.append("\n```\n")
        elif tag == "li":
            self.indent -= 1
        elif tag == "ul" or tag == "ol":
            self.in_list = False
            self.list_type = None
            self.markdown.append("\n")
        elif tag == "a":
            self.markdown.append(f"]({self.current_link})")
        elif tag == "p":
            self.markdown.append("\n")

    def handle_data(self, data):
        if not self.in_code_block:
            data = data.strip()
        self.markdown.append(data)

    def get_markdown(self):
        result = "".join(self.markdown)
        result = "\n".join(line for line in result.splitlines() if line.strip() or result.count("\n") < 2)
        return result.strip()


def confluence_to_markdown(html_content: str) -> str:
    """
    将 Confluence Storage Format (HTML) 转换为 Markdown。

    Args:
        html_content: Confluence HTML 内容

    Returns:
        Markdown 格式的内容
    """
    if not html_content:
        return ""

    try:
        soup = BeautifulSoup(html_content, "html.parser")

        for macro in soup.find_all("ac:structured-macro"):
            macro_name = macro.find("ac:name")
            if macro_name:
                name = macro_name.get_text().strip()
                if name == "code":
                    code_body = macro.find("ac:plain-text-body")
                    if code_body:
                        code_text = code_body.get_text().strip()
                        language = ""
                        params = macro.find_all("ac:parameter")
                        for param in params:
                            if param.find("ac:name") and param.find("ac:name").get_text() == "language":
                                if param.find("ac:value"):
                                    language = param.find("ac:value").get_text()
                        code_block = f"```\n{code_text}\n```"
                        if language:
                            code_block = f"```\n{code_text}\n```"
                        macro.replace_with(BeautifulSoup(code_block, "html.parser"))
                elif name == "info" or name == "note" or name == "warning":
                    body = macro.find("ac:plain-text-body") or macro.find("ac:rich-text-body")
                    if body:
                        text = body.get_text().strip()
                        if name == "warning":
                            note_block = f"> ⚠️ **警告**: {text}\n"
                        else:
                            note_block = f"> ℹ️ **提示**: {text}\n"
                        macro.replace_with(BeautifulSoup(note_block, "html.parser"))

        cleaned_html = str(soup)

        parser = ConfluenceToMarkdownParser()
        parser.feed(cleaned_html)
        return parser.get_markdown()

    except Exception as e:
        logger.error(f"Confluence转Markdown失败: {str(e)}")
        return html_content


def markdown_to_confluence(markdown_content: str) -> str:
    """
    将 Markdown 转换为 Confluence Storage Format (HTML)。

    Args:
        markdown_content: Markdown 格式的内容

    Returns:
        Confluence HTML 格式的内容
    """
    if not markdown_content:
        return "<p></p>"

    try:
        lines = markdown_content.split("\n")
        html_lines: List[str] = []
        in_code_block = False
        code_lang = ""
        in_list = False
        list_type = ""

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_code_block:
                    html_lines.append("</pre>")
                    in_code_block = False
                else:
                    code_lang = stripped[3:].strip()
                    html_lines.append(f'<pre class="language-{code_lang}"><code>')
                    in_code_block = True
                continue

            if in_code_block:
                html_lines.append(line)
                continue

            if stripped.startswith("# "):
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("#### "):
                html_lines.append(f"<h4>{stripped[5:]}</h4>")
            elif stripped.startswith("##### "):
                html_lines.append(f"<h5>{stripped[6:]}</h5>")
            elif stripped.startswith("###### "):
                html_lines.append(f"<h6>{stripped[7:]}</h6>")
            elif stripped.startswith("- ") or stripped.startswith("* "):
                if not in_list or list_type != "ul":
                    if in_list:
                        html_lines.append(f"</{list_type}>")
                    html_lines.append("<ul>")
                    in_list = True
                    list_type = "ul"
                html_lines.append(f"<li>{stripped[2:]}</li>")
            elif stripped.startswith(("1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.")):
                if not in_list or list_type != "ol":
                    if in_list:
                        html_lines.append(f"</{list_type}>")
                    html_lines.append("<ol>")
                    in_list = True
                    list_type = "ol"
                html_lines.append(f"<li>{stripped[stripped.index('.') + 2:]}</li>")
            elif stripped.startswith("> "):
                html_lines.append(f"<p><strong>提示:</strong> {stripped[2:]}</p>")
            elif stripped.startswith("---"):
                html_lines.append("<hr/>")
            elif stripped:
                if in_list:
                    html_lines.append(f"</{list_type}>")
                    in_list = False
                html_lines.append(f"<p>{stripped}</p>")

        if in_list:
            html_lines.append(f"</{list_type}>")

        return "\n".join(html_lines)

    except Exception as e:
        logger.error(f"Markdown转Confluence失败: {str(e)}")
        return f"<p>{markdown_content}</p>"