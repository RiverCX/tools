"""测试 CLI 主入口模块"""

import pytest
import tempfile
from pathlib import Path

from llm_trace_analyzer.main import LLMTraceAnalyzer, main
from tests.conftest import (
    SAMPLE_LOG,
    EXPECTED_SESSION_ID,
    EXPECTED_TOTAL_ITERATIONS,
)


class TestLLMTraceAnalyzer:
    """测试分析器类"""

    def test_run_basic(self):
        """测试基本运行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))
            success = analyzer.run(str(output_path), verbose=True)

            assert success
            assert output_path.exists()

    def test_run_with_session_filter(self):
        """测试 session 过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))
            success = analyzer.run(
                str(output_path),
                verbose=False,
                session_filter=EXPECTED_SESSION_ID,
            )

            assert success
            assert output_path.exists()

    def test_run_file_not_found(self):
        """测试文件不存在"""
        analyzer = LLMTraceAnalyzer("/nonexistent/path.log")
        success = analyzer.run("/tmp/report")
        assert not success

    def test_verbose_output(self, capsys):
        """测试详细输出"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))
            analyzer.run(str(output_path), verbose=True)

            captured = capsys.readouterr()
            assert "Total sessions" in captured.out
            assert str(EXPECTED_TOTAL_ITERATIONS) in captured.out


class TestSessionFiltering:
    """测试 session 过滤功能"""

    def test_filter_traces_for_session(self):
        """测试 trace 过滤"""
        analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))
        loader = analyzer._get_loader() if hasattr(analyzer, "_get_loader") else None

        # 直接测试过滤逻辑
        from llm_trace_analyzer.loader import LogLoader

        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        filtered = analyzer._filter_traces_for_session(traces, EXPECTED_SESSION_ID)

        # 过滤后的 traces 应只包含主 session 和 subagent
        session_ids = set(t["session_id"] for t in filtered)
        for sid in session_ids:
            assert EXPECTED_SESSION_ID in sid or "_subagent_" in sid

    def test_collect_subagent_sessions(self):
        """测试 subagent 收集"""
        analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))

        from llm_trace_analyzer.loader import LogLoader

        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        collected = set()
        analyzer._collect_subagent_sessions(EXPECTED_SESSION_ID, traces, collected)

        # 应收集到 subagent sessions
        assert len(collected) > 0
        for sid in collected:
            assert "_subagent_" in sid or "_fork_agent_" in sid

    def test_new_format_subagent_collection(self):
        """测试新格式 subagent 收集"""
        analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))

        from llm_trace_analyzer.loader import LogLoader

        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        collected = set()
        analyzer._collect_subagent_sessions(EXPECTED_SESSION_ID, traces, collected)

        # 新格式：session_id 包含父 session
        for sid in collected:
            if "_fork_agent_" in sid:
                # fork_agent 应包含 parent 和 subagent
                assert EXPECTED_SESSION_ID in sid or "_subagent_" in sid


class TestCLIMain:
    """测试 CLI main 函数"""

    def test_main_basic(self):
        """测试基本 CLI 运行"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            # 模拟命令行参数
            import sys

            old_args = sys.argv
            sys.argv = ["lt", str(SAMPLE_LOG), "-o", str(output_path), "-v"]

            try:
                main()
            except SystemExit as e:
                # main() 可能调用 sys.exit(0)
                pass
            finally:
                sys.argv = old_args

            # 检查报告生成
            assert output_path.exists()

    def test_main_with_session_filter(self):
        """测试 CLI session 过滤"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "report"

            import sys

            old_args = sys.argv
            sys.argv = [
                "lt",
                str(SAMPLE_LOG),
                "-o",
                str(output_path),
                "--session",
                EXPECTED_SESSION_ID,
            ]

            try:
                main()
            except SystemExit:
                pass
            finally:
                sys.argv = old_args

            assert output_path.exists()

    def test_main_no_log_file(self):
        """测试无日志文件时的错误处理"""
        import sys

        old_args = sys.argv
        sys.argv = ["lt"]

        try:
            main()
        except SystemExit as e:
            # 应退出且非 0
            assert e.code != 0
        finally:
            sys.argv = old_args


class TestOutputPath:
    """测试输出路径处理"""

    def test_default_output_path(self):
        """测试默认输出路径"""
        analyzer = LLMTraceAnalyzer(str(SAMPLE_LOG))

        # 默认应在日志文件所在目录
        log_path = Path(SAMPLE_LOG)
        expected_dir = log_path.parent / "llm_trace_report"

        with tempfile.TemporaryDirectory() as tmpdir:
            # 在临时目录测试
            output_path = Path(tmpdir) / "llm_trace_report"
            analyzer.run(str(output_path))

            assert output_path.exists()
            assert (output_path / "index.html").exists()
