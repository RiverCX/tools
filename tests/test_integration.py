"""集成测试 - 测试完整流程"""

import pytest
import tempfile
from pathlib import Path

from llm_trace_analyzer import LLMTraceAnalyzer
from llm_trace_analyzer.loader import LogLoader
from llm_trace_analyzer.parser import TraceParser
from llm_trace_analyzer.analyzer import ChainAnalyzer
from llm_trace_analyzer.reporter import HTMLReporter
from tests.conftest import (
    SAMPLE_LOG,
    EXPECTED_SESSION_ID,
    EXPECTED_SHORT_ID,
    EXPECTED_MODEL_NAME,
    EXPECTED_CHAIN_REQUESTS,
    EXPECTED_CHAIN_RESPONSES,
    EXPECTED_CHAIN_ITERATIONS,
)


class TestFullPipeline:
    """测试完整分析流程"""

    def test_full_pipeline(self):
        """测试从日志加载到报告生成的完整流程"""
        # 1. 加载日志
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        assert len(traces) > 0

        # 2. 解析 traces
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()
        assert len(requests) > 0
        assert len(responses) > 0

        # 3. 分析链路
        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()
        assert len(result.sessions) > 0

        # 4. 生成报告
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(result, str(output_path))

            assert (output_path / "index.html").exists()
            assert (output_path / f"session_{EXPECTED_SHORT_ID}.html").exists()

    def test_cli_full_run(self):
        """测试 CLI 完整运行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))
            success = analyzer.run(str(output_path), verbose=True)

            assert success
            assert output_path.exists()


class TestExpectedResults:
    """测试预期结果验证"""

    def test_total_iterations(self):
        """验证总迭代数"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        chain = result.sessions.get(EXPECTED_SESSION_ID)
        assert chain.total_iterations == EXPECTED_CHAIN_ITERATIONS
        assert len(chain.requests) == EXPECTED_CHAIN_REQUESTS
        assert len(chain.responses) == EXPECTED_CHAIN_RESPONSES

    def test_session_count(self):
        """验证 session 数量"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        # 主 session + subagents 合并为 1 个 chain
        assert result.statistics.total_sessions == 1

    def test_model_name(self):
        """验证模型名称"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        chain = result.sessions.get(EXPECTED_SESSION_ID)
        assert chain.model_name == EXPECTED_MODEL_NAME

    def test_timing_statistics(self):
        """验证时间统计"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        chain = result.sessions.get(EXPECTED_SESSION_ID)

        # 总时间应合理
        assert chain.total_llm_duration_seconds > 0
        assert chain.total_llm_duration_seconds < 3600  # 不超过 1 小时

        # 平均时间
        avg_llm = chain.total_llm_duration_seconds / len(chain.iteration_timings)
        assert avg_llm > 0
        assert avg_llm < 120  # 平均不超过 2 分钟


class TestReportContent:
    """测试报告内容验证"""

    def test_report_timing_panel(self):
        """验证时间面板"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(result, str(output_path))

            session_file = output_path / f"session_{EXPECTED_SHORT_ID}.html"
            content = session_file.read_text(encoding="utf-8")

            # 应包含时间面板
            assert "timing-panel" in content
            assert "Timing" in content

    def test_report_iteration_blocks(self):
        """验证迭代块"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(result, str(output_path))

            session_file = output_path / f"session_{EXPECTED_SHORT_ID}.html"
            content = session_file.read_text(encoding="utf-8")

            # 应包含多个迭代块
            assert "iteration-block" in content
            # 检查迭代编号
            assert 'data-iteration="1"' in content

    def test_report_subagent_section(self):
        """验证 subagent 区域"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses, _system_metrics = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        chain = result.sessions.get(EXPECTED_SESSION_ID)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"
            reporter = HTMLReporter(str(SAMPLE_LOG))
            reporter.generate(result, str(output_path))

            session_file = output_path / f"session_{EXPECTED_SHORT_ID}.html"
            content = session_file.read_text(encoding="utf-8")

            # 如果有 subagent，应显示
            if chain.subagents:
                assert "agent-block" in content or "subagent" in content


class TestEdgeCases:
    """测试边界情况"""

    def test_empty_log_file(self):
        """测试空日志文件"""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_log = Path(tmpdir) / "empty.log"
            empty_log.write_text("")

            loader = LogLoader(str(empty_log))
            traces = loader.load()
            assert len(traces) == 0

    def test_no_llm_io_trace(self):
        """测试无 LLM_IO_TRACE 的日志"""
        with tempfile.TemporaryDirectory() as tmpdir:
            no_trace_log = Path(tmpdir) / "no_trace.log"
            no_trace_log.write_text("2024-05-01 12:00:00 [INFO] Some other log\n")

            loader = LogLoader(str(no_trace_log))
            traces = loader.load()
            assert len(traces) == 0

    def test_malformed_trace_line(self):
        """测试格式错误的 trace 行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            malformed_log = Path(tmpdir) / "malformed.log"
            malformed_log.write_text("2024-05-01 12:00:00 [DEBUG] [LLM_IO_TRACE] incomplete line\n")

            loader = LogLoader(str(malformed_log))
            traces = loader.load()
            # 应跳过格式错误的行
            assert len(traces) == 0


class TestSessionFilterIntegration:
    """测试 session 过滤集成"""

    def test_filter_main_session_only(self):
        """测试只过滤主 session"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))
            success = analyzer.run(
                str(output_path),
                session_filter=EXPECTED_SESSION_ID,
            )

            assert success

            # 报告应只包含该 session
            index_file = output_path / "index.html"
            content = index_file.read_text(encoding="utf-8")
            assert EXPECTED_SHORT_ID in content
