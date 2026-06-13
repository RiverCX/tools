"""测试 TraceParser 模块"""

import pytest

from llm_trace_analyzer.loader import LogLoader
from llm_trace_analyzer.parser import TraceParser
from tests.conftest import (
    SAMPLE_LOG,
    EXPECTED_SESSION_ID,
    EXPECTED_PARSE_REQUESTS,
    EXPECTED_PARSE_RESPONSES,
)


class TestTraceParser:
    """测试解析器"""

    @pytest.fixture
    def parser_data(self):
        """准备解析数据"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses = parser.parse()
        return requests, responses

    def test_parse_returns_dicts(self):
        """测试解析返回字典结构"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()
        parser = TraceParser(traces)
        requests, responses = parser.parse()

        assert isinstance(requests, dict)
        assert isinstance(responses, dict)

    def test_main_session_requests(self, parser_data):
        """测试主 session 的请求数量"""
        requests, _ = parser_data

        main_session_requests = requests.get(EXPECTED_SESSION_ID, [])
        # 主 session 至少有请求
        assert len(main_session_requests) > 0

    def test_request_fields(self, parser_data):
        """测试请求字段"""
        requests, _ = parser_data

        # 取第一个请求检查字段
        all_requests = [r for reqs in requests.values() for r in reqs]
        if all_requests:
            first_req = all_requests[0]
            assert hasattr(first_req, "session_id")
            assert hasattr(first_req, "iteration")
            assert hasattr(first_req, "timestamp")
            assert hasattr(first_req, "body")
            assert hasattr(first_req, "messages")
            assert hasattr(first_req, "tools")

    def test_response_fields(self, parser_data):
        """测试响应字段"""
        _, responses = parser_data

        all_responses = [r for resps in responses.values() for r in resps]
        if all_responses:
            first_resp = all_responses[0]
            assert hasattr(first_resp, "session_id")
            assert hasattr(first_resp, "iteration")
            assert hasattr(first_resp, "timestamp")
            assert hasattr(first_resp, "content")
            assert hasattr(first_resp, "reasoning_content")
            assert hasattr(first_resp, "tool_calls")

    def test_body_part_merging(self):
        """测试分片合并功能"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        # 找有多个分片的请求
        request_traces = [t for t in traces if t["event"] == "stream_request"]
        if request_traces:
            parser = TraceParser(traces)
            requests, _ = parser.parse()

            # 检查合并后的请求 body 是完整 JSON
            all_requests = [r for reqs in requests.values() for r in reqs]
            for req in all_requests[:3]:
                assert isinstance(req.body, dict)

    def test_reasoning_merging(self, parser_data):
        """测试 reasoning 合并"""
        _, responses = parser_data

        all_responses = [r for resps in responses.values() for r in resps]
        # 检查有 reasoning_content 的响应
        with_reasoning = [r for r in all_responses if r.reasoning_content]
        assert len(with_reasoning) > 0

    def test_iteration_count(self, parser_data):
        """测试迭代数量"""
        requests, responses = parser_data

        total_requests = sum(len(reqs) for reqs in requests.values())
        total_responses = sum(len(resps) for resps in responses.values())

        assert total_requests == EXPECTED_PARSE_REQUESTS
        assert total_responses == EXPECTED_PARSE_RESPONSES

    def test_subagent_sessions_parsed(self, parser_data):
        """测试 subagent session 解析"""
        requests, responses = parser_data

        # 检查包含 subagent session
        subagent_request_keys = [k for k in requests.keys() if "_subagent_" in k]
        subagent_response_keys = [k for k in responses.keys() if "_subagent_" in k]

        assert len(subagent_request_keys) > 0
        assert len(subagent_response_keys) > 0


class TestTraceParserGrouping:
    """测试时间戳分组"""

    def test_group_by_timestamp(self):
        """测试时间戳分组逻辑"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        # 只取一个 session 的 traces
        session_traces = [t for t in traces if t["session_id"] == EXPECTED_SESSION_ID]
        parser = TraceParser(session_traces)

        # 测试分组方法
        request_traces = [t for t in session_traces if t["event"] == "stream_request"]
        groups = parser._group_by_timestamp(request_traces, threshold=1.0)

        assert isinstance(groups, list)
        if groups:
            assert isinstance(groups[0], list)

    def test_group_by_seq_reset(self):
        """测试 reasoning_seq 重置分组"""
        loader = LogLoader(str(SAMPLE_LOG))
        traces = loader.load()

        reasoning_traces = [t for t in traces if t["event"] == "reasoning_delta"]
        if reasoning_traces:
            parser = TraceParser(traces)
            groups = parser._group_by_seq_reset(reasoning_traces)

            assert isinstance(groups, list)
