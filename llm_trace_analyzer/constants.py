"""常量定义模块"""

from enum import Enum


class TraceEventType(Enum):
    STREAM_REQUEST = "stream_request"
    STREAM_OUTPUT = "stream_output"
    REASONING_DELTA = "reasoning_delta"
    INVOKE_REQUEST = "invoke_request"
    INVOKE_OUTPUT = "invoke_output"
    SYSTEM_METRICS = "system_metrics"


DEFAULT_LOGS_DIR = ".office-claw/.jiuwenclaw/service_default/.logs"
DEFAULT_LOG_FILE = "full.json"
DEFAULT_LOG_FILE_FALLBACK = "full.log"
TRACE_MARKER = "[LLM_IO_TRACE]"
