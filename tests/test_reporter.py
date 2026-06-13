"""测试 HTMLReporter 模块"""

import pytest
import tempfile
from pathlib import Path

from llm_trace_analyzer.loader import LogLoader
from llm_trace_analyzer.parser import TraceParser
from llm_trace_analyzer.analyzer import ChainAnalyzer
from llm_trace_analyzer.reporter import HTMLReporter
from tests.conftest import (
    SAMPLE_LOG,
    EXPECTED_SESSION_ID,
    EXPECTED_SHORT_ID,
    EXPECTED_MODEL_NAME,
)


class TestHTMLReporter:
    """测试 HTML 报告生成器"""

    @pytest.fixture
    def report_data(self):
        """准备报告数据"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        return result

    def test_generate_report(self, report_data):
        """测试报告生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(report_data, str(output_path))

            # 检查生成的文件
            assert output_path.exists()
            assert (output_path / "index.html").exists()
            assert (output_path / f"session_{EXPECTED_SHORT_ID}.html").exists()

    def test_index_html_content(self, report_data):
        """测试 index.html 内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(report_data, str(output_path))

            index_file = output_path / "index.html"
            content = index_file.read_text(encoding="utf-8")

            # 检查基本 HTML 结构
            assert "<!DOCTYPE html>" in content
            assert "<title>LLM Trace Index</title>" in content
            assert EXPECTED_SHORT_ID in content

    def test_session_html_content(self, report_data):
        """测试 session 详情页内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(report_data, str(output_path))

            session_file = output_path / f"session_{EXPECTED_SHORT_ID}.html"
            content = session_file.read_text(encoding="utf-8")

            # 检查基本内容
            assert "<!DOCTYPE html>" in content
            assert EXPECTED_MODEL_NAME in content
            assert "Timing Overview" in content or "timing-panel" in content

    def test_short_session_id(self):
        """测试 session_id 缩短"""
        reporter = HTMLReporter(str(SAMPLE_LOG))

        short = reporter._short_session_id(EXPECTED_SESSION_ID)
        assert short == EXPECTED_SHORT_ID

    def test_format_timestamp(self):
        """测试时间戳格式化"""
        reporter = HTMLReporter(str(SAMPLE_LOG))

        # 正常时间戳
        ts = reporter._format_timestamp(1714527300)  # 2024-05-01 12:21:40
        assert ":" in ts  # 应包含时间分隔符

        # 零时间戳
        ts_zero = reporter._format_timestamp(0)
        assert ts_zero == "N/A"

    def test_format_duration(self):
        """测试时长格式化"""
        reporter = HTMLReporter(str(SAMPLE_LOG))

        # 毫秒级
        ms = reporter._format_duration(0.5)
        assert "ms" in ms

        # 秒级
        s = reporter._format_duration(15.5)
        assert "s" in s

        # 分钟级
        m = reporter._format_duration(120)
        assert "m" in m

        # 零值
        zero = reporter._format_duration(0)
        assert zero == "N/A"

    def test_timing_list_html(self, report_data):
        """测试时间列表 HTML 生成"""
        chain = report_data.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            reporter = HTMLReporter(str(SAMPLE_LOG))
            timing_html = reporter._generate_timing_list_html(chain)

            # 应包含时间列表结构
            assert "timing-panel" in timing_html or "timing-item" in timing_html

    def test_iterations_html(self, report_data):
        """测试迭代详情 HTML 生成"""
        chain = report_data.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            reporter = HTMLReporter(str(SAMPLE_LOG))
            iterations_html = reporter._generate_iterations_html(chain)

            # 应包含迭代块
            assert "iteration-block" in iterations_html

    def test_subagents_tree_html(self, report_data):
        """测试 subagent 树 HTML 生成"""
        chain = report_data.sessions.get(EXPECTED_SESSION_ID)
        if chain and chain.subagents:
            reporter = HTMLReporter(str(SAMPLE_LOG))
            tree_html = reporter._generate_subagents_tree_html(chain)

            # 应包含 subagent 节点
            assert "subagent-node" in tree_html or "Subagents" in tree_html


class TestHTMLReporterTemplates:
    """测试模板渲染"""

    def test_request_template(self, report_data):
        """测试请求模板"""
        chain = report_data.sessions.get(EXPECTED_SESSION_ID)
        if chain and chain.requests:
            reporter = HTMLReporter(str(SAMPLE_LOG))
            req = chain.requests[0]

            html = reporter._generate_request_html(req, None, {})
            assert "REQUEST" in html
            assert "Messages" in html or "message" in html.lower()

    def test_response_template(self, report_data):
        """测试响应模板"""
        chain = report_data.sessions.get(EXPECTED_SESSION_ID)
        if chain and chain.responses:
            reporter = HTMLReporter(str(SAMPLE_LOG))
            resp = chain.responses[0]

            html = reporter._generate_response_html(resp)
            assert "RESPONSE" in html

    def test_tool_calls_html(self, report_data):
        """测试工具调用 HTML"""
        chain = report_data.sessions.get(EXPECTED_SESSION_ID)
        # 找有 tool_calls 的响应
        responses_with_tools = [r for r in chain.responses if r.tool_calls]
        if responses_with_tools:
            reporter = HTMLReporter(str(SAMPLE_LOG))
            resp = responses_with_tools[0]

            html = reporter._generate_response_html(resp)
            assert "Tool Calls" in html or "tool_calls" in html


class TestHTMLReporterCopyFunctions:
    """测试复制功能"""

    def test_copy_button_present(self, report_data):
        """测试复制按钮存在"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(report_data, str(output_path))

            session_file = output_path / f"session_{EXPECTED_SHORT_ID}.html"
            content = session_file.read_text(encoding="utf-8")

            # 应包含复制按钮脚本
            assert "copyToClipboard" in content or "copy-btn" in content
