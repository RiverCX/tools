"""数据模型定义模块"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IterationTiming:
    """单个迭代的时间统计"""

    iteration_num: int
    session_id: str
    request_timestamp: float = 0.0
    response_timestamp: float = 0.0
    llm_call_duration: float = 0.0  # 模型调用时间（秒）
    tool_processing_duration: float = 0.0  # 工具调用+思考时间（秒）
    is_last_iteration: bool = False


@dataclass
class LLMRequest:
    session_id: str
    iteration: int
    model_name: str
    timestamp: float
    body: Dict[str, Any]
    messages: List[Dict[str, Any]] = field(default_factory=list)
    tools: List[Dict[str, Any]] = field(default_factory=list)
    source: str = "parent"
    source_label: str = ""
    is_internal: bool = False  # 是否为框架内部请求（如 command_intent）


@dataclass
class LLMResponse:
    session_id: str
    iteration: int
    model_name: str
    timestamp: float
    content: str = ""
    reasoning_content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    source: str = "parent"
    source_label: str = ""


@dataclass
class SubagentInfo:
    task_id: str
    session_id: str
    start_time: float = 0.0
    end_time: float = 0.0
    depth: int = 0  # 嵌套深度：0=直接子Agent, 1=子Agent的子Agent...
    parent_session_id: str = ""  # 直接调用者 session_id
    chain_path: List[str] = field(default_factory=list)  # 嵌套路径：["Parent", "Sub1", "Sub2"]


@dataclass
class LLMChain:
    session_id: str
    model_name: str
    requests: List[LLMRequest] = field(default_factory=list)
    responses: List[LLMResponse] = field(default_factory=list)
    start_time: float = 0.0
    end_time: float = 0.0
    total_iterations: int = 0
    subagents: List[SubagentInfo] = field(default_factory=list)
    is_subagent: bool = False
    # 时间统计
    iteration_timings: List[IterationTiming] = field(default_factory=list)
    total_llm_duration_seconds: float = 0.0
    total_tool_duration_seconds: float = 0.0


@dataclass
class Statistics:
    total_sessions: int = 0
    total_requests: int = 0
    total_responses: int = 0
    total_iterations: int = 0
    sessions_by_model: Dict[str, int] = field(default_factory=dict)
    # 时间统计
    total_duration_seconds: float = 0.0  # 所有 session 总耗时
    total_llm_time_seconds: float = 0.0  # 模型调用总时间
    total_tool_time_seconds: float = 0.0  # 工具调用+思考总时间
    avg_llm_time_seconds: float = 0.0  # 平均每次模型调用耗时
    avg_tool_time_seconds: float = 0.0  # 平均每次工具调用+思考耗时


@dataclass(init=False)
class AnalysisResult:
    sessions: Dict[str, LLMChain]
    statistics: Statistics
    sorted_sessions: List[LLMChain]

    def __init__(self):
        self.sessions = {}
        self.statistics = Statistics()
        self.sorted_sessions = []
