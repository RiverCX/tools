"""HTML模板模块"""

from datetime import datetime
from typing import List

from .models import Statistics

CSS_TEMPLATE = """
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f7fa;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }

        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px 15px;
            text-align: center;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .header h1 { font-size: 1.8em; margin-bottom: 5px; }
        .header p { font-size: 0.85em; opacity: 0.9; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 12px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            border-radius: 8px;
            padding: 12px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .stat-card:hover { transform: translateY(-3px); }
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }
        .stat-label { font-size: 0.85em; color: #666; }

        .section {
            background: white;
            border-radius: 10px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .section-title {
            font-size: 1.8em;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }

        .timeline-item {
            border-left: 4px solid #667eea;
            padding-left: 20px;
            margin-bottom: 30px;
            position: relative;
        }
        .timeline-item::before {
            content: '';
            position: absolute;
            left: -8px;
            top: 0;
            width: 16px;
            height: 16px;
            background: #667eea;
            border-radius: 50%;
        }

        .request-header {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .request-header:hover { background: #e9ecef; }
        .request-id { font-weight: bold; color: #667eea; }

        .request-details {
            display: none;
            padding: 15px;
            background: #fafafa;
            border-radius: 8px;
            margin-top: 10px;
        }
        .request-details.active { display: block; }

        .flow-item {
            margin: 10px 0;
        }
        .duration-badge {
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 3px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.85em;
            min-width: 60px;
            text-align: center;
        }
        .cumulative-time {
            display: inline-block;
            background: #e3f2fd;
            color: #1976d2;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 0.85em;
            margin-top: 3px;
        }

        .message-box {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
        }
        .message-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 10px;
        }
        .message-label {
            font-weight: bold;
            color: #666;
        }
        .message-content { color: #333; }
        .user-message { border-left: 4px solid #2196F3; }
        .assistant-message { border-left: 4px solid #4CAF50; }
        .tool-call { border-left: 4px solid #FF9800; }
        .compression { border-left: 4px solid #F44336; }

        .chart-container {
            background: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 30px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .chart-title {
            font-size: 1.2em;
            color: #333;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }
        .chart-wrapper {
            position: relative;
            height: 300px;
        }

        .tool-table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }
        .tool-table th, .tool-table td {
            border: 1px solid #e0e0e0;
            padding: 12px;
            text-align: left;
        }
        .tool-table th { background: #667eea; color: white; }
        .tool-table tr:hover { background: #f5f5f5; }

        .collapsible-header {
            background: #f0f0f0;
            padding: 10px;
            cursor: pointer;
            border-radius: 5px;
            margin: 10px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .collapsible-header:hover { background: #e0e0e0; }
        .collapsible-content {
            display: none;
            padding: 15px;
            background: #fafafa;
            border-radius: 5px;
            max-height: 500px;
            overflow-y: auto;
        }
        .collapsible-content.active { display: block; }

        .arrow { transition: transform 0.3s; }
        .arrow.rotated { transform: rotate(180deg); }

        .badge {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .badge-blue { background: #e3f2fd; color: #1976d2; }
        .badge-green { background: #e8f5e9; color: #388e3c; }
        .badge-orange { background: #fff3e0; color: #f57c00; }
        .badge-red { background: #ffebee; color: #d32f2f; }

        .metadata {
            font-size: 0.9em;
            color: #999;
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
        }
    </style>
"""

JS_TEMPLATE = """
    <script>
        function scrollToCard(card) {
            if (!card) return;
            // 展开父级详情
            let details = card.closest('.request-details');
            if (details && !details.classList.contains('active')) {
                details.classList.add('active');
            }
            // 滚动到卡片
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // 高亮效果
            card.style.transition = 'box-shadow 0.3s';
            card.style.boxShadow = '0 0 15px rgba(102, 126, 234, 0.8)';
            setTimeout(function() {
                card.style.boxShadow = '';
            }, 2000);
        }

        function toggleCollapsible(header) {
            const content = header.nextElementSibling;
            const arrow = header.querySelector('.arrow');

            if (content.classList.contains('active')) {
                content.classList.remove('active');
                arrow.classList.remove('rotated');
            } else {
                content.classList.add('active');
                arrow.classList.add('rotated');
            }
        }

        function toggleRequest(header) {
            const details = header.nextElementSibling;
            if (details.classList.contains('active')) {
                details.classList.remove('active');
            } else {
                details.classList.add('active');
            }
        }
    </script>
"""


NEWLINE = "\n"


