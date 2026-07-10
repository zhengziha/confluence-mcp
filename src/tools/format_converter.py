import logging
import re
from html.parser import HTMLParser
from typing import List

from bs4 import BeautifulSoup

logger = logging.getLogger("confluence-mcp-server")


def _escape(text: str) -> str:
    """HTML 转义：Confluence storage 是严格 XHTML，裸 & < > 会被服务端判为非法实体返回 400。"""
    if not text:
        return ""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """处理行内 markdown 格式：`code`、**bold**、*italic*。
    先转义再还原行内 code 的内容，保证 code 内的 * 等不被误解析。
    """
    if not text:
        return ""
    escaped = _escape(text)
    # 用占位符保护行内 code（code 内的 * _ 等不解析）
    placeholders: List[str] = []

    def stash_code(m):
        placeholders.append(m.group(1))
        return f"\x00{len(placeholders) - 1}\x00"

    escaped = re.sub(r"`([^`]+)`", stash_code, escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", escaped)
    # 还原 code 占位符
    escaped = re.sub(r"\x00(\d+)\x00", lambda m: f"<code>{placeholders[int(m.group(1))]}</code>", escaped)
    return escaped


def _is_table_row(stripped: str) -> bool:
    return stripped.startswith("|") and stripped.endswith("|")


def _is_table_separator(stripped: str) -> bool:
    # 形如 | --- | --- | 的分隔行
    inner = stripped.strip("|")
    parts = [p.strip() for p in inner.split("|")]
    return bool(parts) and all(set(p) <= set("-: ") and "-" in p for p in parts)


def _split_row(stripped: str) -> List[str]:
    return [c.strip() for c in stripped.strip("|").split("|")]


# 有序列表项：1. / 10. 等数字紧跟点+空格
_OL_RE = re.compile(r"^([0-9]{1,9})\.\s+")


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
        in_table = False
        in_quote = False

        def close_list():
            nonlocal in_list
            if in_list:
                html_lines.append(f"</{list_type}>")
                in_list = False

        def close_table():
            nonlocal in_table
            if in_table:
                html_lines.append("</tbody></table>")
                in_table = False

        def close_quote():
            nonlocal in_quote
            if in_quote:
                html_lines.append("</blockquote>")
                in_quote = False

        for line in lines:
            stripped = line.strip()

            if stripped.startswith("```"):
                close_list()
                close_table()
                close_quote()
                if in_code_block:
                    # 结束代码块：闭合 code 宏的 CDATA 与 structured-macro
                    html_lines.append("]]></ac:plain-text-body></ac:structured-macro>")
                    in_code_block = False
                else:
                    code_lang = stripped[3:].strip()
                    # Confluence storage 格式不支持裸 <pre>/<code>，必须用 code 宏，
                    # 否则服务端校验 storage XML 会直接返回 400。
                    if code_lang:
                        html_lines.append(
                            f'<ac:structured-macro ac:name="code">'
                            f'<ac:parameter ac:name="language">{_escape(code_lang)}</ac:parameter>'
                            f'<ac:plain-text-body><![CDATA['
                        )
                    else:
                        html_lines.append(
                            '<ac:structured-macro ac:name="code">'
                            "<ac:plain-text-body><![CDATA["
                        )
                    in_code_block = True
                continue

            if in_code_block:
                # 代码块内容原样保留，不做任何 markdown 转义
                html_lines.append(line)
                continue

            # 表格行处理（| a | b |）
            if _is_table_row(stripped):
                if _is_table_separator(stripped):
                    # 分隔行：跳过，表头已在上一行输出
                    continue
                cells = _split_row(stripped)
                if not in_table:
                    close_list()
                    close_quote()
                    html_lines.append("<table><thead><tr>")
                    html_lines.append("".join(f"<th>{_inline(c)}</th>" for c in cells))
                    html_lines.append("</tr></thead><tbody>")
                    in_table = True
                else:
                    html_lines.append("<tr>")
                    html_lines.append("".join(f"<td>{_inline(c)}</td>" for c in cells))
                    html_lines.append("</tr>")
                continue
            close_table()

            # 引用块（连续 > 合并为一个 blockquote）
            if stripped.startswith("> "):
                if not in_quote:
                    close_list()
                    html_lines.append("<blockquote>")
                    in_quote = True
                html_lines.append(f"<p>{_inline(stripped[2:])}</p>")
                continue
            close_quote()

            # 标题（按 # 数量优先匹配，避免 ## 被 # 误命中）
            heading = None
            for level in (6, 5, 4, 3, 2, 1):
                prefix = "#" * level + " "
                if stripped.startswith(prefix):
                    heading = (level, stripped[len(prefix):])
                    break
            if heading:
                close_list()
                level, text = heading
                html_lines.append(f"<h{level}>{_inline(text)}</h{level}>")
                continue

            # 无序列表项
            if stripped.startswith("- ") or stripped.startswith("* "):
                close_quote()
                if not in_list or list_type != "ul":
                    close_list()
                    html_lines.append("<ul>")
                    in_list = True
                    list_type = "ul"
                html_lines.append(f"<li>{_inline(stripped[2:])}</li>")
                continue

            # 有序列表项（1. 2. ... 10. 等）
            ol_match = _OL_RE.match(stripped)
            if ol_match:
                close_quote()
                if not in_list or list_type != "ol":
                    close_list()
                    html_lines.append("<ol>")
                    in_list = True
                    list_type = "ol"
                content = stripped[ol_match.end():]
                html_lines.append(f"<li>{_inline(content)}</li>")
                continue

            # 分隔线
            if stripped.startswith("---"):
                close_list()
                close_quote()
                html_lines.append("<hr/>")
                continue

            # 普通段落
            if stripped:
                close_list()
                close_quote()
                html_lines.append(f"<p>{_inline(stripped)}</p>")

        close_list()
        close_table()
        close_quote()

        # 代码块未闭合（markdown 末尾漏写 ```）时补上闭合，避免 storage XML 不完整被 400
        if in_code_block:
            html_lines.append("]]></ac:plain-text-body></ac:structured-macro>")

        return "\n".join(html_lines)

    except Exception as e:
        logger.error(f"Markdown转Confluence失败: {str(e)}")
        return f"<p>{markdown_content}</p>"