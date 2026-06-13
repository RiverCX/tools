"""测试配置"""

import pytest
import sys
from pathlib import Path

from llm_trace_analyzer.loader import LogLoader
from llm_trace_analyzer.parser import TraceParser
from llm_trace_analyzer.analyzer import ChainAnalyzer

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 测试数据路径
FIXTURES_DIR = project_root / "tests" / "fixtures"
SAMPLE_LOG = FIXTURES_DIR / "llm_trace_b2fbb87bbeeb.log"

# 预期值（基于精简日志）
EXPECTED_SESSION_ID = "officeclaw_b2fbb87bbeebde489553cb50"
EXPECTED_SHORT_ID = "b2fbb87bbeeb"
EXPECTED_MODEL_NAME = "glm-5"

# 解析阶段预期值
EXPECTED_TRACE_COUNT = 836
EXPECTED_PARSE_REQUESTS = 37  # 各 session 独立计数
EXPECTED_PARSE_RESPONSES = 37

# 分析阶段预期值（合并后的 chain）
EXPECTED_CHAIN_REQUESTS = 43
EXPECTED_CHAIN_RESPONSES = 43
EXPECTED_CHAIN_ITERATIONS = 43

# Subagent 数量
EXPECTED_SUBAGENT_COUNT = 9

# 预期的统计信息
EXPECTED_TOTAL_ITERATIONS = EXPECTED_CHAIN_ITERATIONS

# Subagent session IDs
EXPECTED_SUBAGENT_SESSIONS = [
    "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651",
    "officeclaw_b2fbb87bbeebde489553cb50_subagent_dceb49b5",
    "officeclaw_b2fbb87bbeebde489553cb50_subagent_131f0848",
    "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651_fork_agent_0e4cf63b",
    "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651_fork_agent_82d818e3",
    "officeclaw_b2fbb87bbeebde489553cb50_subagent_ade2a651_fork_agent_ab88ae4e",
]


@pytest.fixture
def loader():
    """日志加载器 fixture"""
    return LogLoader(str(SAMPLE_LOG))


@pytest.fixture
def traces(loader):
    """traces fixture"""
    return loader.load()


@pytest.fixture
def parser_data(traces):
    """解析数据 fixture"""
    parser = TraceParser(traces)
    requests, responses = parser.parse()
    return requests, responses


@pytest.fixture
def analyzer_data(parser_data):
    """分析数据 fixture"""
    requests, responses = parser_data
    analyzer = ChainAnalyzer(requests, responses)
    result = analyzer.analyze()
    return result


@pytest.fixture
def report_data(analyzer_data):
    """报告数据 fixture"""
    return analyzer_data
