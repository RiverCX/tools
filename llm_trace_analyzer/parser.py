"""LLM_IO_TRACE 解析器 - 分片合并与JSON解析"""

import json
import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from .constants import TraceEventType
from .models import LLMRequest, LLMResponse, SystemMetrics


class TraceParser:
    def __init__(self, traces: List[Dict[str, Any]]):
        self.traces = traces

    def parse(self) -> Tuple[Dict[str, List[LLMRequest]], Dict[str, List[LLMResponse]], Dict[Tuple[str, int], List[SystemMetrics]]]:
        grouped = self._group_traces()

        requests: Dict[str, List[LLMRequest]] = {}
        responses: Dict[str, List[LLMResponse]] = {}
        system_metrics: Dict[Tuple[str, int], List[SystemMetrics]] = {}

        for session_id, session_traces in grouped.items():
            reqs, resps, metrics = self._parse_session(session_id, session_traces)
            if reqs:
                requests[session_id] = reqs
            if resps:
                responses[session_id] = resps
            if metrics:
                system_metrics.update(metrics)

        return requests, responses, system_metrics

    def _group_traces(self) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for trace in self.traces:
            session_id = trace["session_id"]
            if session_id:
                grouped[session_id].append(trace)
        return dict(grouped)

    def _parse_session(
        self, session_id: str, traces: List[Dict[str, Any]]
    ) -> Tuple[List[LLMRequest], List[LLMResponse], Dict[Tuple[str, int], List[SystemMetrics]]]:
        # 按 iteration 和事件类型分组
        by_iteration: Dict[int, List[Dict[str, Any]]] = defaultdict(list)

        for trace in traces:
            iteration = trace["iteration"]
            by_iteration[iteration].append(trace)

        requests: List[LLMRequest] = []
        responses: List[LLMResponse] = []
        system_metrics: Dict[Tuple[str, int], List[SystemMetrics]] = {}

        for iteration in sorted(by_iteration.keys()):
            iter_traces = by_iteration[iteration]

            # 分离不同事件类型
            request_traces = [
                t
                for t in iter_traces
                if t["event"]
                in (TraceEventType.STREAM_REQUEST.value, TraceEventType.INVOKE_REQUEST.value)
            ]
            output_traces = [
                t
                for t in iter_traces
                if t["event"]
                in (TraceEventType.STREAM_OUTPUT.value, TraceEventType.INVOKE_OUTPUT.value)
            ]
            reasoning_traces = [
                t for t in iter_traces if t["event"] == TraceEventType.REASONING_DELTA.value
            ]
            system_metrics_traces = [
                t for t in iter_traces if t["event"] == TraceEventType.SYSTEM_METRICS.value
            ]

            # 按 stream_request/stream_output 时间戳聚类（阈值 1 秒）
            request_groups = self._group_by_timestamp(request_traces, threshold=1.0)
            output_groups = self._group_by_timestamp(output_traces, threshold=1.0)

            # reasoning_delta 按 seq 重置分组
            reasoning_groups = self._group_by_seq_reset(reasoning_traces)

            # 按 request/output 数量确定 iteration 数（应该是一致的）
            num_iterations = len(request_groups)
            if num_iterations != len(output_groups):
                # 如果不一致，使用较大的数量
                num_iterations = max(len(request_groups), len(output_groups))

            for sub_iteration in range(num_iterations):
                actual_iteration = iteration * 10 + sub_iteration

                req_traces = (
                    request_groups[sub_iteration] if sub_iteration < len(request_groups) else []
                )
                out_traces = (
                    output_groups[sub_iteration] if sub_iteration < len(output_groups) else []
                )

                # 计算当前 output group 的中心时间
                if out_traces:
                    out_center = sum(t["timestamp"] for t in out_traces) / len(out_traces)
                elif req_traces:
                    # 如果没有 output，用 request 的结束时间作为参考
                    out_center = (
                        max(t["timestamp"] for t in req_traces) + 30
                    )  # 预期 output 在 request 后约 30 秒
                else:
                    out_center = 0

                # 找最接近的 reasoning group
                reason_traces = []
                if reasoning_groups:
                    # 选择时间距离最近的 reasoning group
                    best_group = None
                    best_distance = float("inf")
                    for rg in reasoning_groups:
                        rg_center = sum(t["timestamp"] for t in rg) / len(rg)
                        distance = abs(rg_center - out_center)
                        if distance < best_distance:
                            best_distance = distance
                            best_group = rg
                    if best_group and best_distance < 120:  # 最大允许 120 秒差距
                        reason_traces = best_group

                if req_traces:
                    req = self._parse_request(session_id, actual_iteration, req_traces)
                    if req:
                        requests.append(req)

                if out_traces or reason_traces:
                    resp = self._parse_response(
                        session_id,
                        actual_iteration,
                        out_traces,
                        reason_traces,
                    )
                    if resp:
                        responses.append(resp)

            # 解析 system_metrics traces
            if system_metrics_traces:
                metrics_list = []
                for trace in system_metrics_traces:
                    body_str = trace.get("body_str", "")
                    if body_str:
                        try:
                            body = json.loads(body_str)
                            metrics = SystemMetrics(
                                phase=body.get("phase", ""),
                                cpu_percent=body.get("cpu_percent", 0.0),
                                memory_rss_mb=body.get("memory_rss_mb", 0.0),
                                memory_vms_mb=body.get("memory_vms_mb", 0.0),
                                read_bytes=body.get("read_bytes", 0),
                                write_bytes=body.get("write_bytes", 0),
                                timestamp=trace.get("timestamp", 0.0),
                            )
                            metrics_list.append(metrics)
                        except json.JSONDecodeError:
                            pass
                if metrics_list:
                    # 使用 iteration * 10 作为 key（与 actual_iteration 对应）
                    system_metrics[(session_id, iteration * 10)] = metrics_list

        return requests, responses, system_metrics

    def _group_by_timestamp(
        self, traces: List[Dict[str, Any]], threshold: float = 1.0
    ) -> List[List[Dict[str, Any]]]:
        """按时间戳聚类，同一 iteration 内时间差超过阈值的分开"""
        if not traces:
            return []

        sorted_traces = sorted(traces, key=lambda t: t["timestamp"])
        groups: List[List[Dict[str, Any]]] = []
        current_group: List[Dict[str, Any]] = [sorted_traces[0]]

        for trace in sorted_traces[1:]:
            if trace["timestamp"] - current_group[-1]["timestamp"] > threshold:
                groups.append(current_group)
                current_group = [trace]
            else:
                current_group.append(trace)

        groups.append(current_group)
        return groups

    def _parse_request(
        self, session_id: str, iteration: int, traces: List[Dict[str, Any]]
    ) -> Optional[LLMRequest]:
        merged_body = self._merge_body_parts(traces)
        if not merged_body:
            return None

        try:
            body_dict = json.loads(merged_body)
        except json.JSONDecodeError:
            return None

        timestamp = traces[0]["timestamp"] if traces else 0
        model_name = traces[0]["model_name"] if traces else ""

        messages = body_dict.get("messages", [])
        tools = body_dict.get("tools", [])

        # 判断是否为框架内部请求（如 command_intent）
        is_internal = False
        if not tools and len(messages) == 1:
            first_msg = messages[0]
            if first_msg.get("role") == "user":
                content = first_msg.get("content", "")
                # 检查是否包含框架内部提示关键词
                internal_keywords = [
                    "安全工具调用解析器",
                    "你是一个安全工具调用解析器",
                    "file_guard.extract",
                    "command_intent",
                ]
                if any(kw in content for kw in internal_keywords):
                    is_internal = True

        return LLMRequest(
            session_id=session_id,
            iteration=iteration,
            model_name=model_name,
            timestamp=timestamp,
            body=body_dict,
            messages=messages,
            tools=tools,
            is_internal=is_internal,
        )

    def _parse_response(
        self,
        session_id: str,
        iteration: int,
        output_traces: List[Dict[str, Any]],
        reasoning_traces: List[Dict[str, Any]],
    ) -> Optional[LLMResponse]:
        merged_body = self._merge_body_parts(output_traces)
        body_dict = {}
        if merged_body:
            try:
                body_dict = json.loads(merged_body)
            except json.JSONDecodeError:
                pass

        # 如果 output 和 reasoning 都为空，跳过
        reasoning_merged = self._merge_reasoning(reasoning_traces)
        if not body_dict and not reasoning_merged:
            return None

        timestamp = output_traces[0]["timestamp"] if output_traces else (
            reasoning_traces[0]["timestamp"] if reasoning_traces else 0
        )
        model_name = output_traces[0]["model_name"] if output_traces else (
            reasoning_traces[0]["model_name"] if reasoning_traces else ""
        )

        content = body_dict.get("content", "")
        reasoning_content = body_dict.get("reasoning_content", "") or ""

        # 仅当 output body 未携带 reasoning_content 时，才回退到 reasoning_delta 合并结果。
        # body 中的 reasoning_content 是权威值；当 trace 共享 iteration=0 / 复用 request_id 时，
        # reasoning_delta 按时间戳聚类会错配到其他调用，直接覆盖会导致显示异常且与 token 统计不符。
        if not reasoning_content and reasoning_merged:
            reasoning_content = reasoning_merged

        tool_calls = body_dict.get("tool_calls", [])

        # 解析 usage_metadata
        usage_metadata = body_dict.get("usage_metadata", "")
        token_stats = self._parse_usage_metadata(usage_metadata)

        return LLMResponse(
            session_id=session_id,
            iteration=iteration,
            model_name=model_name,
            timestamp=timestamp,
            content=content,
            reasoning_content=reasoning_content,
            tool_calls=tool_calls,
            input_tokens=token_stats.get("input_tokens", 0),
            output_tokens=token_stats.get("output_tokens", 0),
            total_tokens=token_stats.get("total_tokens", 0),
            cache_tokens=token_stats.get("cache_tokens", 0),
            input_cost=token_stats.get("input_cost", 0.0),
            output_cost=token_stats.get("output_cost", 0.0),
            total_cost=token_stats.get("total_cost", 0.0),
        )

    def _parse_usage_metadata(self, usage_str: str) -> Dict[str, Any]:
        """解析 usage_metadata 字符串，提取 token 统计信息。

        格式: "code=0 err_msg='' prompt='' task_id='' model_name='glm-5.1'
               total_latency=0.0 first_token_time='******' request_start_time=''
               input_tokens=23661 output_tokens=3546 total_tokens=27207
               cache_tokens=0 input_cost=0.0 output_cost=0.0 total_cost=0.0"
        """
        if not usage_str:
            return {}

        result = {}
        # 提取数值字段
        int_fields = ["input_tokens", "output_tokens", "total_tokens", "cache_tokens"]
        float_fields = ["input_cost", "output_cost", "total_cost"]

        for field in int_fields:
            match = re.search(rf"{field}=(\d+)", usage_str)
            if match:
                result[field] = int(match.group(1))

        for field in float_fields:
            match = re.search(rf"{field}=([\d.]+)", usage_str)
            if match:
                result[field] = float(match.group(1))

        return result

    def _merge_body_parts(self, traces: List[Dict[str, Any]]) -> str:
        if not traces:
            return ""

        with_parts = [t for t in traces if t["body_part"] is not None]
        without_parts = [t for t in traces if t["body_part"] is None]

        if with_parts:
            sorted_traces = sorted(with_parts, key=lambda t: t["body_part"][0])
            merged = "".join(str(t["body_str"]) for t in sorted_traces)
            return merged

        if without_parts:
            return str(without_parts[0]["body_str"])

        return ""

    def _merge_reasoning(self, traces: List[Dict[str, Any]]) -> str:
        if not traces:
            return ""

        with_seq = [t for t in traces if t.get("reasoning_seq") is not None]
        if with_seq:
            # 按 seq 重置分组，再按 seq 排序合并
            groups = self._group_by_seq_reset(with_seq)
            merged_parts = []
            for group in groups:
                sorted_group = sorted(group, key=lambda t: t["reasoning_seq"])
                merged_parts.append("".join(str(t["body_str"]) for t in sorted_group))
            return "".join(merged_parts)

        merged_body = self._merge_body_parts(traces)
        if not merged_body:
            return ""

        try:
            body_dict = json.loads(merged_body)
            return body_dict.get("reasoning_content", "") or ""
        except json.JSONDecodeError:
            return ""

    def _group_by_seq_reset(self, traces: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """按 reasoning_seq 重置分组：seq 从高变低说明是新的一组"""
        if not traces:
            return []

        sorted_traces = sorted(traces, key=lambda t: t["timestamp"])
        groups: List[List[Dict[str, Any]]] = []
        current_group: List[Dict[str, Any]] = [sorted_traces[0]]

        for trace in sorted_traces[1:]:
            prev_seq = current_group[-1].get("reasoning_seq", 0)
            curr_seq = trace.get("reasoning_seq", 0)
            # seq 重置（从高变低）说明是新的一组
            if curr_seq < prev_seq:
                groups.append(current_group)
                current_group = [trace]
            else:
                current_group.append(trace)

        groups.append(current_group)
        return groups
