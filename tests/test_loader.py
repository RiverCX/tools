"""测试 LogLoader 模块"""

import pytest
from pathlib import Path

from llm_trace_analyzer.loader import LogLoader
from tests.conftest import SAMPLE_LOG, EXPECTED_SESSION_ID


class TestLogLoader:
    """测试日志加载器"""

    def test_load_log_file(self):
        """测试加载日志文件"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        assert len(traces) > 0
        from tests.conftest import EXPECTED_TRACE_COUNT

        assert len(traces) == EXPECTED_TRACE_COUNT

    def test_trace_fields(self):
        """测试 trace 字段提取"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        # 检查第一个 trace 的字段
        first_trace = traces[0]
        assert "timestamp" in first_trace
        assert "event" in first_trace
        assert "session_id" in first_trace
        assert "request_id" in first_trace
        assert "iteration" in first_trace
        assert "model_name" in first_trace
        assert "body_str" in first_trace

    def test_session_id_filter(self):
        """测试 session_id 包含预期值"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        session_ids = set(t["session_id"] for t in traces)
        assert EXPECTED_SESSION_ID in session_ids

        # 检查包含 subagent session
        subagent_sessions = [s for s in session_ids if "_subagent_" in s]
        assert len(subagent_sessions) > 0

    def test_event_types(self):
        """测试事件类型分布"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        event_types = set(t["event"] for t in traces)
        expected_events = {
            "stream_request",
            "stream_output",
            "reasoning_delta",
            "invoke_request",
            "invoke_output",
        }
        # 至少包含部分预期事件
        assert len(event_types & expected_events) > 0

    def test_body_part_parsing(self):
        """测试 body_part 解析"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        # 检查有 body_part 的 trace
        traces_with_parts = [t for t in traces if t["body_part"] is not None]
        assert len(traces_with_parts) > 0

        # body_part 应是 (int, int) 元组
        for t in traces_with_parts[:5]:
            assert isinstance(t["body_part"], tuple)
            assert len(t["body_part"]) == 2
            assert t["body_part"][0] <= t["body_part"][1]

    def test_reasoning_seq_parsing(self):
        """测试 reasoning_seq 解析"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        # 检查有 reasoning_seq 的 trace
        reasoning_traces = [t for t in traces if t["reasoning_seq"] is not None]
        assert len(reasoning_traces) > 0

        # reasoning_seq 应是整数
        for t in reasoning_traces[:5]:
            assert isinstance(t["reasoning_seq"], int)

    def test_file_not_found(self):
        """测试文件不存在异常"""
        loader = LogLoader("/nonexistent/path.log")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_model_name_extraction(self):
        """测试 model_name 提取"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        model_names = set(t["model_name"] for t in traces)
        assert "glm-5" in model_names
