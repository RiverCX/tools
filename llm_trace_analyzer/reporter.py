"""HTML报告生成器"""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import AnalysisResult, IterationTiming, LLMChain, LLMRequest, LLMResponse, SubagentInfo
from .templates import (
    AGENT_BLOCK_TEMPLATE,
    CONTENT_TEMPLATE,
    GANTT_BAR_TEMPLATE,
    GANTT_PANEL_TEMPLATE,
    INDEX_TEMPLATE,
    ITERATION_DETAIL_TEMPLATE,
    JSON_BLOCK_TEMPLATE,
    PARALLEL_GROUP_TEMPLATE,
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

        # Build shared state
        self._global_tool_name_map = {}
        for resp in chain.responses:
            if resp.tool_calls:
                for tc in resp.tool_calls:
                    tc_id = tc.get("id", "")
                    tc_name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                    if tc_id and tc_name:
                        self._global_tool_name_map[tc_id] = tc_name

        self._timing_map: Dict[int, Dict] = {}
        for timing in chain.iteration_timings:
            self._timing_map[timing.iteration_num] = {
                "llm_duration": timing.llm_call_duration,
                "tool_duration": timing.tool_processing_duration,
            }

        # Build global numbering
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

        sorted_items = sorted(paired_items.values(), key=lambda x: x["timestamp"])
        self._global_num_map: Dict[Tuple[str, int], int] = {}
        for i, item in enumerate(sorted_items):
            req = item["request"]
            resp = item["response"]
            key = (req.session_id, req.iteration) if req else (resp.session_id, resp.iteration)
            self._global_num_map[key] = i + 1

        # Build parent-child map for subagents
        self._children_by_session: Dict[str, List] = {}
        for sa in chain.subagents:
            parent_sid = self._get_parent_session_id(sa.session_id, chain)
            if parent_sid not in self._children_by_session:
                self._children_by_session[parent_sid] = []
            self._children_by_session[parent_sid].append(sa)

        # Render main flow
        iterations_html = self._render_agent_flow(chain.session_id, chain)

        # Render Gantt timeline and timing list
        gantt_html = self._generate_gantt_html(chain) if chain.subagents else ""
        timing_list_html = self._generate_timing_list_html(chain)

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
            timing_list_html=timing_list_html,
            iterations_html=iterations_html,
        )

        with open(detail_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_gantt_html(self, chain: LLMChain) -> str:
        """生成交替式 Gantt 时间线：Parent 行与 SubAgent 行交替显示"""
        if not chain.iteration_timings:
            return ""

        session_start = chain.start_time
        session_end = chain.end_time
        total_span = max(session_end - session_start, 0.001)

        # 按 session_id 分组 timings
        timings_by_session: Dict[str, List] = {}
        for t in chain.iteration_timings:
            if t.session_id not in timings_by_session:
                timings_by_session[t.session_id] = []
            timings_by_session[t.session_id].append(t)

        parent_timings = timings_by_session.get(chain.session_id, [])
        if not parent_timings:
            return ""

        # 构建 parent → children 映射
        children_map: Dict[str, List] = {}
        for sa in chain.subagents:
            p = sa.parent_session_id
            if p not in children_map:
                children_map[p] = []
            children_map[p].append(sa)
        for p in children_map:
            children_map[p].sort(key=lambda s: s.start_time)

        # 找到 parent 的 spawn 点（parent response 后有 child 开始）
        spawn_groups: List[Tuple[float, List]] = []
        direct_children = children_map.get(chain.session_id, [])
        if direct_children:
            # 按 spawn 时间分组（1s 内的视为同一组）
            current_group = [direct_children[0]]
            for sa in direct_children[1:]:
                if sa.start_time - current_group[-1].start_time < 1.0:
                    current_group.append(sa)
                else:
                    spawn_groups.append((current_group[0].start_time, current_group))
                    current_group = [sa]
            spawn_groups.append((current_group[0].start_time, current_group))

        # 构建交替时间线
        rows: List[str] = []

        def render_parent_window(win_start: float, win_end: float, label_suffix: str = ""):
            """渲染一个 Parent 时间窗口行"""
            window_timings = [
                t for t in parent_timings
                if t.request_timestamp >= win_start - 0.5 and t.response_timestamp <= win_end + 0.5
            ]
            if not window_timings:
                # 没有 parent 迭代，只显示 wait 段
                bar_left = ((win_start - session_start) / total_span) * 100
                bar_width = max(((win_end - win_start) / total_span) * 100, 0.5)
                rows.append(self._gantt_row_html(
                    label=f"Parent {label_suffix}",
                    tree_prefix="",
                    depth=0,
                    left_pct=bar_left,
                    width_pct=bar_width,
                    segments_html=f'<div class="gantt-seg gantt-seg-wait" style="width:100%"></div>',
                    first_global=parent_timings[0].iteration_num,
                    tooltip_data=self._parent_tooltip_data(parent_timings, win_start, win_end),
                ))
                return

            first_global = window_timings[0].iteration_num
            agent_start = window_timings[0].request_timestamp
            agent_end = max(t.response_timestamp for t in window_timings)
            bar_left_ts = min(win_start, agent_start)
            bar_right_ts = max(win_end, agent_end)
            bar_left = ((bar_left_ts - session_start) / total_span) * 100
            bar_width = max(((bar_right_ts - bar_left_ts) / total_span) * 100, 0.5)
            agent_span = max(bar_right_ts - bar_left_ts, 0.001)

            # 构建段：LLM + wait（填充到窗口边界）
            events: List[Tuple[float, float, str]] = []
            for t in window_timings:
                events.append((t.request_timestamp, t.response_timestamp, "llm"))

            sorted_llm = sorted(events, key=lambda e: e[0])
            # 在 LLM 之间加 wait 段
            for i in range(len(sorted_llm) - 1):
                gap_start = sorted_llm[i][1]
                gap_end = sorted_llm[i + 1][0]
                if gap_end > gap_start + 0.5:
                    events.append((gap_start, gap_end, "wait"))

            # 在窗口首尾加 wait 段
            if sorted_llm[0][0] > win_start + 0.5:
                events.append((win_start, sorted_llm[0][0], "wait"))
            last_end = max(e[1] for e in sorted_llm)
            if win_end > last_end + 0.5:
                events.append((last_end, win_end, "wait"))

            all_events = sorted(events, key=lambda e: e[0])
            segments: List[str] = []
            for start, end, etype in all_events:
                w = max(((end - start) / agent_span) * 100, 0.3)
                segments.append(f'<div class="gantt-seg gantt-seg-{etype}" style="width:{w:.2f}%"></div>')

            rows.append(self._gantt_row_html(
                label=f"Parent {label_suffix}",
                tree_prefix="",
                depth=0,
                left_pct=bar_left,
                width_pct=bar_width,
                segments_html="".join(segments),
                first_global=first_global,
                tooltip_data=self._parent_tooltip_data(window_timings, win_start, win_end),
            ))

        def render_subagent_row(sa, depth: int, is_last: List[bool]):
            """渲染一个 SubAgent 行"""
            sa_timings = timings_by_session.get(sa.session_id, [])
            if not sa_timings:
                return

            prefix_parts = []
            for i, last in enumerate(is_last[:-1]):
                prefix_parts.append("    " if last else "│   ")
            if is_last:
                prefix_parts.append("└─ " if is_last[-1] else "├─ ")
            tree_prefix = "".join(prefix_parts)

            label = sa.chain_path[-1] if sa.chain_path else self._short_session_id(sa.session_id)
            agent_start = sa.start_time
            agent_end = sa.end_time
            agent_span = max(agent_end - agent_start, 0.001)
            bar_left = ((agent_start - session_start) / total_span) * 100
            bar_width = max(((agent_end - agent_start) / total_span) * 100, 0.5)

            segments: List[str] = []
            for t in sa_timings:
                llm_w = max((t.llm_call_duration / agent_span) * 100, 0.3)
                tool_w = max((t.tool_processing_duration / agent_span) * 100, 0)
                segments.append(f'<div class="gantt-seg gantt-seg-llm" style="width:{llm_w:.2f}%"></div>')
                if tool_w > 0.1:
                    segments.append(f'<div class="gantt-seg gantt-seg-tool" style="width:{tool_w:.2f}%"></div>')

            rows.append(self._gantt_row_html(
                label=label,
                tree_prefix=tree_prefix,
                depth=depth,
                left_pct=bar_left,
                width_pct=bar_width,
                segments_html="".join(segments),
                first_global=sa_timings[0].iteration_num,
                tooltip_data=self._agent_tooltip_data(sa_timings, label),
            ))

            # 递归渲染子 agent
            children = children_map.get(sa.session_id, [])
            for i, child in enumerate(children):
                render_subagent_row(child, depth + 1, is_last + [i == len(children) - 1])

        # 构建交替序列
        if not spawn_groups:
            # 无 subagent，只显示一个 Parent 行
            render_parent_window(session_start, session_end)
        else:
            # Parent 窗口 1：session_start → 第一个 spawn
            render_parent_window(session_start, spawn_groups[0][0], "")

            for gi, (spawn_time, group) in enumerate(spawn_groups):
                # SubAgent 行
                for i, sa in enumerate(group):
                    render_subagent_row(sa, 1, [i == len(group) - 1])

                # 下一个 Parent 窗口
                window_start = max(sa.end_time for sa in group)
                window_end = spawn_groups[gi + 1][0] if gi + 1 < len(spawn_groups) else session_end
                if window_end > window_start + 0.5:
                    render_parent_window(window_start, window_end, "")

        return GANTT_PANEL_TEMPLATE.format(
            agent_count=len(rows),
            total_duration=self._format_duration(session_end - session_start),
            gantt_bars_html="\n".join(rows),
        )

    def _gantt_row_html(self, label, tree_prefix, depth, left_pct, width_pct, segments_html, first_global, tooltip_data) -> str:
        depth_class = "parent" if depth == 0 else str(min(depth - 1, 2))
        data_attrs = " ".join(f'data-{k}="{html.escape(str(v))}"' for k, v in tooltip_data.items())
        return (
            f'<div class="gantt-row">'
            f'<div class="gantt-label" style="padding-left:{depth * 16}px">'
            f'<span class="gantt-tree">{html.escape(tree_prefix)}</span>'
            f'{html.escape(label)}'
            f'</div>'
            f'<div class="gantt-track">'
            f'<div class="gantt-bar depth-{depth_class}" '
            f'style="left:{left_pct:.1f}%;width:{width_pct:.1f}%" '
            f'data-first-global="{first_global}" {data_attrs} '
            f'onclick="jumpToIteration({first_global})" '
            f'onmouseenter="showGanttTooltip(event, this)" '
            f'onmousemove="moveGanttTooltip(event)" '
            f'onmouseleave="hideGanttTooltip()">'
            f'{segments_html}'
            f'</div></div></div>'
        )

    def _parent_tooltip_data(self, timings, win_start, win_end):
        llm = sum(t.llm_call_duration for t in timings)
        tool = sum(t.tool_processing_duration for t in timings)
        total = llm + tool
        llm_pct = (llm / total * 100) if total > 0 else 0
        tool_pct = (tool / total * 100) if total > 0 else 0
        return {
            "agent-name": "Parent",
            "iter-count": str(len(timings)),
            "llm": self._format_duration(llm),
            "tool": self._format_duration(tool),
            "total": self._format_duration(total),
            "llm-pct": f"{llm_pct:.1f}",
            "tool-pct": f"{tool_pct:.1f}",
            "time-range": f"{self._format_timestamp(win_start)} - {self._format_timestamp(win_end)}",
        }

    def _agent_tooltip_data(self, timings, label):
        llm = sum(t.llm_call_duration for t in timings)
        tool = sum(t.tool_processing_duration for t in timings)
        total = llm + tool
        llm_pct = (llm / total * 100) if total > 0 else 0
        tool_pct = (tool / total * 100) if total > 0 else 0
        start = timings[0].request_timestamp
        end = max(t.response_timestamp for t in timings)
        return {
            "agent-name": label,
            "iter-count": str(len(timings)),
            "llm": self._format_duration(llm),
            "tool": self._format_duration(tool),
            "total": self._format_duration(total),
            "llm-pct": f"{llm_pct:.1f}",
            "tool-pct": f"{tool_pct:.1f}",
            "time-range": f"{self._format_timestamp(start)} - {self._format_timestamp(end)}",
        }

    def _generate_timing_list_html(self, chain: LLMChain) -> str:
        """生成全局 timing 面板"""
        if not chain.iteration_timings:
            return ""

        # 构建 response_map（使用配对逻辑）
        paired_items: Dict[Tuple[str, int], Dict] = {}
        for req in chain.requests:
            key = (req.session_id, req.iteration)
            if key not in paired_items:
                paired_items[key] = {"timestamp": req.timestamp, "response": None}
        for resp in chain.responses:
            key = (resp.session_id, resp.iteration)
            if key not in paired_items:
                paired_items[key] = {"timestamp": resp.timestamp, "response": resp}
            else:
                paired_items[key]["response"] = resp
                if paired_items[key]["timestamp"] == 0:
                    paired_items[key]["timestamp"] = resp.timestamp

        sorted_items = sorted(paired_items.values(), key=lambda x: x["timestamp"])
        response_map: Dict[int, Optional[LLMResponse]] = {}
        for i, item in enumerate(sorted_items):
            response_map[i + 1] = item["response"]

        timing_items: List[str] = []
        for timing in chain.iteration_timings:
            resp = response_map.get(timing.iteration_num)
            content = resp.content if resp else ""
            content_preview = content[:80] + "..." if len(content) > 80 else content
            if not content_preview:
                content_preview = "(no content)"

            total_seconds = timing.llm_call_duration + timing.tool_processing_duration

            item_html = TIMING_ITEM_TEMPLATE.format(
                local_num=timing.iteration_num,
                global_num=timing.iteration_num,
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
            timing_list_id="timing-list-global",
            timing_items_html="\n".join(timing_items),
        )

    def _get_parent_session_id(self, session_id: str, chain: LLMChain) -> str:
        """从 session_id 推断直接 parent 的 session_id"""
        if "_fork_agent_" in session_id:
            parts = session_id.split("_fork_agent_")
            partial_parent = parts[0]
            # 找到完整匹配的 session
            all_sessions = {r.session_id for r in chain.requests} | {r.session_id for r in chain.responses}
            for sid in all_sessions:
                if sid == partial_parent or sid.endswith(partial_parent):
                    return sid
            return partial_parent
        if "_subagent_" in session_id:
            parts = session_id.split("_subagent_")
            return parts[0]
        return chain.session_id

    def _render_agent_flow(self, session_id: str, chain: LLMChain) -> str:
        """渲染一个 Agent 的完整流程：迭代 + 内嵌的 subAgent 块"""
        # 获取该 session 的请求和响应
        reqs = sorted([r for r in chain.requests if r.session_id == session_id], key=lambda r: r.timestamp)
        resps = sorted([r for r in chain.responses if r.session_id == session_id], key=lambda r: r.timestamp)

        # 按 iteration 配对
        paired: Dict[int, Dict] = {}
        for req in reqs:
            if req.iteration not in paired:
                paired[req.iteration] = {"request": None, "response": None, "timestamp": 0}
            paired[req.iteration]["request"] = req
            paired[req.iteration]["timestamp"] = req.timestamp
        for resp in resps:
            if resp.iteration not in paired:
                paired[resp.iteration] = {"request": None, "response": None, "timestamp": 0}
            paired[resp.iteration]["response"] = resp
            if paired[resp.iteration]["timestamp"] == 0:
                paired[resp.iteration]["timestamp"] = resp.timestamp

        sorted_iters = sorted(paired.keys(), key=lambda k: paired[k]["timestamp"])

        # 获取该 session 的直接子 Agent
        children = self._children_by_session.get(session_id, [])
        children_by_spawn: Dict[int, List] = {}
        if children:
            # 按 spawn 时间匹配到 parent response
            for child in sorted(children, key=lambda s: s.start_time):
                spawn_idx = -1
                for i, iter_key in enumerate(sorted_iters):
                    resp = paired[iter_key]["response"]
                    if resp and resp.timestamp <= child.start_time:
                        spawn_idx = i
                if spawn_idx >= 0:
                    iter_key = sorted_iters[spawn_idx]
                    if iter_key not in children_by_spawn:
                        children_by_spawn[iter_key] = []
                    children_by_spawn[iter_key].append(child)

        # 渲染流程
        parts: List[str] = []
        prev_request: Optional[LLMRequest] = None

        for local_idx, iter_key in enumerate(sorted_iters):
            local_num = local_idx + 1
            item = paired[iter_key]
            req = item["request"]
            resp = item["response"]

            key = (req.session_id, req.iteration) if req else (resp.session_id, resp.iteration)
            global_num = self._global_num_map.get(key, 0)

            timing_info = self._timing_map.get(global_num, {})
            llm_duration_str = self._format_duration(timing_info.get("llm_duration", 0))
            tool_duration_str = self._format_duration(timing_info.get("tool_duration", 0))

            request_html = ""
            body_id = ""
            body_json = ""
            copy_body_btn = ""

            if req:
                is_first = prev_request is None and req.source == "subagent"
                request_html = self._generate_request_html(
                    req, prev_request, self._global_tool_name_map, is_first
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
                depth=0,
                depth_indicator="",
                llm_duration=llm_duration_str,
                tool_duration=tool_duration_str,
                copy_body_btn=copy_body_btn,
                body_id=body_id,
                body_json=body_json,
                request_html=request_html,
                response_html=response_html,
            )
            parts.append(iteration_html)

            # 在此迭代后插入 subAgent 块
            if iter_key in children_by_spawn:
                spawn_children = children_by_spawn[iter_key]
                if len(spawn_children) == 1:
                    parts.append(self._render_subagent_block(spawn_children[0], chain))
                else:
                    parts.append(self._render_parallel_group(spawn_children, chain))

        return "\n".join(parts)

    def _render_subagent_block(self, subagent, chain: LLMChain) -> str:
        """渲染单个 subAgent 的折叠块"""
        depth_class = str(min(subagent.depth, 2))
        label = subagent.chain_path[-1] if subagent.chain_path else self._short_session_id(subagent.session_id)
        duration = self._format_duration(subagent.end_time - subagent.start_time)

        # 递归渲染 subAgent 的流程
        content_html = self._render_agent_flow(subagent.session_id, chain)

        return AGENT_BLOCK_TEMPLATE.format(
            depth_class=depth_class,
            label=label,
            iteration_count=len([r for r in chain.requests if r.session_id == subagent.session_id]),
            duration=duration,
            content_html=content_html,
        )

    def _render_parallel_group(self, subagents: List, chain: LLMChain) -> str:
        """渲染并行 subAgent 组的 Tab 页"""
        min_start = min(s.start_time for s in subagents)
        max_end = max(s.end_time for s in subagents)
        duration = self._format_duration(max_end - min_start)
        depth_class = str(min(subagents[0].depth, 2))

        # 生成 Tab 按钮
        buttons: List[str] = []
        panels: List[str] = []
        for i, sa in enumerate(sorted(subagents, key=lambda s: s.start_time)):
            label = sa.chain_path[-1] if sa.chain_path else self._short_session_id(sa.session_id)
            agent_key = f"sa_{self._short_session_id(sa.session_id)}_{id(sa) % 10000}"
            active_class = " active" if i == 0 else ""
            iter_count = len([r for r in chain.requests if r.session_id == sa.session_id])

            buttons.append(TAB_BUTTON_TEMPLATE.format(
                agent_key=agent_key,
                label=label,
                iteration_count=iter_count,
                active_class=active_class,
            ))

            content_html = self._render_agent_flow(sa.session_id, chain)
            panels.append(TAB_PANEL_TEMPLATE.format(
                agent_key=agent_key,
                active_class=active_class,
                timing_list_html="",
                iterations_html=content_html,
            ))

        tab_nav_html = TAB_NAV_TEMPLATE.format(tab_buttons_html="\n".join(buttons))
        tab_content_html = TAB_CONTENT_WRAPPER_TEMPLATE.format(tab_panels_html="\n".join(panels))

        return PARALLEL_GROUP_TEMPLATE.format(
            agent_count=len(subagents),
            duration=duration,
            tab_nav_html=tab_nav_html,
            tab_content_html=tab_content_html,
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
