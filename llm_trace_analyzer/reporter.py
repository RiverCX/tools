"""HTML报告生成器"""

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .models import AnalysisResult, IterationTiming, LLMChain, LLMRequest, LLMResponse, SubagentInfo, build_global_num_map, pair_requests_responses
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
    def __init__(self, log_file_path: str):
        self.log_file_path = log_file_path
        self._id_counter = 0
        self._global_tool_name_map: Dict[str, str] = {}
        self._timing_map: Dict[int, Dict] = {}
        self._global_num_map: Dict[Tuple[str, int], int] = {}
        self._children_by_session: Dict[str, List] = {}

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
            total_input_tokens=stats.total_input_tokens,
            total_output_tokens=stats.total_output_tokens,
            total_tokens=stats.total_tokens,
            total_cache_tokens=stats.total_cache_tokens,
            session_rows="\n".join(session_rows),
            statistics_html=self._generate_global_statistics_html(result),
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
        sorted_items = pair_requests_responses(chain.requests, chain.responses)
        self._global_num_map = build_global_num_map(sorted_items)

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

        # Session 级别统计
        session_statistics_html = self._generate_session_statistics_html(chain)

        num_iters = len(chain.iteration_timings)
        avg_llm = chain.total_llm_duration_seconds / num_iters if num_iters > 0 else 0

        # 统计总迭代次数、模型调用次数、工具调用次数
        total_iterations = len(chain.iteration_timings)
        total_model_calls = total_iterations  # 每次迭代调用一次模型
        total_tool_calls = sum(len(resp.tool_calls) for resp in chain.responses if resp.tool_calls)

        # Session 级别 token 统计
        session_input_tokens = sum(resp.input_tokens for resp in chain.responses)
        session_output_tokens = sum(resp.output_tokens for resp in chain.responses)
        session_total_tokens = sum(resp.total_tokens for resp in chain.responses)
        session_cache_tokens = sum(resp.cache_tokens for resp in chain.responses)

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
            total_iterations_count=total_iterations,
            total_model_calls=total_model_calls,
            total_tool_calls=total_tool_calls,
            session_input_tokens=session_input_tokens,
            session_output_tokens=session_output_tokens,
            session_total_tokens=session_total_tokens,
            session_cache_tokens=session_cache_tokens,
            gantt_html=gantt_html,
            timing_list_html=timing_list_html,
            iterations_html=iterations_html,
            session_statistics_html=session_statistics_html,
        )

        with open(detail_file, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _generate_gantt_html(self, chain: LLMChain) -> str:
        """生成 Gantt 时间线：默认 agent 级别折叠 bar，展开后显示逐 iteration 细节"""
        if not chain.iteration_timings:
            return ""

        # 使用非零时间戳计算 session 范围，避免 timestamp=0 导致定位错误
        non_zero_starts = [t.request_timestamp for t in chain.iteration_timings if t.request_timestamp > 0]
        non_zero_ends = [t.response_timestamp for t in chain.iteration_timings if t.response_timestamp > 0]
        session_start = min(non_zero_starts) if non_zero_starts else chain.start_time
        session_end = max(non_zero_ends) if non_zero_ends else chain.end_time
        total_span = max(session_end - session_start, 0.001)

        # 按 session_id 分组 timings
        timings_by_session: Dict[str, List] = {}
        for t in chain.iteration_timings:
            if t.session_id not in timings_by_session:
                timings_by_session[t.session_id] = []
            timings_by_session[t.session_id].append(t)

        # 构建 session_id -> 显示名称
        sa_label_map: Dict[str, str] = {chain.session_id: "Main"}
        for sa in chain.subagents:
            label = sa.chain_path[-1] if sa.chain_path else self._short_session_id(sa.session_id)
            sa_label_map[sa.session_id] = label

        # 构建排序顺序（Main 穿插 subAgent，同 agent 连续）
        parent_timings = timings_by_session.get(chain.session_id, [])
        parent_resp_times = sorted(
            [(t.iteration_num, t.response_timestamp) for t in parent_timings],
            key=lambda x: x[1]
        )

        def find_spawn_parent(start_time: float) -> int:
            if start_time <= 0:
                return 0
            result = 0
            for pnum, pts in parent_resp_times:
                if pts <= start_time + 1.0:
                    result = pnum
                else:
                    break
            return result

        # 预计算每个 subAgent 的 spawn_parent（用首个非零时间戳）
        spawn_parent_by_session: Dict[str, int] = {}
        for timing in chain.iteration_timings:
            sid = timing.session_id
            if sid != chain.session_id and sid not in spawn_parent_by_session:
                if timing.request_timestamp > 0:
                    spawn_parent_by_session[sid] = find_spawn_parent(timing.request_timestamp)

        # 对仍无 spawn_parent 的 subAgent，找其首个非零 timing
        for sid in set(t.session_id for t in chain.iteration_timings if t.session_id != chain.session_id):
            if sid not in spawn_parent_by_session:
                non_zero = [t for t in chain.iteration_timings if t.session_id == sid and t.request_timestamp > 0]
                if non_zero:
                    spawn_parent_by_session[sid] = find_spawn_parent(non_zero[0].request_timestamp)
                else:
                    spawn_parent_by_session[sid] = 0

        # 按 spawn_parent 分组 subAgent
        subagent_groups: Dict[int, List[str]] = {}  # spawn_parent_global -> [session_ids]
        for sid, sp in spawn_parent_by_session.items():
            if sp not in subagent_groups:
                subagent_groups[sp] = []
            if sid not in subagent_groups[sp]:
                subagent_groups[sp].append(sid)

        # 将 Main 的 iterations 按 spawn 点切分成段
        main_timings = sorted(
            [t for t in chain.iteration_timings if t.session_id == chain.session_id],
            key=lambda t: t.iteration_num
        )
        # spawn 点：哪些 Main iteration 后面有 subAgent
        # 合并连续的 spawn_points（如 12,13 → 只保留 13），避免把连续 Main 迭代拆碎
        raw_spawn_points = sorted(subagent_groups.keys())
        spawn_points = []
        for i, sp in enumerate(raw_spawn_points):
            if i + 1 < len(raw_spawn_points) and raw_spawn_points[i + 1] == sp + 1:
                continue  # 下一个是连续的，跳过当前
            spawn_points.append(sp)

        # 构建 Main 分段
        main_segments: List[Tuple[str, List]] = []  # (segment_id, [timings])
        prev_end = 0
        seg_idx = 0
        for sp in spawn_points:
            seg_timings = [t for t in main_timings if prev_end < t.iteration_num <= sp]
            if seg_timings:
                main_segments.append((f"__main_seg_{seg_idx}__", seg_timings))
                seg_idx += 1
            prev_end = sp
        # 最后一段
        remaining = [t for t in main_timings if t.iteration_num > prev_end]
        if remaining:
            main_segments.append((f"__main_seg_{seg_idx}__", remaining))
        if not main_segments and main_timings:
            main_segments.append((f"__main_seg_0__", main_timings))

        # 构建交替序列：main_seg, sub_group, main_seg, sub_group, ...
        # 用 (sort_key, type, id, timings) 表示每个条目
        timeline_entries: List[Tuple[int, str, str, List]] = []
        prev_seg_end = 0
        for seg_id, seg_timings in main_segments:
            last_global = seg_timings[-1].iteration_num
            timeline_entries.append((last_global, 0, seg_id, seg_timings))
            # 收集这个 Main 段之后所有 spawn 的 subAgent（包括被合并的 spawn point）
            for sp in raw_spawn_points:
                if prev_seg_end < sp <= last_global:
                    for sub_sid in sorted(subagent_groups[sp]):
                        sub_t = [t for t in chain.iteration_timings if t.session_id == sub_sid]
                        timeline_entries.append((last_global, 1, sub_sid, sub_t))
            prev_seg_end = last_global

        # 按 (sort_key, type) 排序：同 sort_key 下 Main(0) 在 SubAgent(1) 之前
        timeline_entries.sort(key=lambda x: (x[0], x[1]))

        # 处理没有 spawn 点的 subAgent（spawn_parent=0 或不在 spawn_points 中）
        handled_subs = set()
        for _, _, sid, _ in timeline_entries:
            if not sid.startswith("__"):
                handled_subs.add(sid)
        for sid, sp in spawn_parent_by_session.items():
            if sid not in handled_subs:
                sub_t = [t for t in chain.iteration_timings if t.session_id == sid]
                timeline_entries.append((sp, 1, sid, sub_t))
        timeline_entries.sort(key=lambda x: (x[0], x[1]))

        # 生成行
        rows: List[str] = []
        row_counter = 0
        main_seg_counter = 0

        for group_idx, (sort_key, entry_type, sid, agent_timings) in enumerate(timeline_entries):
            row_counter += 1
            expand_id = f"gantt-expand-{row_counter}"

            is_main_seg = sid.startswith("__main_seg_")
            is_main = is_main_seg or sid == chain.session_id

            if is_main_seg:
                agent_label = f"Main #{main_seg_counter + 1}"
                main_seg_counter += 1
            else:
                agent_label = sa_label_map.get(sid, self._short_session_id(sid))

            lookup_sid = chain.session_id if is_main_seg else sid

            # === Agent 级别摘要 bar ===
            if agent_timings:
                # 使用非零时间戳计算位置
                valid_starts = [t.request_timestamp for t in agent_timings if t.request_timestamp > 0]
                valid_ends = [t.response_timestamp + (t.tool_processing_duration or 0)
                              for t in agent_timings if t.response_timestamp > 0]
                if valid_starts and valid_ends:
                    a_start = min(valid_starts)
                    a_end = max(valid_ends)
                    a_span = max(a_end - a_start, 0.001)
                    bar_left = max(((a_start - session_start) / total_span) * 100, 0)
                    bar_width = max(((a_end - a_start) / total_span) * 100, 0.5)

                    # 构建 LLM + Tool 段
                    segments: List[str] = []
                    for t in agent_timings:
                        llm_w = max((t.llm_call_duration / a_span) * 100, 0.3)
                        segments.append(f'<div class="gantt-seg gantt-seg-llm" style="width:{llm_w:.2f}%"></div>')
                        if t.tool_processing_duration > 0:
                            tool_w = max((t.tool_processing_duration / a_span) * 100, 0.8)
                            segments.append(f'<div class="gantt-seg gantt-seg-tool" style="width:{tool_w:.2f}%"></div>')

                    agent_resps = [r for r in chain.responses if r.session_id == lookup_sid]
                    tooltip = self._tooltip_data(agent_timings, agent_label, responses=agent_resps)
                    iter_count = len(agent_timings)

                    rows.append(self._gantt_row_html(
                        label=f"{agent_label} ({iter_count})",
                        tree_prefix="",
                        depth=0,
                        left_pct=bar_left,
                        width_pct=bar_width,
                        segments_html="".join(segments),
                        first_global=agent_timings[0].iteration_num,
                        tooltip_data=tooltip,
                        expandable_id=expand_id,
                    ))

            # === 展开内容：逐 iteration 细节行 ===
            # 构建该 agent 的 response 查找表（按 response_timestamp 匹配）
            resp_lookup: Dict[float, LLMResponse] = {}
            for r in chain.responses:
                if r.session_id == lookup_sid:
                    resp_lookup[round(r.timestamp, 3)] = r

            detail_rows: List[str] = []
            for local_idx, timing in enumerate(agent_timings):
                local_num = local_idx + 1

                iter_start = timing.request_timestamp
                iter_end = timing.response_timestamp
                tool_end = iter_end + (timing.tool_processing_duration or 0)
                bar_end = max(tool_end, iter_end)
                iter_span = max(bar_end - iter_start, 0.001)

                # 处理 timestamp=0 的情况
                if iter_start <= 0:
                    i_left = 0
                    i_width = 0.3
                else:
                    i_left = max(((iter_start - session_start) / total_span) * 100, 0)
                    i_width = max(((bar_end - iter_start) / total_span) * 100, 0.3)

                llm_w = max((timing.llm_call_duration / iter_span) * 100, 0.5)
                segs = [f'<div class="gantt-seg gantt-seg-llm" style="width:{llm_w:.1f}%"></div>']
                if timing.tool_processing_duration > 0:
                    tool_w = max((timing.tool_processing_duration / iter_span) * 100, 0.8)
                    segs.append(f'<div class="gantt-seg gantt-seg-tool" style="width:{tool_w:.1f}%"></div>')

                # 构建标签：#N + tool calls + content 摘要
                label_text = f"#{local_num}"
                full_content = ""
                full_tool_calls = ""
                resp = resp_lookup.get(round(timing.response_timestamp, 3))
                if resp:
                    # Tool call 名称
                    if resp.tool_calls:
                        tc_names = []
                        for tc in resp.tool_calls:
                            name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                            if name:
                                tc_names.append(name)
                        if tc_names:
                            label_text += f'  {", ".join(tc_names[:3])}'
                            if len(tc_names) > 3:
                                label_text += f"+{len(tc_names)-3}"
                            full_tool_calls = ", ".join(tc_names)
                    # Content 摘要
                    if resp.content:
                        full_content = resp.content
                        preview = resp.content[:40].replace("\n", " ").strip()
                        if len(resp.content) > 40:
                            preview += "..."
                        label_text += f'  {preview}'

                # LLM/Tool 百分比
                iter_total = timing.llm_call_duration + timing.tool_processing_duration
                llm_pct = (timing.llm_call_duration / iter_total * 100) if iter_total > 0 else 0
                tool_pct = (timing.tool_processing_duration / iter_total * 100) if iter_total > 0 else 0

                # 字数统计
                reasoning_chars = len(resp.reasoning_content or "") if resp else 0
                content_chars = len(resp.content or "") if resp else 0
                tc_chars = 0
                if resp and resp.tool_calls:
                    tc_chars = len(json.dumps(resp.tool_calls, ensure_ascii=False))

                detail_tooltip = {
                    "agent-name": f"{agent_label} #{local_num}",
                    "iter-count": "1",
                    "llm": self._format_duration(timing.llm_call_duration),
                    "tool": self._format_duration(timing.tool_processing_duration),
                    "total": self._format_duration(iter_total),
                    "llm-pct": f"{llm_pct:.1f}",
                    "tool-pct": f"{tool_pct:.1f}",
                    "time-range": f"{self._format_timestamp(iter_start)} - {self._format_timestamp(bar_end)}",
                    "full-content": full_content,
                    "tool-calls": full_tool_calls,
                    "reasoning-chars": str(reasoning_chars),
                    "content-chars": str(content_chars),
                    "tool-calls-chars": str(tc_chars),
                    "input-tokens": str(resp.input_tokens if resp else 0),
                    "output-tokens": str(resp.output_tokens if resp else 0),
                    "total-tokens": str(resp.total_tokens if resp else 0),
                    "cache-tokens": str(resp.cache_tokens if resp else 0),
                }

                detail_rows.append(self._gantt_row_html(
                    label=label_text,
                    label_title=full_content,
                    tree_prefix="",
                    depth=0,
                    left_pct=i_left,
                    width_pct=i_width,
                    segments_html="".join(segs),
                    first_global=timing.iteration_num,
                    tooltip_data=detail_tooltip,
                ))

            rows.append(f'<div class="gantt-expand-content" id="{expand_id}" style="display:none">')
            rows.extend(detail_rows)
            rows.append('</div>')

        return GANTT_PANEL_TEMPLATE.format(
            agent_count=len(timeline_entries),
            total_duration=self._format_duration(session_end - session_start),
            gantt_bars_html="\n".join(rows),
        )

    def _build_segments(self, timings: List, span_start: float, span_end: float, is_parent: bool = False) -> str:
        """构建 LLM/Tool 段的 HTML"""
        if not timings:
            return ""

        intervals: List[Tuple[float, float, str]] = []
        for t in timings:
            intervals.append((t.request_timestamp, t.response_timestamp, "llm"))
            if t.tool_processing_duration > 0:
                tool_end = min(t.response_timestamp + t.tool_processing_duration, span_end)
                intervals.append((t.response_timestamp, tool_end, "tool"))

        intervals.sort(key=lambda x: x[0])
        agent_span = max(span_end - span_start, 0.001)

        segments: List[str] = []
        for start, end, seg_type in intervals:
            min_w = 0.8 if seg_type == "tool" else 0.3
            w = max(((end - start) / agent_span) * 100, min_w)
            segments.append(f'<div class="gantt-seg gantt-seg-{seg_type}" style="width:{w:.2f}%"></div>')
        return "".join(segments)

    def _build_spawn_groups(self, chain: LLMChain) -> List[Tuple[float, List]]:
        """构建 parent 的 spawn 分组"""
        direct_children = self._children_by_session.get(chain.session_id, [])
        if not direct_children:
            return []

        spawn_groups: List[Tuple[float, List]] = []
        current_group = [direct_children[0]]
        for sa in direct_children[1:]:
            if sa.start_time - current_group[-1].start_time < 1.0:
                current_group.append(sa)
            else:
                spawn_groups.append((current_group[0].start_time, current_group))
                current_group = [sa]
        spawn_groups.append((current_group[0].start_time, current_group))
        return spawn_groups

    def _gantt_row_html(
        self, label: str, tree_prefix: str, depth: int,
        left_pct: float, width_pct: float, segments_html: str,
        first_global: int, tooltip_data: Dict,
        expandable_id: str = "",
        label_title: str = "",
    ) -> str:
        depth_class = "parent" if depth == 0 else str(min(depth - 1, 2))
        data_attrs = " ".join(f'data-{k}="{html.escape(str(v))}"' for k, v in tooltip_data.items())
        expand_btn = ""
        if expandable_id:
            expand_btn = (
                f'<button class="gantt-expand-btn" '
                f'onclick="event.stopPropagation();toggleGanttExpand(\'{expandable_id}\', this)" '
                f'title="展开详情">&#9654;</button>'
            )
        title_attr = f' title="{html.escape(label_title)}"' if label_title else ""
        return (
            f'<div class="gantt-row">'
            f'<div class="gantt-label" style="padding-left:{depth * 16}px"{title_attr}>'
            f'{expand_btn}'
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

    def _tooltip_data(self, timings, label: str, start_ts: float = 0, end_ts: float = 0,
                      responses: List = None) -> Dict:
        llm = sum(t.llm_call_duration for t in timings)
        tool = sum(t.tool_processing_duration for t in timings)
        total = llm + tool
        llm_pct = (llm / total * 100) if total > 0 else 0
        tool_pct = (tool / total * 100) if total > 0 else 0
        if not start_ts and timings:
            start_ts = timings[0].request_timestamp
        if not end_ts and timings:
            end_ts = max(t.response_timestamp for t in timings)

        # 计算字数统计
        reasoning_chars = 0
        content_chars = 0
        tool_calls_chars = 0
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0
        cache_tokens = 0
        if responses:
            for r in responses:
                reasoning_chars += len(r.reasoning_content or "")
                content_chars += len(r.content or "")
                if r.tool_calls:
                    import json as _json
                    tool_calls_chars += len(_json.dumps(r.tool_calls, ensure_ascii=False))
                input_tokens += r.input_tokens
                output_tokens += r.output_tokens
                total_tokens += r.total_tokens
                cache_tokens += r.cache_tokens

        return {
            "agent-name": label,
            "iter-count": str(len(timings)),
            "llm": self._format_duration(llm),
            "tool": self._format_duration(tool),
            "total": self._format_duration(total),
            "llm-pct": f"{llm_pct:.1f}",
            "tool-pct": f"{tool_pct:.1f}",
            "time-range": f"{self._format_timestamp(start_ts)} - {self._format_timestamp(end_ts)}",
            "reasoning-chars": str(reasoning_chars),
            "content-chars": str(content_chars),
            "tool-calls-chars": str(tool_calls_chars),
            "input-tokens": str(input_tokens),
            "output-tokens": str(output_tokens),
            "total-tokens": str(total_tokens),
            "cache-tokens": str(cache_tokens),
        }

    def _generate_timing_list_html(self, chain: LLMChain) -> str:
        """生成全局 timing 面板"""
        if not chain.iteration_timings:
            return ""

        # 构建配对 + 按 session 分组计算本地编号
        sorted_items = pair_requests_responses(chain.requests, chain.responses)

        # 构建 session_id -> 显示名称
        sa_label_map: Dict[str, str] = {chain.session_id: "Main"}
        for sa in chain.subagents:
            label = sa.chain_path[-1] if sa.chain_path else self._short_session_id(sa.session_id)
            sa_label_map[sa.session_id] = label

        # 一次遍历：分配 global_num、local_num、收集 response
        global_data: Dict[int, Dict] = {}
        session_counters: Dict[str, int] = {}
        for i, item in enumerate(sorted_items):
            req = item["request"]
            resp = item["response"]
            sid = req.session_id if req else resp.session_id
            if sid not in session_counters:
                session_counters[sid] = 0
            session_counters[sid] += 1
            global_data[i + 1] = {
                "response": resp,
                "local_num": session_counters[sid],
                "agent_label": sa_label_map.get(sid, self._short_session_id(sid)),
            }

        # 按 session 分组 timing
        timings_by_session: Dict[str, List] = {}
        for timing in chain.iteration_timings:
            if timing.session_id not in timings_by_session:
                timings_by_session[timing.session_id] = []
            timings_by_session[timing.session_id].append(timing)

        # 找到每个 subagent 被哪个 parent 迭代 spawn（通过 start_time 匹配 parent response）
        parent_timings = timings_by_session.get(chain.session_id, [])
        parent_resp_times = sorted(
            [(t.iteration_num, t.response_timestamp) for t in parent_timings],
            key=lambda x: x[1]
        )

        def find_spawn_parent(start_time: float) -> int:
            """找到 spawn 该 subagent 的 parent 迭代的 global_num"""
            result = 0
            for pnum, pts in parent_resp_times:
                if pts <= start_time + 1.0:
                    result = pnum
                else:
                    break
            return result

        # 构建排序 key：(spawn_parent_global_num, is_subagent, session_id, local_num)
        # 这样 subagent 会紧跟在 spawn 它的 parent 迭代之后，同 session 连续
        sort_entries: List[Tuple] = []
        for timing in chain.iteration_timings:
            data = global_data.get(timing.iteration_num, {})
            local_num = data.get("local_num", timing.iteration_num)
            if timing.session_id == chain.session_id:
                # Main: 按 global_num 排序
                sort_entries.append((timing.iteration_num, 0, "", local_num, timing))
            else:
                # SubAgent: 按 spawn parent 排序，同 parent 的按 session_id 分组
                spawn_parent = find_spawn_parent(timing.request_timestamp)
                sort_entries.append((spawn_parent, 1, timing.session_id, local_num, timing))

        sort_entries.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
        ordered_timings = [entry[4] for entry in sort_entries]

        timing_items: List[str] = []
        for timing in ordered_timings:
            data = global_data.get(timing.iteration_num, {})
            resp = data.get("response")
            local_num = data.get("local_num", timing.iteration_num)
            agent_label = data.get("agent_label", "Unknown")

            content = resp.content if resp else ""
            content_preview = content[:80] + "..." if len(content) > 80 else content
            if not content_preview:
                content_preview = "(no content)"

            # 提取 tool call 名称
            tool_names = ""
            if resp and resp.tool_calls:
                names = []
                for tc in resp.tool_calls:
                    name = tc.get("name", "") or tc.get("function", {}).get("name", "")
                    if name:
                        names.append(name)
                tool_names = ", ".join(names)

            total_seconds = timing.llm_call_duration + timing.tool_processing_duration

            item_html = TIMING_ITEM_TEMPLATE.format(
                agent_label=html.escape(agent_label),
                local_num=local_num,
                global_num=timing.iteration_num,
                llm_seconds=timing.llm_call_duration,
                tool_seconds=timing.tool_processing_duration,
                total_seconds=total_seconds,
                llm_duration=self._format_duration(timing.llm_call_duration),
                tool_duration=self._format_duration(timing.tool_processing_duration),
                total_duration=self._format_duration(total_seconds),
                tool_names=html.escape(tool_names),
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
            # Iteration 级别 token 统计
            iter_input_tokens = 0
            iter_output_tokens = 0
            iter_total_tokens = 0
            if resp:
                response_html = self._generate_response_html(resp)
                iter_input_tokens = resp.input_tokens
                iter_output_tokens = resp.output_tokens
                iter_total_tokens = resp.total_tokens

            iteration_html = ITERATION_DETAIL_TEMPLATE.format(
                local_num=local_num,
                global_num=global_num,
                depth=0,
                depth_indicator="",
                llm_duration=llm_duration_str,
                tool_duration=tool_duration_str,
                iter_input_tokens=iter_input_tokens,
                iter_output_tokens=iter_output_tokens,
                iter_total_tokens=iter_total_tokens,
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

    def _generate_global_statistics_html(self, result: AnalysisResult) -> str:
        """生成 index 页面的统计面板 HTML"""
        stats = result.statistics
        parts: List[str] = []

        # 概览卡片
        parts.append('<div class="stat-cards">')
        overview = [
            (stats.total_sessions, "Sessions"),
            (stats.total_iterations, "Iterations"),
            (self._format_duration(stats.total_llm_time_seconds), "LLM Total"),
            (self._format_duration(stats.total_tool_time_seconds), "Tool Total"),
            (f"{stats.total_tokens:,}", "Total Tokens"),
        ]
        for val, label in overview:
            parts.append(f'<div class="stat-card"><div class="stat-value">{val}</div><div class="stat-label">{label}</div></div>')
        parts.append('</div>')

        # 工具调用统计
        if stats.tool_call_counts:
            max_count = max(stats.tool_call_counts.values())
            parts.append('<div class="stat-section">')
            parts.append("<h3>Tool Calls</h3>")
            avg_tool_per_call = stats.total_tool_time_seconds / stats.total_tool_calls if stats.total_tool_calls > 0 else 0
            summary_rows = [
                ("Total Time", self._format_duration(stats.total_tool_time_seconds)),
                ("Avg Time", self._format_duration(avg_tool_per_call)),
                ("Total Calls", f"{stats.total_tool_calls}"),
            ]
            for name, val in summary_rows:
                parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
            for name, count in stats.tool_call_counts.items():
                pct = count / stats.total_tool_calls * 100 if stats.total_tool_calls > 0 else 0
                bar_w = count / max_count * 100 if max_count > 0 else 0
                parts.append(
                    f'<div class="stat-row">'
                    f'<span class="stat-name">{html.escape(name)}</span>'
                    f'<span class="stat-val">{count} ({pct:.1f}%)</span>'
                    f'</div>'
                    f'<div class="tool-bar"><div class="tool-bar-fill" style="width:{bar_w:.0f}%"></div></div>'
                )
            parts.append('</div>')

        # LLM 调用统计
        parts.append('<div class="stat-section">')
        parts.append("<h3>LLM Calls</h3>")
        avg_llm_per_call = stats.total_llm_time_seconds / stats.total_iterations if stats.total_iterations > 0 else 0
        llm_rows = [
            ("Total Time", self._format_duration(stats.total_llm_time_seconds)),
            ("Avg Time", self._format_duration(avg_llm_per_call)),
            ("Total Calls", f"{stats.total_iterations}"),
        ]
        for name, val in llm_rows:
            parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
        parts.append('</div>')

        # 时间统计
        parts.append('<div class="stat-section">')
        parts.append("<h3>Timing</h3>")
        timing_rows = [
            ("LLM Avg", self._format_duration(stats.avg_llm_time_seconds)),
            ("Tool Avg", self._format_duration(stats.avg_tool_time_seconds)),
            ("LLM Total", self._format_duration(stats.total_llm_time_seconds)),
            ("Tool Total", self._format_duration(stats.total_tool_time_seconds)),
            ("Total Duration", self._format_duration(stats.total_duration_seconds)),
        ]
        # 最大 LLM / Tool 耗时
        max_llm = 0.0
        max_tool = 0.0
        for chain in result.sorted_sessions:
            for t in chain.iteration_timings:
                if t.llm_call_duration > max_llm:
                    max_llm = t.llm_call_duration
                if t.tool_processing_duration > max_tool:
                    max_tool = t.tool_processing_duration
        timing_rows.append(("LLM Max", self._format_duration(max_llm)))
        timing_rows.append(("Tool Max", self._format_duration(max_tool)))
        # 每迭代平均总时间
        if stats.total_iterations > 0:
            avg_total = (stats.total_llm_time_seconds + stats.total_tool_time_seconds) / stats.total_iterations
            timing_rows.append(("Avg per Iteration", self._format_duration(avg_total)))
        for name, val in timing_rows:
            parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
        parts.append('</div>')

        # Token 统计
        parts.append('<div class="stat-section">')
        parts.append("<h3>Tokens</h3>")
        cache_rate = (stats.total_cache_tokens / stats.total_tokens * 100) if stats.total_tokens > 0 else 0
        avg_tokens = stats.total_tokens // stats.total_iterations if stats.total_iterations > 0 else 0
        token_rows = [
            ("Input", f"{stats.total_input_tokens:,}"),
            ("Output", f"{stats.total_output_tokens:,}"),
            ("Cache", f"{stats.total_cache_tokens:,}"),
            ("Total", f"{stats.total_tokens:,}"),
            ("Cache Hit Rate", f"{cache_rate:.1f}%"),
            ("Avg per Iteration", f"{avg_tokens:,}"),
        ]
        for name, val in token_rows:
            parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
        parts.append('</div>')

        # 模型使用统计
        if stats.sessions_by_model:
            parts.append('<div class="stat-section">')
            parts.append("<h3>Models</h3>")
            parts.append('<table><tr><th>Model</th><th>Sessions</th></tr>')
            for model, cnt in sorted(stats.sessions_by_model.items(), key=lambda x: -x[1]):
                parts.append(f'<tr><td>{html.escape(model)}</td><td>{cnt}</td></tr>')
            parts.append('</table></div>')

        # Session 对比表
        if stats.session_stats:
            parts.append('<div class="stat-section">')
            parts.append("<h3>Session Comparison</h3>")
            parts.append(
                '<table><tr>'
                '<th>Session</th><th>Model</th><th>Iters</th>'
                '<th>LLM</th><th>Tool</th><th>Tokens</th><th>Tool Calls</th>'
                '</tr>'
            )
            for s in stats.session_stats:
                short = self._short_session_id(s["session_id"])
                parts.append(
                    f'<tr>'
                    f'<td>{short}</td>'
                    f'<td>{html.escape(s["model"])}</td>'
                    f'<td>{s["iterations"]}</td>'
                    f'<td>{self._format_duration(s["llm_time"])}</td>'
                    f'<td>{self._format_duration(s["tool_time"])}</td>'
                    f'<td>{s["tokens"]:,}</td>'
                    f'<td>{s["tool_calls"]}</td>'
                    f'</tr>'
                )
            parts.append('</table></div>')

        return "\n".join(parts)

    def _generate_session_statistics_html(self, chain: LLMChain) -> str:
        """生成 session 详情页的统计面板 HTML"""
        parts: List[str] = []

        # 收集工具调用统计
        tool_counts: Dict[str, int] = {}
        for resp in chain.responses:
            if resp.tool_calls:
                for tc in resp.tool_calls:
                    name = tc.get("name") or tc.get("function", {}).get("name", "unknown")
                    tool_counts[name] = tool_counts.get(name, 0) + 1
        total_tool_calls = sum(tool_counts.values())
        tool_counts_sorted = dict(sorted(tool_counts.items(), key=lambda x: -x[1]))

        # 时间统计
        timings = chain.iteration_timings
        num_iters = len(timings)
        max_llm = max((t.llm_call_duration for t in timings), default=0)
        max_tool = max((t.tool_processing_duration for t in timings), default=0)
        min_llm = min((t.llm_call_duration for t in timings if t.llm_call_duration > 0), default=0)
        min_tool = min((t.tool_processing_duration for t in timings if t.tool_processing_duration > 0), default=0)

        # Token 统计
        s_input = sum(r.input_tokens for r in chain.responses)
        s_output = sum(r.output_tokens for r in chain.responses)
        s_total = sum(r.total_tokens for r in chain.responses)
        s_cache = sum(r.cache_tokens for r in chain.responses)

        # 概览卡片
        parts.append('<div class="stat-cards">')
        overview = [
            (num_iters, "Iterations"),
            (len(chain.subagents), "Subagents"),
            (total_tool_calls, "Tool Calls"),
            (self._format_duration(chain.total_llm_duration_seconds), "LLM Total"),
            (self._format_duration(chain.total_tool_duration_seconds), "Tool Total"),
            (f"{s_total:,}", "Total Tokens"),
        ]
        for val, label in overview:
            parts.append(f'<div class="stat-card"><div class="stat-value">{val}</div><div class="stat-label">{label}</div></div>')
        parts.append('</div>')

        # 工具调用统计
        if tool_counts_sorted:
            max_count = max(tool_counts_sorted.values())
            parts.append('<div class="stat-section">')
            parts.append("<h3>Tool Calls</h3>")
            avg_tool_per_call = chain.total_tool_duration_seconds / total_tool_calls if total_tool_calls > 0 else 0
            summary_rows = [
                ("Total Time", self._format_duration(chain.total_tool_duration_seconds)),
                ("Avg Time", self._format_duration(avg_tool_per_call)),
                ("Total Calls", f"{total_tool_calls}"),
            ]
            for name, val in summary_rows:
                parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
            for name, count in tool_counts_sorted.items():
                pct = count / total_tool_calls * 100 if total_tool_calls > 0 else 0
                bar_w = count / max_count * 100 if max_count > 0 else 0
                parts.append(
                    f'<div class="stat-row">'
                    f'<span class="stat-name">{html.escape(name)}</span>'
                    f'<span class="stat-val">{count} ({pct:.1f}%)</span>'
                    f'</div>'
                    f'<div class="tool-bar"><div class="tool-bar-fill" style="width:{bar_w:.0f}%"></div></div>'
                )
            parts.append('</div>')

        # LLM 调用统计
        parts.append('<div class="stat-section">')
        parts.append("<h3>LLM Calls</h3>")
        avg_llm_per_call = chain.total_llm_duration_seconds / num_iters if num_iters > 0 else 0
        llm_rows = [
            ("Total Time", self._format_duration(chain.total_llm_duration_seconds)),
            ("Avg Time", self._format_duration(avg_llm_per_call)),
            ("Total Calls", f"{num_iters}"),
        ]
        for name, val in llm_rows:
            parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
        parts.append('</div>')

        # 时间统计
        parts.append('<div class="stat-section">')
        parts.append("<h3>Timing</h3>")
        avg_llm = chain.total_llm_duration_seconds / num_iters if num_iters > 0 else 0
        avg_tool = chain.total_tool_duration_seconds / num_iters if num_iters > 0 else 0
        avg_total = avg_llm + avg_tool
        timing_rows = [
            ("LLM Avg", self._format_duration(avg_llm)),
            ("LLM Min", self._format_duration(min_llm)),
            ("LLM Max", self._format_duration(max_llm)),
            ("Tool Avg", self._format_duration(avg_tool)),
            ("Tool Min", self._format_duration(min_tool)),
            ("Tool Max", self._format_duration(max_tool)),
            ("Avg per Iteration", self._format_duration(avg_total)),
            ("LLM Total", self._format_duration(chain.total_llm_duration_seconds)),
            ("Tool Total", self._format_duration(chain.total_tool_duration_seconds)),
        ]
        for name, val in timing_rows:
            parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
        parts.append('</div>')

        # Token 统计
        parts.append('<div class="stat-section">')
        parts.append("<h3>Tokens</h3>")
        cache_rate = (s_cache / s_total * 100) if s_total > 0 else 0
        avg_tokens = s_total // num_iters if num_iters > 0 else 0
        token_rows = [
            ("Input", f"{s_input:,}"),
            ("Output", f"{s_output:,}"),
            ("Cache", f"{s_cache:,}"),
            ("Total", f"{s_total:,}"),
            ("Cache Hit Rate", f"{cache_rate:.1f}%"),
            ("Avg per Iteration", f"{avg_tokens:,}"),
        ]
        for name, val in token_rows:
            parts.append(f'<div class="stat-row"><span class="stat-name">{name}</span><span class="stat-val">{val}</span></div>')
        parts.append('</div>')

        # Subagent 统计
        if chain.subagents:
            parts.append('<div class="stat-section">')
            parts.append("<h3>Subagents</h3>")
            parts.append('<table><tr><th>Subagent</th><th>Depth</th><th>Duration</th></tr>')
            for sa in chain.subagents:
                duration = sa.end_time - sa.start_time if sa.end_time and sa.start_time else 0
                short = self._short_session_id(sa.session_id)
                parts.append(
                    f'<tr><td>{short}</td><td>{sa.depth}</td>'
                    f'<td>{self._format_duration(duration)}</td></tr>'
                )
            parts.append('</table></div>')

        return "\n".join(parts)

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
