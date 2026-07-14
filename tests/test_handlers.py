"""Mermaid / Draw.io handler 单元测试。"""
from src.tools.converters.drawio_handler import DrawioHandler
from src.tools.converters.mermaid_handler import MermaidHandler


class TestMermaidHandler:
    def test_extract_and_roundtrip_markdown(self):
        md = "前置\n\n```mermaid\ngraph TD\n  A-->B\n```\n\n后置"
        blocks = MermaidHandler.extract_mermaid_blocks(md)
        assert len(blocks) == 1
        assert "A-->B" in blocks[0][1]

        converted = MermaidHandler.markdown_to_confluence(md)
        assert 'ac:name="mermaid-macro"' in converted
        assert "A-->B" in converted

    def test_extract_confluence_mermaid(self):
        storage = (
            '<ac:structured-macro ac:name="mermaid-macro">'
            "<ac:plain-text-body><![CDATA[sequenceDiagram\nA->>B: hi]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )
        blocks = MermaidHandler.extract_confluence_mermaid(storage)
        assert len(blocks) == 1
        assert "sequenceDiagram" in blocks[0][1]

        md = MermaidHandler.confluence_to_markdown(storage)
        assert "```mermaid" in md
        assert "A->>B: hi" in md

    def test_compat_mermaid_without_macro_suffix(self):
        storage = (
            '<ac:structured-macro ac:name="mermaid">'
            "<ac:plain-text-body><![CDATA[graph LR\nX-->Y]]></ac:plain-text-body>"
            "</ac:structured-macro>"
        )
        blocks = MermaidHandler.extract_confluence_mermaid(storage)
        assert len(blocks) == 1


class TestDrawioHandler:
    def test_extract_confluence_drawio(self):
        storage = (
            '<ac:structured-macro ac:name="drawio" ac:schema-version="1">'
            '<ac:parameter ac:name="diagramName">a.drawio</ac:parameter>'
            '<ac:parameter ac:name="attachment">a.drawio</ac:parameter>'
            "</ac:structured-macro>"
        )
        blocks = DrawioHandler.extract_confluence_drawio(storage)
        assert len(blocks) == 1
        assert blocks[0][1]["diagramName"] == "a.drawio"

    def test_markdown_markers(self):
        md = (
            "> 📊 **Draw.io 图表**: arch.drawio\n"
            "> [draw.io 在线编辑器](https://app.diagrams.net/)"
        )
        blocks = DrawioHandler.extract_markdown_drawio(md)
        assert len(blocks) == 1
        assert blocks[0][1] == "arch.drawio"

        macro = DrawioHandler.markdown_to_drawio_macro("arch.drawio")
        assert 'ac:name="drawio"' in macro
        assert "arch.drawio" in macro

    def test_extract_drawio_codeblocks_and_filename(self):
        md = "```drawio\n<mxfile>ok</mxfile>\n```"
        blocks = DrawioHandler.extract_drawio_codeblocks(md)
        assert len(blocks) == 1
        assert "<mxfile>ok</mxfile>" in blocks[0][1]
        assert DrawioHandler.generate_attachment_filename(2) == "drawio_diagram_2.drawio"

    def test_drawio_to_markdown(self):
        text = DrawioHandler.drawio_to_markdown("x.drawio")
        assert "x.drawio" in text
        assert "app.diagrams.net" in text
