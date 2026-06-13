"""HTML报告生成器"""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import AnalysisResult, IterationTiming, LLMChain, LLMRequest, LLMResponse, SubagentInfo
from .templates import (
    CONTENT_TEMPLATE,
    INDEX_TEMPLATE,
    ITERATION_DETAIL_TEMPLATE,
    JSON_BLOCK_TEMPLATE,
    REASONING_TEMPLATE,
    REQUEST_TEMPLATE,
    RESPONSE_TEMPLATE,
    SESSION_DETAIL_TEMPLATE,
    SESSION_ROW_TEMPLATE,
    SUBAGENT_NODE_TEMPLATE,
    SUBAGENT_TREE_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    TIMING_ITEM_TEMPLATE,
    TIMING_LIST_TEMPLATE,
    TOOL_CALLS_TEMPLATE,
    TOOL_NAME_ITEM_TEMPLATE,
    TOOL_RESULT_TEMPLATE,
    TOOLS_SECTION_TEMPLATE,
)


class HTMLReporter:
    _id_counter = 0

    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path

    def generate(self, result: AnalysisResult, output_path: str) -> None:
        output_dir = Path(output_path).parent
        output_name = Path(output_path).stem

        report_dir = output_dir / output_name
        report_dir.mkdir(parents=True, exist_ok=True)

        self._generate_index(result, report_dir)

        for chain in result.sorted_sessions:
            self._generate_session_detail(chain, report_dir)

        print(f"Report generated in: {report_dir}/")
        print("  - index.html (session list)")
        for chain in result.sorted_sessions:
            short_id = self._short_session_id(chain.session_id)
            print(f"  - session_{short_id}.html")

    def _generate_index(self, result: AnalysisResult, report_dir: Path) -> None:
        stats = result.statistics

        session_rows: List[str] = []
        for chain in result.sorted_sessions:
            short_id = self._short_session_id(chain.session_id)
            detail_file = f"session_{short_id}.html"

            row = SESSION_ROW_TEMPLATE.format(
                session_id_short=short_id,
                session_id=chain.session_id,
                model_name=chain.model_name,
                total_iterations=chain.total_iterations,
                start_time=self._format_timestamp(chain.start_time),
                end_time=self._format_timestamp(chain.end_time),
                detail_file=detail_file,
            )
            session_rows.append(row)

        index_html = INDEX_TEMPLATE.format(
            total_sessions=stats.total_sessions,
            total_requests=stats.total_requests,
            total_iterations=stats.total_iterations,
            total_duration=self._format_duration(stats.total_duration_seconds),
            avg_llm_time=self._format_duration(stats.avg_llm_time_seconds),
            session_rows="\n".join(session_rows),
        )

        with open(report_dir / "index.html", "w", encoding="utf-8") as f:
            f.write(index_html)

    def _generate_session_detail(self, chain: LLMChain, report_dir: Path) -> None:
        short_id = self._short_session_id(chain.session_id)
        detail_file = report_dir / f"session_{short_id}.html"

        iterations_html = self._generate_iterations_html(chain)
        subagents_tree_html = self._generate_subagents_tree_html(chain)
        timing_list_html = self._generate_timing_list_html(chain)

        # 计算平均值
        num_iters = len(chain.iteration_timings)
        avg_llm = chain.total_llm_duration_seconds / num_iters if num_iters > 0 else 0

        html_content = SESSION_DETAIL_TEMPLATE.format(
            session_id_short=short_id,
            session_id=chain.session_id,
            model_name=chain.model_name,
            total_iterations=chain.total_iterations,
            start_time=self._format_timestamp(chain.start_time),
            end_time=self._format_timestamp(chain.end_time),
            session_duration=self._format_duration(chain.end_time - chain.start_time),
            total_llm_duration=self._format_duration(chain.total_llm_duration_seconds),
            total_tool_duration=self._format_duration(chain.total_tool_duration_seconds),
            avg_llm_per_iter=self._format_duration(avg_llm),
            timing_list_html=timing_list_html,
            subagents_tree_html=subagents_tree_html,
            iterations_html=iterations_html,
        )

        with open(detail_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_subagents_tree_html(self, chain: LLMChain) -> str:
        if not chain.subagents:
            return ""

        # 按深度和开始时间排序
        sorted_subagents = sorted(chain.subagents, key=lambda s: (s.depth, s.start_time))

        tree_nodes: List[str] = []
        for sa in sorted_subagents:
            # 计算 iterations 数量
            iterations = len(self._get_requests_for_subagent(chain, sa.session_id))

            node_html = SUBAGENT_NODE_TEMPLATE.format(
                depth=sa.depth,
                chain_label=" → ".join(sa.chain_path) if sa.chain_path else sa.task_id[:12],
                iterations=iterations,
            )
            tree_nodes.append(node_html)

        return SUBAGENT_TREE_TEMPLATE.format(
            subagent_count=len(chain.subagents),
            tree_nodes_html="\n".join(tree_nodes),
        )

    def _generate_timing_list_html(self, chain: LLMChain) -> str:
        """生成迭代耗时列表 HTML"""
        if not chain.iteration_timings:
            return ""

        # 构建 iteration_num -> response 的映射，获取 content
        response_map: Dict[int, LLMResponse] = {}
        for resp in chain.responses:
            # 按 timestamp 找对应的 iteration_num
            for timing in chain.iteration_timings:
                if abs(resp.timestamp - timing.response_timestamp) < 1.0:
                    response_map[timing.iteration_num] = resp
                    break

        timing_items: List[str] = []
        for timing in chain.iteration_timings:
            # 获取 response content
            resp = response_map.get(timing.iteration_num)
            content = resp.content if resp else ""
            # 截断预览（最多 80 字符）
            content_preview = content[:80] + "..." if len(content) > 80 else content
            if not content_preview:
                content_preview = "(no content)"

            total_seconds = timing.llm_call_duration + timing.tool_processing_duration

            item_html = TIMING_ITEM_TEMPLATE.format(
                iteration_num=timing.iteration_num,
                llm_seconds=timing.llm_call_duration,
                tool_seconds=timing.tool_processing_duration,
                total_seconds=total_seconds,
                llm_duration=self._format_duration(timing.llm_call_duration),
                tool_duration=self._format_duration(timing.tool_processing_duration),
                total_duration=self._format_duration(total_seconds),
                content_preview=html.escape(content_preview),
                content_full=html.escape(content),
            )
            timing_items.append(item_html)

        return TIMING_LIST_TEMPLATE.format(
            total_iterations=len(chain.iteration_timings),
            timing_items_html="\n".join(timing_items),
        )

    def _get_requests_for_subagent(self, chain: LLMChain, session_id: str) -> List[LLMRequest]:
        """获取特定 subAgent session 的请求"""
        return [r for r in chain.requests if r.session_id == session_id]

    def _short_session_id(self, session_id: str) -> str:
        if not session_id:
            return "unknown"
        parts = session_id.split("_")
        if len(parts) >= 2:
            return parts[-1][:12]
        return session_id[:12]

    def _next_id(self) -> str:
        self._id_counter += 1
        return f"content_{self._id_counter}"

    def _generate_iterations_html(self, chain: LLMChain) -> str:
        # 先构建全局 tool_call_id → tool_name 映射表
        global_tool_name_map: Dict[str, str] = {}
        for resp in chain.responses:
            if resp.tool_calls:
                for tc in resp.tool_calls:
                    tc_id = tc.get("id", "")
                    # 支持两种格式：旧格式直接有 name，新格式在 function.name 下
                    tc_name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                    if tc_id and tc_name:
                        global_tool_name_map[tc_id] = tc_name

        # 构建 iteration_num -> timing 映射
        timing_map: Dict[int, Dict] = {}
        for timing in chain.iteration_timings:
            timing_map[timing.iteration_num] = {
                "llm_duration": timing.llm_call_duration,
                "tool_duration": timing.tool_processing_duration,
            }

        # 按 (session_id, iteration) 配对请求和响应
        paired_items: Dict[Tuple[str, int], Dict] = {}

        for req in chain.requests:
            key = (req.session_id, req.iteration)
            if key not in paired_items:
                paired_items[key] = {"request": None, "response": None, "timestamp": 0}
            paired_items[key]["request"] = req
            paired_items[key]["timestamp"] = req.timestamp

        for resp in chain.responses:
            key = (resp.session_id, resp.iteration)
            if key not in paired_items:
                paired_items[key] = {"request": None, "response": None, "timestamp": 0}
            paired_items[key]["response"] = resp
            # 如果没有 request，用 response 的 timestamp
            if paired_items[key]["timestamp"] == 0:
                paired_items[key]["timestamp"] = resp.timestamp

        # 按 timestamp 排序
        sorted_items = sorted(paired_items.values(), key=lambda x: x["timestamp"])

        iterations_parts: List[str] = []
        # 按 session_id 维护 prev_request，避免跨 session 比较导致 Tool Call Results 计算错误
        prev_requests_by_session: Dict[str, Optional[LLMRequest]] = {}
        prev_response: Optional[LLMResponse] = None
        for i, item in enumerate(sorted_items):
            iteration_num = i + 1

            request_html = ""
            depth = 0
            depth_indicator = ""
            is_internal = False
            body_id = ""
            body_json = ""
            copy_body_btn = ""
            if item["request"]:
                request = item["request"]
                is_internal = request.is_internal
                session_id = request.session_id
                # 获取该 session 的 prev_request
                prev_request = prev_requests_by_session.get(session_id)
                # 判断是否是子 Agent 的第一次请求（继承父 Agent context，不应显示 Tool Call Results）
                is_subagent_first_request = request.source == "subagent" and prev_request is None
                request_html = self._generate_request_html(
                    request, prev_request, global_tool_name_map, is_subagent_first_request
                )
                if request.source == "subagent":
                    depth = self._calc_depth_from_label(request.source_label)
                # 内部请求不更新 prev_request，避免影响 Tool Call Results 计算
                if not is_internal:
                    prev_requests_by_session[session_id] = request
                # 生成 Copy Body 按钮和数据
                body_id = self._next_id()
                # 转换 tools 格式为标准 OpenAI 格式
                converted_body = self._convert_tools_to_openai_format(request.body)
                body_json_raw = json.dumps(converted_body, indent=2, ensure_ascii=False)
                body_json = html.escape(body_json_raw)
                copy_body_btn = f'<button class="copy-btn" style="margin-left: 15px;" onclick="copyRequestBody(this)">Copy Body</button>'

            response_html = ""
            if item["response"]:
                response = item["response"]
                response_html = self._generate_response_html(response)
                if response.source == "subagent":
                    depth = self._calc_depth_from_label(response.source_label)
                # 响应始终更新 prev_response（用于工具名称关联），即使是内部请求的响应
                prev_response = response

            if depth > 0:
                depth_indicator = f"(Depth {depth})"

            # 获取时间统计
            timing_info = timing_map.get(iteration_num, {})
            llm_duration_str = self._format_duration(timing_info.get("llm_duration", 0))
            tool_duration_str = self._format_duration(timing_info.get("tool_duration", 0))

            iteration_html = ITERATION_DETAIL_TEMPLATE.format(
                iteration_num=iteration_num,
                depth=depth,
                depth_indicator=depth_indicator,
                llm_duration=llm_duration_str,
                tool_duration=tool_duration_str,
                copy_body_btn=copy_body_btn,
                body_id=body_id,
                body_json=body_json,
                request_html=request_html,
                response_html=response_html,
            )
            iterations_parts.append(iteration_html)

        return "\n".join(iterations_parts)

    def _calc_depth_from_label(self, label: str) -> int:
        """从 source_label 计算嵌套深度，如 'Parent → Sub[xxx] → Fork[xxx]'"""
        if not label:
            return 0
        arrows = label.split(" → ")
        return len(arrows) - 1

    def _generate_request_html(
        self,
        request: LLMRequest,
        prev_request: Optional[LLMRequest] = None,
        global_tool_name_map: Dict[str, str] = None,
        is_subagent_first_request: bool = False,
    ) -> str:
        system_prompt_html = ""
        system_prompt_chars = 0
        other_messages = []

        for msg in request.messages:
            if msg.get("role") == "system" and not system_prompt_html:
                content = msg.get("content", "")
                if content:
                    system_prompt_chars = len(content)
                    content_id = self._next_id()
                    escaped_content = html.escape(content)
                    system_prompt_html = SYSTEM_PROMPT_TEMPLATE.format(
                        content_id=content_id,
                        system_prompt=escaped_content,
                        char_count=system_prompt_chars,
                    )
            else:
                other_messages.append(msg)

        messages_json = json.dumps(other_messages, indent=2, ensure_ascii=False)
        tools_json = json.dumps(request.tools, indent=2, ensure_ascii=False)
        messages_chars = len(messages_json)
        tools_chars = len(tools_json)

        messages_html = self._make_json_block(other_messages)
        tools_full_html = self._make_json_block(request.tools)
        tool_names_html = self._generate_tool_names_html(request.tools)
        timestamp_str = self._format_timestamp(request.timestamp)

        names_id = self._next_id()
        full_id = self._next_id()

        tools_section_html = TOOLS_SECTION_TEMPLATE.format(
            tool_count=len(request.tools),
            tools_chars=tools_chars,
            names_id=names_id,
            full_id=full_id,
            tool_names_html=tool_names_html,
            tools_html=tools_full_html,
        )

        # 生成 Tool Call Results HTML
        new_message_html = self._generate_new_message_html(
            other_messages, prev_request, global_tool_name_map or {}, is_subagent_first_request
        )

        request_chars = system_prompt_chars + messages_chars + tools_chars

        # 生成内部请求标记
        internal_label = ""
        if request.is_internal:
            internal_label = (
                '<span class="label" style="background: #ff9800; color: white;">Internal</span>'
            )

        return REQUEST_TEMPLATE.format(
            timestamp=timestamp_str,
            request_chars=request_chars,
            source_class="subagent" if request.source == "subagent" else "",
            source_label=request.source_label,
            internal_label=internal_label,
            system_prompt_html=system_prompt_html,
            message_count=len(other_messages),
            messages_chars=messages_chars,
            messages_html=messages_html,
            tools_html=tools_section_html,
            new_message_html=new_message_html,
        )

    def _generate_tool_names_html(self, tools: List) -> str:
        """生成工具名网格 HTML"""
        items = []
        for tool in tools:
            name = tool.get("name", "")
            if name:
                items.append(TOOL_NAME_ITEM_TEMPLATE.format(name=name))
        return "\n".join(items)

    def _generate_new_message_html(
        self,
        current_messages: List,
        prev_request: Optional[LLMRequest],
        global_tool_name_map: Dict[str, str],
        is_subagent_first_request: bool = False,
    ) -> str:
        """生成 ToolResult 部分 HTML，显示与上一个迭代相比新增的工具调用结果"""
        # 只显示 tool 类型的 messages（工具调用结果）
        # assistant 是上一轮 RESPONSE 的输出，user 是用户输入，不应算作 REQUEST 的新增
        current_tools = [m for m in current_messages if m.get("role") == "tool"]

        if not prev_request:
            # 子 Agent 的第一次请求继承了父 Agent 的 context，其中的 tool messages 不应算作新增
            if is_subagent_first_request:
                return ""
            # 主 session 的第一个迭代，所有 tool message 都是新的
            if not current_tools:
                return ""
            new_messages = current_tools
        else:
            # 获取上一个迭代的 tool messages
            prev_tools = [m for m in prev_request.messages if m.get("role") == "tool"]

            # 找出新增的 tool messages
            new_messages = self._find_new_messages(current_tools, prev_tools)

        if not new_messages:
            return ""

        # 为每个 tool message 获取工具名称（使用全局映射表）
        tool_names: List[str] = []
        for msg in new_messages:
            tc_id = msg.get("tool_call_id", "")
            name = global_tool_name_map.get(tc_id, tc_id[:20] if tc_id else "unknown")
            tool_names.append(name)

        new_messages_json = json.dumps(new_messages, indent=2, ensure_ascii=False)
        new_chars = len(new_messages_json)
        content_id = self._next_id()
        escaped_content = html.escape(new_messages_json)

        return TOOL_RESULT_TEMPLATE.format(
            new_count=len(new_messages),
            new_chars=new_chars,
            content_id=content_id,
            new_messages_json=escaped_content,
            tool_names=", ".join(tool_names),
        )

    def _find_new_messages(self, current_messages: List, prev_messages: List) -> List:
        """找出新增的 tool messages（基于 tool_call_id 判断）"""
        # 收集上一迭代的 tool_call_id 集合
        prev_tool_ids = set()
        for msg in prev_messages:
            tc_id = msg.get("tool_call_id", "")
            if tc_id:
                prev_tool_ids.add(tc_id)

        # 找当前迭代中 tool_call_id 不在上一迭代的 messages
        new_messages = []
        for msg in current_messages:
            tc_id = msg.get("tool_call_id", "")
            if tc_id and tc_id not in prev_tool_ids:
                new_messages.append(msg)

        return new_messages

    def _generate_response_html(self, response: LLMResponse) -> str:
        timestamp_str = self._format_timestamp(response.timestamp)

        reasoning_chars = 0
        reasoning_html = ""
        if response.reasoning_content:
            reasoning_chars = len(response.reasoning_content)
            content_id = self._next_id()
            escaped_content = html.escape(response.reasoning_content)
            reasoning_html = REASONING_TEMPLATE.format(
                content_id=content_id,
                reasoning_content=escaped_content,
                char_count=reasoning_chars,
            )

        content_chars = 0
        content_html = ""
        if response.content:
            content_chars = len(response.content)
            content_id = self._next_id()
            escaped_content = html.escape(response.content)
            content_html = CONTENT_TEMPLATE.format(
                content_id=content_id,
                content=escaped_content,
                char_count=content_chars,
            )

        tool_calls_chars = 0
        tool_calls_html = ""
        tool_names_list: List[str] = []
        if response.tool_calls:
            tool_calls_json = json.dumps(response.tool_calls, indent=2, ensure_ascii=False)
            tool_calls_chars = len(tool_calls_json)
            # 提取工具名称
            for tc in response.tool_calls:
                # 支持两种格式：旧格式直接有 name，新格式在 function.name 下
                name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                if name:
                    tool_names_list.append(name)
            tool_calls_html = self._make_json_block(
                response.tool_calls,
                tool_count=len(response.tool_calls),
                char_count=tool_calls_chars,
                tool_names=", ".join(tool_names_list),
            )

        response_chars = reasoning_chars + content_chars + tool_calls_chars

        return RESPONSE_TEMPLATE.format(
            timestamp=timestamp_str,
            response_chars=response_chars,
            source_class="subagent" if response.source == "subagent" else "",
            source_label=response.source_label,
            reasoning_html=reasoning_html,
            content_html=content_html,
            tool_calls_html=tool_calls_html,
        )

    def _make_json_block(
        self, obj, tool_count: int = 0, char_count: int = 0, tool_names: str = ""
    ) -> str:
        json_str = json.dumps(obj, indent=2, ensure_ascii=False)
        if char_count == 0:
            char_count = len(json_str)
        content_id = self._next_id()
        escaped_content = html.escape(json_str)

        if tool_count > 0:
            return TOOL_CALLS_TEMPLATE.format(
                content_id=content_id,
                tool_count=tool_count,
                char_count=char_count,
                tool_calls_json=escaped_content,
                tool_names=tool_names,
            )
        return JSON_BLOCK_TEMPLATE.format(content_id=content_id, content=escaped_content)

    def _format_timestamp(self, timestamp: float) -> str:
        if timestamp == 0:
            return "N/A"
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%m-%d %H:%M:%S")

    def _format_duration(self, seconds: float) -> str:
        """格式化时长显示"""
        if seconds <= 0:
            return "N/A"
        if seconds < 1:
            return f"{seconds * 1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        else:
            minutes = int(seconds / 60)
            secs = seconds % 60
            return f"{minutes}m {secs:.0f}s"

    def _convert_tools_to_openai_format(self, body: dict) -> dict:
        """将 tools 从旧格式转换为标准 OpenAI 格式

        旧格式: {"type": "function", "name": "xxx", "parameters": {...}}
        标准格式: {"type": "function", "function": {"name": "xxx", "parameters": {...}}}
        """
        if "tools" not in body or not body["tools"]:
            return body

        converted_tools = []
        for tool in body["tools"]:
            if tool.get("type") == "function" and "name" in tool and "function" not in tool:
                # 旧格式，需要转换
                converted_tool = {
                    "type": "function",
                    "function": {
                        "name": tool.get("name"),
                        "description": tool.get("description", ""),
                        "parameters": tool.get("parameters", {}),
                    },
                }
                # 保留其他可能的字段如 strict
                if "strict" in tool:
                    converted_tool["function"]["strict"] = tool["strict"]
                converted_tools.append(converted_tool)
            else:
                # 已经是标准格式或其他类型，保持不变
                converted_tools.append(tool)

        # 创建新的 body，不修改原始对象
        new_body = body.copy()
        new_body["tools"] = converted_tools
        return new_body
