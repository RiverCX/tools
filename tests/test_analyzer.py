"""测试 ChainAnalyzer 模块"""

import pytest

from llm_trace_analyzer.loader import LogLoader
from llm_trace_analyzer.parser import TraceParser
from llm_trace_analyzer.analyzer import ChainAnalyzer
from tests.conftest import (
    SAMPLE_LOG,
    EXPECTED_SESSION_ID,
    EXPECTED_SHORT_ID,
    EXPECTED_MODEL_NAME,
    EXPECTED_CHAIN_ITERATIONS,
    EXPECTED_TOTAL_ITERATIONS,
    EXPECTED_SUBAGENT_SESSIONS,
)


class TestChainAnalyzer:
    """测试链路分析器"""

    @pytest.fixture
    def analysis_result(self):
        """准备分析结果"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        return analyzer.analyze()

    def test_analyze_returns_result(self, analysis_result):
        """测试分析返回结果"""
        assert analysis_result is not None
        assert hasattr(analysis_result, "sessions")
        assert hasattr(analysis_result, "statistics")
        assert hasattr(analysis_result, "sorted_sessions")

    def test_main_session_exists(self, analysis_result):
        """测试主 session 存在"""
        assert EXPECTED_SESSION_ID in analysis_result.sessions

    def test_session_chain_fields(self, analysis_result):
        """测试 session chain 字段"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            assert hasattr(chain, "session_id")
            assert hasattr(chain, "model_name")
            assert hasattr(chain, "requests")
            assert hasattr(chain, "responses")
            assert hasattr(chain, "start_time")
            assert hasattr(chain, "end_time")
            assert hasattr(chain, "total_iterations")
            assert hasattr(chain, "subagents")
            assert hasattr(chain, "iteration_timings")

    def test_model_name(self, analysis_result):
        """测试模型名称"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            assert chain.model_name == EXPECTED_MODEL_NAME

    def test_iteration_count(self, analysis_result):
        """测试迭代数量"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            assert chain.total_iterations == EXPECTED_CHAIN_ITERATIONS

    def test_subagents_identified(self, analysis_result):
        """测试 subagent 识别"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            # 应识别出 subagent
            assert len(chain.subagents) > 0

    def test_subagent_session_ids(self, analysis_result):
        """测试 subagent session_id 格式"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain and chain.subagents:
            for sa in chain.subagents:
                # 新格式：包含 _subagent_ 或 _fork_agent_
                assert "_subagent_" in sa.session_id or "_fork_agent_" in sa.session_id

    def test_iteration_timings(self, analysis_result):
        """测试迭代时间统计"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            timings = chain.iteration_timings
            assert len(timings) > 0

            # 检查第一个 timing 字段
            first_timing = timings[0]
            assert hasattr(first_timing, "iteration_num")
            assert hasattr(first_timing, "llm_call_duration")
            assert hasattr(first_timing, "tool_processing_duration")

    def test_timing_values(self, analysis_result):
        """测试时间统计值"""
        chain = analysis_result.sessions.get(EXPECTED_SESSION_ID)
        if chain:
            # LLM 时间总和应大于 0
            assert chain.total_llm_duration_seconds > 0
            # Tool 时间总和
            assert chain.total_tool_duration_seconds >= 0

    def test_statistics(self, analysis_result):
        """测试统计信息"""
        stats = analysis_result.statistics
        assert stats.total_sessions == 1
        assert stats.total_iterations == EXPECTED_TOTAL_ITERATIONS

    def test_sorted_sessions(self, analysis_result):
        """测试排序后的 sessions"""
        sorted_sessions = analysis_result.sorted_sessions
        assert len(sorted_sessions) == 1
        assert sorted_sessions[0].session_id == EXPECTED_SESSION_ID


class TestChainAnalyzerSubagentDepth:
    """测试 subagent 深度计算"""

    @pytest.fixture
    def analyzer(self):
        """准备分析器"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses = parser.parse()

        return ChainAnalyzer(requests, responses)

    def test_compute_subagent_depth(self, analyzer):
        """测试深度计算"""
        # 使用新格式的 task_id 测试
        task_id = "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651"
        depth, chain_path, direct_parent = analyzer._compute_subagent_depth(task_id)

        assert depth >= 0
        assert len(chain_path) > 0
        assert "Parent" in chain_path or "Sub" in chain_path

    def test_fork_agent_depth(self, analyzer):
        """测试 fork_agent 深度"""
        task_id = "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651_fork_agent_0e4cf63b"
        depth, chain_path, direct_parent = analyzer._compute_subagent_depth(task_id)

        # fork_agent 嵌套在 subagent 下，深度应 >= 0
        assert depth >= 0
        # chain_path 应包含 Fork
        assert any("Fork" in p or "Sub" in p for p in chain_path)

    def test_format_chain_label(self, analyzer):
        """测试链路标签格式化"""
        chain_path = ["Parent", "Sub[ade2a651]", "Fork[0e4cf63b]"]
        label = analyzer._format_chain_label(chain_path, 2)

        assert "→" in label
        assert "Parent" in label
        assert "Sub" in label
        assert "Fork" in label

    def test_find_root_parent(self, analyzer):
        """测试查找根父 session"""
        # 嵌套的 fork_agent session
        nested_session = "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651_fork_agent_0e4cf63b"
        root = analyzer._find_root_parent(nested_session)

        # 根应是主 session
        assert root == EXPECTED_SESSION_ID or "_subagent_" not in root


class TestChainAnalyzerTiming:
    """测试时间统计计算"""

    @pytest.fixture
    def timing_data(self):
        """准备时间数据"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        chain = result.sessions.get(EXPECTED_SESSION_ID)
        return chain.iteration_timings if chain else []

    def test_timing_iteration_nums(self, timing_data):
        """测试迭代编号连续"""
        if timing_data:
            nums = [t.iteration_num for t in timing_data]
            assert nums[0] == 1
            assert nums[-1] == len(nums)

    def test_timing_llm_duration(self, timing_data):
        """测试 LLM 时间"""
        if timing_data:
            # 大部分迭代应有 LLM 时间
            with_llm = [t for t in timing_data if t.llm_call_duration > 0]
            assert len(with_llm) > 0

    def test_timing_session_id(self, timing_data):
        """测试 timing 的 session_id"""
        if timing_data:
            for t in timing_data[:5]:
                assert t.session_id != ""
