"""报告生成模块"""

import json
from datetime import datetime
from pathlib import Path
from typing import List

from .constants import FlowItemType
from .models import AnalysisResult, FlowItem, RequestData
from .templates import (
    CSS_TEMPLATE,
    JS_TEMPLATE,
    escape_html,
    format_time_display,
    get_context_chart_section,
    get_header_section,
    get_html_body_end,
    get_html_body_start,
    get_html_end,
    get_html_head_end,
    get_html_start,
    get_metadata_section,
    get_stats_section,
    get_top_duration_section,
)


class HTMLReporter:
    """HTML报告生成器"""

    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self._compression_index = 0
        self._flow_item_index = 0

    def generate(self, result: AnalysisResult, output_path: str) -> None:
        """生成HTML报告"""
        # 重置索引
        self._compression_index = 0
        self._flow_item_index = 0
        html_content = self._build_html(result)

        output_file = Path(output_path)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"报告已生成: {output_file.absolute()}")

    def _build_html(self, result: AnalysisResult) -> str:
        """构建完整HTML"""
        parts = [
            get_html_start(),
            CSS_TEMPLATE,
            get_html_head_end(),
            get_html_body_start(),
            get_header_section(),
            get_stats_section(result.statistics),
            get_context_chart_section(result.compression_events),
            self._get_timeline_section(result.timeline),
            get_top_duration_section(result.top_duration_steps),
            get_metadata_section(
                str(self.file_path),
                result.total_events,
                result.statistics.total_time,
            ),
            get_html_body_end(),
            JS_TEMPLATE,
            get_html_end(),
        ]
        return "\n".join(parts)

    def _get_timeline_section(self, timeline: List[RequestData]) -> str:
        """生成时间线部分"""
        items = []
        for i, request in enumerate(timeline, 1):
            timestamp_str = datetime.fromtimestamp(request.start_time).strftime("%Y-%m-%d %H:%M:%S")
            details = self._generate_request_details(request)

            items.append(f"""<div class="timeline-item">
                <div class="request-header" onclick="toggleRequest(this)">
                    <div>
                        <span class="request-id">#{i} - {request.request_id}</span>
                        <span class="badge badge-blue">{timestamp_str}</span>
                        <span class="badge badge-green" style="margin-left: 10px;">总耗时: {request.duration:.2f}s</span>
                    </div>
                    <div>
                        <span class="arrow">▼</span>
                    </div>
                </div>
                <div class="request-details">
                    {details}
                </div>
            </div>""")

        items_joined = "\n".join(items)
        return f"""
        <div class="section">
            <h2 class="section-title">完整对话历史</h2>
            {items_joined}
        </div>"""

    def _generate_request_details(self, request: RequestData) -> str:
        """生成请求详情"""
        details = []

        if request.user_input:
            details.append(self._render_user_input(request.user_input))

        for flow_item in request.execution_flow:
            detail = self._render_flow_item(flow_item, request)
            if detail:
                details.append(detail)

        return "\n".join(details)

    def _render_user_input(self, user_input: str) -> str:
        """渲染用户输入"""
        index = self._flow_item_index
        self._flow_item_index += 1
        return f"""<div class="flow-item">
            <div class="message-box user-message" id="flow-item-{index}">
                <div class="message-header">
                    <span class="duration-badge">-</span>
                    <span class="badge badge-blue">用户输入</span>
                </div>
                <div class="message-content">{escape_html(user_input)}</div>
            </div>
        </div>"""

    def _render_flow_item(self, flow_item: FlowItem, request: RequestData) -> str:
        """渲染流程项"""
        if flow_item.type == FlowItemType.REASONING:
            return self._render_reasoning(flow_item)
        elif flow_item.type == FlowItemType.TOOL_CALL:
            return self._render_tool_call(flow_item)
        elif flow_item.type == FlowItemType.COMPRESSION:
            return self._render_compression(flow_item, request)
        elif flow_item.type == FlowItemType.ASSISTANT_RESPONSE:
            return self._render_assistant_response(flow_item)
        return ""

    def _render_reasoning(self, flow_item: FlowItem) -> str:
        """渲染推理过程"""
        index = self._flow_item_index
        self._flow_item_index += 1
        time_html = format_time_display(flow_item.duration)
        content = flow_item.content or ""

        return f"""<div class="flow-item">
            <div class="message-box assistant-message" id="flow-item-{index}">
                <div class="message-header">
                    {time_html}
                    <span class="badge badge-green">推理过程</span>
                </div>
                <div class="message-content">{escape_html(content)}</div>
            </div>
        </div>"""

    def _render_tool_call(self, flow_item: FlowItem) -> str:
        """渲染工具调用"""
        index = self._flow_item_index
        self._flow_item_index += 1
        tool_name = flow_item.name or "unknown"
        arguments = flow_item.arguments or "{}"
        timestamp_str = datetime.fromtimestamp(flow_item.timestamp).strftime("%m-%d %H:%M:%S")
        time_html = format_time_display(flow_item.duration)
        params_html = self._format_tool_params(tool_name, arguments)

        result_html = ""
        if flow_item.result:
            result_html = f"""<div style="margin-top: 10px;">
                <div class="message-label"><strong>结果:</strong></div>
                <pre style="white-space: pre-wrap; word-wrap: break-word; background: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 0.85em;">{escape_html(str(flow_item.result))}</pre>
            </div>"""

        return f"""<div class="flow-item">
            <div class="message-box tool-call" id="flow-item-{index}">
                <div class="message-header">
                    {time_html}
                    <span class="badge badge-orange">工具调用: {tool_name}</span>
                    <span style="font-size: 0.9em; color: #999;">{timestamp_str}</span>
                </div>
                <div class="message-label"><strong>参数:</strong></div>
                {params_html}
                {result_html}
            </div>
        </div>"""

    def _render_compression(self, flow_item: FlowItem, request: RequestData) -> str:
        """渲染压缩事件"""
        timestamp_str = datetime.fromtimestamp(flow_item.timestamp).strftime("%m-%d %H:%M:%S")

        prev_end_time = request.start_time
        for i, item in enumerate(request.execution_flow):
            if item == flow_item and i > 0:
                prev_item = request.execution_flow[i - 1]
                if prev_item.type == FlowItemType.TOOL_CALL:
                    prev_end_time = prev_item.timestamp + prev_item.duration
                elif prev_item.type == FlowItemType.REASONING:
                    prev_end_time = prev_item.end_timestamp or prev_item.timestamp
                elif prev_item.type == FlowItemType.ASSISTANT_RESPONSE:
                    prev_end_time = prev_item.end_timestamp or prev_item.timestamp
                elif prev_item.type == FlowItemType.COMPRESSION:
                    prev_end_time = prev_item.timestamp
                break

        duration = flow_item.timestamp - prev_end_time
        time_html = format_time_display(duration)

        before = flow_item.before or 0
        after = flow_item.after or 0
        rate = flow_item.rate or 0
        compression_index = self._compression_index
        flow_index = self._flow_item_index
        self._compression_index += 1
        self._flow_item_index += 1

        return f"""<div class="flow-item">
            <div class="message-box compression" id="flow-item-{flow_index}" data-compression="{compression_index}">
                <div class="message-header">
                    {time_html}
                    <span class="badge badge-red">上下文压缩</span>
                    <span style="font-size: 0.9em; color: #999;">{timestamp_str}</span>
                </div>
                <div class="message-content">
                    <div>压缩前: {before} tokens</div>
                    <div>压缩后: {after} tokens</div>
                    <div>压缩率: {rate / 100:.1%}</div>
                </div>
            </div>
        </div>"""

    def _render_assistant_response(self, flow_item: FlowItem) -> str:
        """渲染助手响应"""
        index = self._flow_item_index
        self._flow_item_index += 1
        time_html = format_time_display(flow_item.duration)
        content = flow_item.content or ""

        return f"""<div class="flow-item">
            <div class="message-box assistant-message" id="flow-item-{index}">
                <div class="message-header">
                    {time_html}
                    <span class="badge badge-green">助手回复</span>
                </div>
                <div class="message-content">{escape_html(content)}</div>
            </div>
        </div>"""

    def _format_tool_params(self, tool_name: str, arguments: str) -> str:
        """格式化工具参数"""
        try:
            params = json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            return f"<pre style='background: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 0.85em;'>{escape_html(arguments)}</pre>"

        if tool_name == "execute_python_code" and "code_block" in params:
            code = params["code_block"]
            return f"""<pre style="background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; font-family: 'Courier New', monospace; font-size: 0.9em;"><code>{escape_html(code)}</code></pre>"""

        formatted_json = json.dumps(params, indent=2, ensure_ascii=False)
        return f"<pre style='background: #f5f5f5; padding: 8px; border-radius: 4px; overflow-x: auto; font-size: 0.85em;'>{escape_html(formatted_json)}</pre>"