def get_html_start() -> str:
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent History Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>"""


def get_html_head_end() -> str:
    return "</head>"


def get_html_body_start() -> str:
    return """
<body>
    <div class="container">"""


def get_html_body_end() -> str:
    return """
    </div>"""


def get_html_end() -> str:
    return """
</body>
</html>"""


def get_context_chart_section(compression_events: List) -> str:
    """生成上下文变化曲线图"""
    if not compression_events:
        return ""

    labels = [str(i + 1) for i in range(len(compression_events))]
    before_data = [e["before"] for e in compression_events]
    after_data = [e["after"] for e in compression_events]

    return f"""
        <div class="chart-container">
            <div class="chart-title">上下文变化曲线 (点击柱状条跳转到详情)</div>
            <div class="chart-wrapper">
                <canvas id="contextChart"></canvas>
            </div>
        </div>
        <script>
            const ctx = document.getElementById('contextChart').getContext('2d');
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: {labels},
                    datasets: [
                        {{
                            label: '压缩前',
                            data: {before_data},
                            backgroundColor: 'rgba(244, 67, 54, 0.7)',
                            borderColor: '#F44336',
                            borderWidth: 1
                        }},
                        {{
                            label: '压缩后',
                            data: {after_data},
                            backgroundColor: 'rgba(76, 175, 80, 0.7)',
                            borderColor: '#4CAF50',
                            borderWidth: 1
                        }}
                    ]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: function(event, elements) {{
                        if (elements.length > 0) {{
                            const index = elements[0].index;
                            const card = document.querySelector('[data-compression="' + index + '"]');
                            if (card) {{
                                scrollToCard(card);
                            }}
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            position: 'top'
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    return context.dataset.label + ': ' + context.raw + ' tokens';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{
                                display: true,
                                text: 'Tokens'
                            }}
                        }},
                        x: {{
                            title: {{
                                display: true,
                                text: '压缩次数'
                            }}
                        }}
                    }}
                }}
            }});
        </script>"""


def get_header_section() -> str:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
        <div class="header">
            <h1>Agent History Analysis Report</h1>
            <p>生成时间: {timestamp}</p>
        </div>"""


def get_stats_section(stats: Statistics) -> str:
    return f"""
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{stats.total_requests}</div>
                <div class="stat-label">总对话轮数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.user_messages}</div>
                <div class="stat-label">用户消息数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.assistant_messages}</div>
                <div class="stat-label">助手回复数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.tool_calls}</div>
                <div class="stat-label">工具调用数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.context_compressed}</div>
                <div class="stat-label">上下文压缩次数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.total_time:.2f}s</div>
                <div class="stat-label">总耗时</div>
            </div>
        </div>"""


def get_metadata_section(file_path: str, total_events: int, total_time: float) -> str:
    return f"""
        <div class="metadata">
            <p>文件路径: {file_path}</p>
            <p>总事件数: {total_events}</p>
            <p>总耗时: {total_time:.2f}秒</p>
        </div>"""


def escape_html(text: str) -> str:
    if not text:
        return ""
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def format_time_display(duration: float) -> str:
    duration_str = f"{duration:.2f}s" if duration > 0 else "-"
    return f"<span class='duration-badge'>{duration_str}</span>"


def get_top_duration_section(top_steps: List) -> str:
    if not top_steps:
        return ""

    rows = []
    for i, step in enumerate(top_steps, 1):
        badge_class = (
            "badge-red"
            if step.duration > 5
            else ("badge-orange" if step.duration > 2 else "badge-blue")
        )
        flow_index = step.flow_item_index
        rows.append(
            f"""<tr onclick="scrollToCard(document.getElementById('flow-item-{flow_index}'))" style="cursor: pointer;">
            <td><strong>#{i}</strong></td>
            <td><span class='badge {badge_class}'>{step.duration:.2f}s</span></td>
            <td><span class='badge badge-green'>{step.type}</span></td>
            <td>{escape_html(step.summary)}</td>
            <td style="font-size: 0.85em; color: #666;">{escape_html(step.user_input)}</td>
        </tr>"""
        )

    rows_joined = NEWLINE.join(rows)
    return f"""
        <div class="section">
            <h2 class="section-title">耗时排行榜 (Top 20) - 点击跳转</h2>
            <table class="tool-table">
                <thead>
                    <tr>
                        <th style="width: 50px;">排名</th>
                        <th style="width: 100px;">耗时</th>
                        <th style="width: 100px;">类型</th>
                        <th>摘要</th>
                        <th>用户输入</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_joined}
                </tbody>
            </table>
        </div>"""
