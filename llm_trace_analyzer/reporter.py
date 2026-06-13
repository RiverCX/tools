"""HTML报告生成器"""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import AnalysisResult, IterationTiming, LLMChain, LLMRequest, LLMResponse, SubagentInfo
from .templates import (
    CONTENT_TEMPLATE,
    GANTT_BAR_TEMPLATE,
    GANTT_PANEL_TEMPLATE,
    INDEX_TEMPLATE,
    ITERATION_DETAIL_TEMPLATE,
    JSON_BLOCK_TEMPLATE,
    REASONING_TEMPLATE,
    REQUEST_TEMPLATE,
    RESPONSE_TEMPLATE,
    SESSION_DETAIL_TEMPLATE,
    SESSION_ROW_TEMPLATE,
    SYSTEM_PROMPT_TEMPLATE,
    TAB_BUTTON_TEMPLATE,
    TAB_CONTENT_WRAPPER_TEMPLATE,
    TAB_NAV_TEMPLATE,
    TAB_PANEL_TEMPLATE,
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

        agent_groups = self._build_agent_groups(chain)
        has_subagents = len(agent_groups) > 1

        gantt_html = self._generate_gantt_html(chain, agent_groups) if has_subagents else ""
        tabs_nav_html = self._generate_tabs_nav_html(agent_groups)
        tabs_content_html = self._generate_tabs_content_html(chain, agent_groups)

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
            gantt_html=gantt_html,
            tabs_nav_html=tabs_nav_html,
            tabs_content_html=tabs_content_html,
        )

        with open(detail_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _build_agent_groups(self, chain: LLMChain) -> List[Dict]:
        """将 iteration_timings 按 session_id 分组，返回 Agent 元数据列表"""
        # 按 session_id 分组 timings
        timings_by_session: Dict[str, List] = {}
        for timing in chain.iteration_timings:
            sid = timing.session_id
            if sid not in timings_by_session:
                timings_by_session[sid] = []
            timings_by_session[sid].append(timing)

        groups: List[Dict] = []

        # Parent session
        parent_timings = timings_by_session.get(chain.session_id, [])
        parent_start = parent_timings[0].request_timestamp if parent_timings else chain.start_time
        parent_end = parent_timings[-1].response_timestamp if parent_timings else chain.end_time
        groups.append({
            "agent_key": "parent",
            "label": "Parent",
            "session_id": chain.session_id,
            "is_parent": True,
            "depth": -1,
            "start_time": parent_start,
            "end_time": parent_end,
            "iteration_count": len(parent_timings),
            "timings": parent_timings,
        })

        # Subagent sessions
        sorted_subagents = sorted(chain.subagents, key=lambda s: (s.depth, s.start_time))
        for sa in sorted_subagents:
            sa_timings = timings_by_session.get(sa.session_id, [])
            label = sa.chain_path[-1] if sa.chain_path else self._short_session_id(sa.session_id)
            agent_key = f"sub_{self._short_session_id(sa.session_id)}"
            groups.append({
                "agent_key": agent_key,
                "label": label,
                "session_id": sa.session_id,
                "is_parent": False,
                "depth": sa.depth,
                "start_time": sa.start_time,
                "end_time": sa.end_time,
                "iteration_count": len(sa_timings),
                "timings": sa_timings,
            })

        return groups

    def _generate_gantt_html(self, chain: LLMChain, agent_groups: List[Dict]) -> str:
        """生成 Gantt 时间线面板"""
        session_start = chain.start_time
        session_end = chain.end_time
        total_span = max(session_end - session_start, 0.001)

        bars: List[str] = []
        for group in agent_groups:
            left_pct = ((group["start_time"] - session_start) / total_span) * 100
            width_pct = max(((group["end_time"] - group["start_time"]) / total_span) * 100, 0.5)
            depth_class = "parent" if group["is_parent"] else str(min(group["depth"], 2))
            bar_text = f'{group["iteration_count"]} iters'
            duration = self._format_duration(group["end_time"] - group["start_time"])

            bars.append(GANTT_BAR_TEMPLATE.format(
                label=group["label"],
                full_label=group["label"],
                agent_key=group["agent_key"],
                left_pct=f"{left_pct:.1f}",
                width_pct=f"{width_pct:.1f}",
                depth_class=depth_class,
                bar_text=bar_text,
                duration=duration,
                iteration_count=group["iteration_count"],
            ))

        return GANTT_PANEL_TEMPLATE.format(
            agent_count=len(agent_groups),
            total_duration=self._format_duration(chain.end_time - chain.start_time),
            gantt_bars_html="\n".join(bars),
        )

    def _generate_tabs_nav_html(self, agent_groups: List[Dict]) -> str:
        """生成 Tab 导航按钮"""
        buttons: List[str] = []
        for i, group in enumerate(agent_groups):
            active_class = " active" if i == 0 else ""
            buttons.append(TAB_BUTTON_TEMPLATE.format(
                agent_key=group["agent_key"],
                label=group["label"],
                iteration_count=group["iteration_count"],
                active_class=active_class,
            ))
        return TAB_NAV_TEMPLATE.format(tab_buttons_html="\n".join(buttons))

    def _generate_tabs_content_html(self, chain: LLMChain, agent_groups: List[Dict]) -> str:
        """生成所有 Tab 面板内容"""
        # 构建全局 tool_call_id → tool_name 映射表
        global_tool_name_map: Dict[str, str] = {}
        for resp in chain.responses:
            if resp.tool_calls:
                for tc in resp.tool_calls:
                    tc_id = tc.get("id", "")
                    tc_name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                    if tc_id and tc_name:
                        global_tool_name_map[tc_id] = tc_name

        # 构建 timing_map (global_num -> timing info)
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
            if paired_items[key]["timestamp"] == 0:
                paired_items[key]["timestamp"] = resp.timestamp

        # 按 timestamp 排序，分配全局编号
        sorted_items = sorted(paired_items.values(), key=lambda x: x["timestamp"])
        global_num_map: Dict[Tuple[str, int], int] = {}
        for i, item in enumerate(sorted_items):
            req = item["request"]
            resp = item["response"]
            if req:
                key = (req.session_id, req.iteration)
            else:
                key = (resp.session_id, resp.iteration)
            global_num_map[key] = i + 1

        # 按 session_id 分组
        items_by_session: Dict[str, List] = {}
        for item in sorted_items:
            req = item["request"]
            resp = item["response"]
            sid = req.session_id if req else resp.session_id
            if sid not in items_by_session:
                items_by_session[sid] = []
            items_by_session[sid].append(item)

        # 为每个 Agent 生成 Tab 面板
        panels: List[str] = []
        for i, group in enumerate(agent_groups):
            active_class = " active" if i == 0 else ""
            agent_items = items_by_session.get(group["session_id"], [])

            iterations_html = self._generate_agent_iterations_html(
                agent_items, group, global_tool_name_map, global_num_map, timing_map
            )
            timing_list_html = self._generate_agent_timing_html(group, chain, global_num_map)

            panels.append(TAB_PANEL_TEMPLATE.format(
                agent_key=group["agent_key"],
                active_class=active_class,
                timing_list_html=timing_list_html,
                iterations_html=iterations_html,
            ))

        return TAB_CONTENT_WRAPPER_TEMPLATE.format(tab_panels_html="\n".join(panels))

    def _generate_agent_iterations_html(
        self,
        agent_items: List[Dict],
        agent_group: Dict,
        global_tool_name_map: Dict[str, str],
        global_num_map: Dict[Tuple[str, int], int],
        timing_map: Dict[int, Dict],
    ) -> str:
        """生成单个 Agent 的迭代块列表"""
        parts: List[str] = []
        prev_request: Optional[LLMRequest] = None

        for i, item in enumerate(agent_items):
            local_num = i + 1
            req = item["request"]
            resp = item["response"]

            # 获取全局编号
            if req:
                key = (req.session_id, req.iteration)
            else:
                key = (resp.session_id, resp.iteration)
            global_num = global_num_map.get(key, 0)

            # 获取时间统计
            timing_info = timing_map.get(global_num, {})
            llm_duration_str = self._format_duration(timing_info.get("llm_duration", 0))
            tool_duration_str = self._format_duration(timing_info.get("tool_duration", 0))

            request_html = ""
            depth = 0
            depth_indicator = ""
            body_id = ""
            body_json = ""
            copy_body_btn = ""

            if req:
                is_subagent_first_request = (
                    req.source == "subagent" and prev_request is None
                )
                request_html = self._generate_request_html(
                    req, prev_request, global_tool_name_map, is_subagent_first_request
                )
                if not req.is_internal:
                    prev_request = req

                body_id = self._next_id()
                converted_body = self._convert_tools_to_openai_format(req.body)
                body_json_raw = json.dumps(converted_body, indent=2, ensure_ascii=False)
                body_json = html.escape(body_json_raw)
                copy_body_btn = '<button class="copy-btn" style="margin-left: 15px;" onclick="copyRequestBody(this)">Copy Body</button>'

            response_html = ""
            if resp:
                response_html = self._generate_response_html(resp)

            iteration_html = ITERATION_DETAIL_TEMPLATE.format(
                local_num=local_num,
                global_num=global_num,
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
            parts.append(iteration_html)

        return "\n".join(parts)

    def _generate_agent_timing_html(
        self,
        agent_group: Dict,
        chain: LLMChain,
        global_num_map: Dict[Tuple[str, int], int],
    ) -> str:
        """生成单个 Agent 的 timing 面板"""
        timings = agent_group["timings"]
        if not timings:
            return ""

        # 构建该 Agent 的 response_map
        session_id = agent_group["session_id"]
        agent_requests = [r for r in chain.requests if r.session_id == session_id]
        agent_responses = [r for r in chain.responses if r.session_id == session_id]

        paired: Dict[Tuple[str, int], Dict] = {}
        for req in agent_requests:
            key = (req.session_id, req.iteration)
            if key not in paired:
                paired[key] = {"timestamp": req.timestamp, "response": None}
        for resp in agent_responses:
            key = (resp.session_id, resp.iteration)
            if key not in paired:
                paired[key] = {"timestamp": resp.timestamp, "response": resp}
            else:
                paired[key]["response"] = resp
                if paired[key]["timestamp"] == 0:
                    paired[key]["timestamp"] = resp.timestamp

        sorted_items = sorted(paired.values(), key=lambda x: x["timestamp"])
        response_map: Dict[int, Optional[LLMResponse]] = {}
        for i, item in enumerate(sorted_items):
            response_map[i + 1] = item["response"]

        timing_items: List[str] = []
        for local_idx, timing in enumerate(timings):
            local_num = local_idx + 1
            global_num = timing.iteration_num
            resp = response_map.get(local_num)
            content = resp.content if resp else ""
            content_preview = content[:80] + "..." if len(content) > 80 else content
            if not content_preview:
                content_preview = "(no content)"

            total_seconds = timing.llm_call_duration + timing.tool_processing_duration

            item_html = TIMING_ITEM_TEMPLATE.format(
                local_num=local_num,
                global_num=global_num,
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
            total_iterations=len(timings),
            timing_list_id=f"timing-list-{agent_group['agent_key']}",
            timing_items_html="\n".join(timing_items),
        )

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
