"""HTML模板模块"""

REQUEST_TEMPLATE = """
<div>
    <span class="label">REQUEST</span>
    <span class="label {source_class}">{source_label}</span>
    {internal_label}
    <span class="timestamp">{timestamp}</span>
    <span class="char-count">{request_chars} chars</span>
    {system_prompt_html}
    <div style="margin-top: 10px;">
        <div class="collapsible" onclick="toggleCollapsible(this)">
            <span class="toggle-icon">&#9654;</span> Messages ({message_count})
            <span class="char-count">{messages_chars} chars</span>
        </div>
        <div class="collapsible-content">
            {messages_html}
        </div>
    </div>
    {tools_html}
    {new_message_html}
</div>
"""

TOOL_RESULT_TEMPLATE = """
<div style="margin-top: 10px;">
    <span class="label tool">Tool Call Results ({new_count})</span>
    <span class="char-count">{new_chars} chars</span>
    <span style="margin-left: 10px; color: #666;">[{tool_names}]</span>
    <div class="json-container">
        <button class="copy-btn" onclick="copyToClipboard(this, '{content_id}')">Copy</button>
        <pre class="json-content" id="{content_id}">{new_messages_json}</pre>
    </div>
</div>
"""

SYSTEM_PROMPT_TEMPLATE = """
<div style="margin-top: 10px;">
    <div class="collapsible" onclick="toggleCollapsible(this)">
        <span class="toggle-icon">&#9654;</span> System
        <span class="char-count">{char_count} chars</span>
    </div>
    <div class="collapsible-content">
        <div class="json-container">
            <button class="copy-btn" onclick="copyToClipboard(this, '{content_id}')">Copy</button>
            <pre class="json-content" id="{content_id}">{system_prompt}</pre>
        </div>
    </div>
</div>
"""

RESPONSE_TEMPLATE = """
<div style="margin-top: 15px;">
    <span class="label response">RESPONSE</span>
    <span class="label {source_class}">{source_label}</span>
    <span class="timestamp">{timestamp}</span>
    <span class="char-count">{response_chars} chars</span>
    {reasoning_html}
    {content_html}
    {tool_calls_html}
</div>
"""

REASONING_TEMPLATE = """
<div style="margin-top: 10px;">
    <span class="label reasoning">Reasoning</span>
    <span class="char-count">{char_count} chars</span>
    <div class="json-container">
        <button class="copy-btn" onclick="copyToClipboard(this, '{content_id}')">Copy</button>
        <pre class="json-content" id="{content_id}">{reasoning_content}</pre>
    </div>
</div>
"""

CONTENT_TEMPLATE = """
<div style="margin-top: 10px;">
    <span class="label">Content</span>
    <span class="char-count">{char_count} chars</span>
    <div class="json-container">
        <button class="copy-btn" onclick="copyToClipboard(this, '{content_id}')">Copy</button>
        <pre class="json-content" id="{content_id}">{content}</pre>
    </div>
</div>
"""

TOOL_CALLS_TEMPLATE = """
<div style="margin-top: 10px;">
    <span class="label tool">Tool Calls ({tool_count})</span>
    <span class="char-count">{char_count} chars</span>
    <span style="margin-left: 10px; color: #666;">[{tool_names}]</span>
    <div class="json-container">
        <button class="copy-btn" onclick="copyToClipboard(this, '{content_id}')">Copy</button>
        <pre class="json-content" id="{content_id}">{tool_calls_json}</pre>
    </div>
</div>
"""

JSON_BLOCK_TEMPLATE = """
<div class="json-container">
    <button class="copy-btn" onclick="copyToClipboard(this, '{content_id}')">Copy</button>
    <pre class="json-content" id="{content_id}">{content}</pre>
</div>
"""

INDEX_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Trace Index</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #1a1a2e; margin-bottom: 20px; }}
        .stats {{ background: #667eea; color: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; }}
        .stats span {{ margin-right: 20px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        th {{ background: #4a90d9; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 12px; border-bottom: 1px solid #e0e0e0; }}
        tr:hover {{ background: #f8f9fa; }}
        a {{ color: #4a90d9; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .model {{ color: #666; font-size: 13px; }}
        .time {{ color: #999; font-size: 12px; }}
        .first-msg {{ max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; color: #555; }}
/* Page Tab Navigation */
.page-tab-nav {{ display: flex; gap: 0; margin-bottom: 0; border-bottom: 2px solid #e0e0e0; padding: 0 5px; }}
.page-tab-btn {{ padding: 10px 20px; border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; background: #f0f0f0; cursor: pointer; font-size: 14px; margin-bottom: -2px; color: #666; transition: all 0.2s; }}
.page-tab-btn:hover {{ background: #e8e8e8; }}
.page-tab-btn.active {{ background: white; color: #4a90d9; font-weight: bold; border-color: #e0e0e0; border-bottom-color: white; }}
.page-tab-panel {{ display: none; padding-top: 20px; }}
.page-tab-panel.active {{ display: block; }}
/* Compare Panel */
.compare-panel {{ background: white; border-radius: 8px; padding: 20px; margin-top: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.compare-table {{ width: 100%; border-collapse: collapse; }}
.compare-table th {{ background: #4a90d9; color: white; padding: 10px 12px; text-align: left; font-size: 13px; cursor: pointer; white-space: nowrap; }}
.compare-table th:hover {{ background: #3a7bc8; }}
.compare-table th.baseline {{ background: #2d6bb4; position: relative; }}
.compare-table th.baseline::after {{ content: ' (baseline)'; font-size: 10px; opacity: 0.8; }}
.compare-table td {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
.compare-table tr:hover {{ background: #f8f9fa; }}
.delta-pos {{ color: #388e3c; font-size: 12px; margin-left: 4px; }}
.delta-neg {{ color: #d32f2f; font-size: 12px; margin-left: 4px; }}
.session-cb {{ cursor: pointer; width: 16px; height: 16px; }}
/* Statistics Panel */
.stat-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin-bottom: 25px; }}
.stat-card {{ background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
.stat-card .stat-value {{ font-size: 28px; font-weight: bold; color: #4a90d9; }}
.stat-card .stat-label {{ font-size: 13px; color: #666; margin-top: 4px; }}
.stat-section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.stat-section h3 {{ color: #1a1a2e; margin-bottom: 15px; font-size: 16px; border-bottom: 2px solid #4a90d9; padding-bottom: 8px; }}
.stat-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }}
.stat-row:last-child {{ border-bottom: none; }}
.stat-row .stat-name {{ font-weight: 500; }}
.stat-row .stat-val {{ color: #4a90d9; font-weight: bold; }}
.tool-bar {{ height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; margin-top: 4px; }}
.tool-bar-fill {{ height: 100%; background: #4a90d9; border-radius: 4px; transition: width 0.3s; }}
.stat-section table {{ width: 100%; border-collapse: collapse; }}
.stat-section th {{ background: #4a90d9; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
.stat-section td {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
.stat-section tr:hover {{ background: #f8f9fa; }}
.stat-section th.sortable {{ cursor: pointer; user-select: none; white-space: nowrap; }}
.stat-section th.sortable:hover {{ background: #3a7bc8; }}
.stat-section th.sortable.sort-asc::after {{ content: ' ▲'; font-size: 10px; }}
.stat-section th.sortable.sort-desc::after {{ content: ' ▼'; font-size: 10px; }}
/* Timing Chart */
.timing-chart-wrapper {{ margin-bottom: 10px; }}
.chart-legend {{ display: flex; gap: 16px; margin-bottom: 8px; font-size: 12px; color: #666; }}
.chart-legend-item {{ display: flex; align-items: center; gap: 4px; }}
.chart-legend-color {{ width: 12px; height: 12px; border-radius: 2px; }}
.chart-legend-llm {{ background: #4a90d9; }}
.chart-legend-tool {{ background: #f57c00; }}
.chart-toggle {{ cursor: pointer; padding: 2px 8px; border-radius: 4px; border: 1px solid transparent; transition: all 0.2s; user-select: none; }}
.chart-toggle:hover {{ background: #f0f0f0; }}
.chart-toggle.active {{ border-color: #ccc; }}
.chart-toggle:not(.active) {{ opacity: 0.4; }}
.timing-chart {{ display: flex; align-items: flex-end; gap: 2px; height: 200px; padding: 0 4px; border-bottom: 1px solid #e0e0e0; position: relative; }}
.timing-chart.dense {{ gap: 0; }}
.chart-bar-col {{ display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 3px; cursor: pointer; }}
.timing-chart.dense .chart-bar-col {{ min-width: 0; }}
.chart-bar {{ display: flex; flex-direction: column; width: 100%; justify-content: flex-end; }}
.chart-bar-llm {{ background: #4a90d9; border-radius: 2px 2px 0 0; min-height: 1px; transition: opacity 0.15s, height 0.3s; }}
.chart-bar-tool {{ background: #f57c00; border-radius: 2px 2px 0 0; min-height: 1px; transition: opacity 0.15s, height 0.3s; }}
.chart-bar-col:hover .chart-bar-llm, .chart-bar-col:hover .chart-bar-tool {{ opacity: 0.8; }}
.timing-chart.hide-llm .chart-bar-llm {{ height: 0 !important; min-height: 0 !important; }}
.timing-chart.hide-tool .chart-bar-tool {{ height: 0 !important; min-height: 0 !important; }}
.chart-pxx-line {{ position: absolute; left: 0; right: 0; border-top: 1px dashed #999; pointer-events: none; z-index: 1; }}
.chart-pxx-label {{ position: absolute; right: 4px; top: -14px; font-size: 10px; color: #666; background: rgba(255,255,255,0.85); padding: 0 4px; border-radius: 2px; white-space: nowrap; }}
.chart-x-label {{ font-size: 9px; color: #999; margin-top: 2px; }}
.chart-tooltip {{ position: fixed; pointer-events: none; background: #1a1a2e; color: white; padding: 10px 14px; border-radius: 8px; font-size: 13px; line-height: 1.8; z-index: 2000; box-shadow: 0 4px 16px rgba(0,0,0,0.3); opacity: 0; transition: opacity 0.15s; }}
.chart-tooltip.visible {{ opacity: 1; }}
.chart-tooltip .tt-name {{ font-weight: bold; color: #82b1ff; margin-bottom: 2px; }}
.chart-tooltip .tt-row {{ display: flex; justify-content: space-between; gap: 16px; }}
.chart-tooltip .tt-label {{ color: #aaa; }}
.chart-tooltip .tt-value {{ font-weight: bold; }}
.go-top-btn {{ position: fixed; bottom: 30px; right: 30px; width: 44px; height: 44px; background: #4a90d9; color: white; border: none; border-radius: 50%; cursor: pointer; font-size: 20px; line-height: 44px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.2); opacity: 0; visibility: hidden; transition: opacity 0.3s, visibility 0.3s, background 0.2s; z-index: 1000; }}
.go-top-btn:hover {{ background: #3a7bc8; }}
.go-top-btn.visible {{ opacity: 1; visibility: visible; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>LLM Trace Analysis Index</h1>
        <div class="stats">
            <span><strong>{total_sessions}</strong> sessions</span>
            <span><strong>{total_requests}</strong> requests</span>
            <span><strong>{total_iterations}</strong> iterations</span>
            <span><strong>{total_duration}</strong> total time</span>
            <span><strong>{avg_llm_time}</strong> avg LLM</span>
        </div>
        <div class="stats" style="background: #48bb78; margin-top: 10px;">
            <span><strong>{total_input_tokens:,}</strong> input tokens</span>
            <span><strong>{total_output_tokens:,}</strong> output tokens</span>
            <span><strong>{total_tokens:,}</strong> total tokens</span>
            <span><strong>{total_cache_tokens:,}</strong> cache tokens</span>
        </div>
        <div class="page-tab-nav">
            <button class="page-tab-btn active" onclick="switchPageTab('sessions')">Sessions</button>
            <button class="page-tab-btn" onclick="switchPageTab('statistics')">Statistics</button>
        </div>
        <div class="page-tab-panel active" id="tab-sessions">
            <table>
                <tr>
                    <th style="width:30px"><input type="checkbox" class="session-cb" id="selectAllCb" onchange="toggleSelectAll(this)" title="Select All" /></th>
                    <th>Session ID</th>
                    <th>Model</th>
                    <th>Iterations</th>
                    <th>Time</th>
                    <th>Prompt</th>
                    <th>Link</th>
                </tr>
                {session_rows}
            </table>
            <div class="compare-panel" id="comparePanel">
                <h3 style="margin:0 0 10px;color:#1a1a2e">Session Comparison <span style="font-size:12px;color:#999;font-weight:normal">(select sessions above, click a column header to set as baseline)</span></h3>
                <div class="compare-hint" id="compareHint" style="color:#999;font-size:14px;padding:20px 0;text-align:center">Select at least 2 sessions using the checkboxes above to compare</div>
                <div class="compare-table-wrapper">
                    <table class="compare-table" id="compareTable"></table>
                </div>
            </div>
        </div>
        <div class="page-tab-panel" id="tab-statistics">
            {statistics_html}
        </div>
    </div>
    <script>
        const sessionStatsData = {session_stats_json};
        let selectedSessions = [];
        let baselineSessionId = null;

        function toggleSessionCompare(cb) {{
            const sid = cb.dataset.sessionId;
            if (cb.checked) {{
                if (!selectedSessions.includes(sid)) selectedSessions.push(sid);
            }} else {{
                selectedSessions = selectedSessions.filter(s => s !== sid);
                if (baselineSessionId === sid) baselineSessionId = null;
            }}
            // 更新全选状态
            const allCbs = document.querySelectorAll('.session-cb[data-session-id]');
            const allChecked = allCbs.length > 0 && Array.from(allCbs).every(c => c.checked);
            const selectAll = document.getElementById('selectAllCb');
            if (selectAll) selectAll.checked = allChecked;
            renderComparison();
        }}

        function toggleSelectAll(masterCb) {{
            const cbs = document.querySelectorAll('.session-cb[data-session-id]');
            cbs.forEach(cb => {{
                if (cb.checked !== masterCb.checked) {{
                    cb.checked = masterCb.checked;
                    toggleSessionCompare(cb);
                }}
            }});
        }}

        function setBaseline(sid) {{
            baselineSessionId = (baselineSessionId === sid) ? selectedSessions[0] : sid;
            renderComparison();
        }}

        function fmtDur(s) {{
            if (s <= 0) return 'N/A';
            if (s < 1) return Math.round(s * 1000) + 'ms';
            if (s < 60) return s.toFixed(1) + 's';
            const m = Math.floor(s / 60);
            const sec = Math.round(s % 60);
            return m + 'm ' + sec + 's';
        }}

        function deltaHtml(val, baseVal, isTime) {{
            const diff = val - baseVal;
            if (diff === 0) return '';
            const sign = diff > 0 ? '+' : '';
            const cls = diff > 0 ? 'delta-pos' : 'delta-neg';
            const formatted = isTime ? fmtDur(Math.abs(diff)) : Math.abs(diff).toLocaleString();
            const prefix = diff > 0 ? '+' : '-';
            return `<span class="${{cls}}">(${{prefix}}${{formatted}})</span>`;
        }}

        function renderComparison() {{
            const hint = document.getElementById('compareHint');
            const table = document.getElementById('compareTable');
            if (selectedSessions.length < 2) {{
                hint.style.display = 'block';
                table.style.display = 'none';
                return;
            }}
            hint.style.display = 'none';
            table.style.display = '';
            if (!baselineSessionId || !selectedSessions.includes(baselineSessionId)) {{
                baselineSessionId = selectedSessions[0];
            }}

            const statsMap = {{}};
            sessionStatsData.forEach(s => {{ statsMap[s.session_id] = s; }});
            const base = statsMap[baselineSessionId];

            const metrics = [
                ['Model', 'model', false],
                ['Iterations', 'iterations', false],
                ['LLM Time', 'llm_time', true],
                ['Tool Time', 'tool_time', true],
                ['Tokens', 'tokens', false],
                ['Tool Calls', 'tool_calls', false],
            ];

            let html = '<tr><th>Metric</th>';
            selectedSessions.forEach(sid => {{
                const short = sid.split('_').pop().substring(0, 12);
                const cls = sid === baselineSessionId ? 'baseline' : '';
                html += `<th class="${{cls}}" onclick="setBaseline('${{sid}}')">${{short}}</th>`;
            }});
            html += '</tr>';

            metrics.forEach(([label, key, isTime]) => {{
                html += `<tr><td><strong>${{label}}</strong></td>`;
                selectedSessions.forEach(sid => {{
                    const s = statsMap[sid];
                    if (!s) {{ html += '<td>N/A</td>'; return; }}
                    const val = s[key];
                    let cell;
                    if (key === 'model') {{
                        cell = val;
                    }} else if (isTime) {{
                        cell = fmtDur(val);
                        if (sid !== baselineSessionId) cell += ' ' + deltaHtml(val, base[key], true);
                    }} else {{
                        cell = typeof val === 'number' ? val.toLocaleString() : val;
                        if (sid !== baselineSessionId && typeof val === 'number') {{
                            cell += ' ' + deltaHtml(val, base[key], false);
                        }}
                    }}
                    html += `<td>${{cell}}</td>`;
                }});
                html += '</tr>';
            }});

            table.innerHTML = html;
        }}

        function switchPageTab(tabId) {{
            document.querySelectorAll('.page-tab-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.getAttribute('onclick').includes("'" + tabId + "'"));
            }});
            document.querySelectorAll('.page-tab-panel').forEach(panel => {{
                panel.classList.toggle('active', panel.id === 'tab-' + tabId);
            }});
        }}
        function showChartTooltip(event, el) {{
            const tt = document.getElementById('chartTooltip');
            if (!tt) return;
            const seq = el.dataset.seq;
            const llm = el.dataset.llm;
            const tool = el.dataset.tool;
            const total = el.dataset.total;
            tt.innerHTML = `
                <div class="tt-name">#${{seq}}</div>
                <div class="tt-row"><span class="tt-label">LLM Time</span><span class="tt-value">${{llm}}</span></div>
                <div class="tt-row"><span class="tt-label">Tool Time</span><span class="tt-value">${{tool}}</span></div>
                <div class="tt-row"><span class="tt-label">Total</span><span class="tt-value">${{total}}</span></div>
            `;
            tt.style.left = (event.clientX + 12) + 'px';
            tt.style.top = (event.clientY - 10) + 'px';
            tt.classList.add('visible');
        }}
        function moveChartTooltip(event) {{
            const tt = document.getElementById('chartTooltip');
            if (tt) {{ tt.style.left = (event.clientX + 12) + 'px'; tt.style.top = (event.clientY - 10) + 'px'; }}
        }}
        function hideChartTooltip() {{
            const tt = document.getElementById('chartTooltip');
            if (tt) tt.classList.remove('visible');
        }}
        function toggleChartSeries(el) {{
            const series = el.dataset.series;
            el.classList.toggle('active');
            const wrapper = el.closest('.timing-chart-wrapper');
            const chart = wrapper ? wrapper.querySelector('.timing-chart') : null;
            if (!chart) return;
            const showLlm = wrapper.querySelector('[data-series="llm"]').classList.contains('active');
            const showTool = wrapper.querySelector('[data-series="tool"]').classList.contains('active');
            chart.classList.toggle('hide-llm', !showLlm);
            chart.classList.toggle('hide-tool', !showTool);

            const cols = chart.querySelectorAll('.chart-bar-col');
            const chartH = 200;
            let maxVal = 0;
            const vals = [];
            cols.forEach(col => {{
                const l = parseInt(col.dataset.llmMs) || 0;
                const t = parseInt(col.dataset.toolMs) || 0;
                const v = (showLlm ? l : 0) + (showTool ? t : 0);
                vals.push({{l, t, v}});
                if (v > maxVal) maxVal = v;
            }});
            if (maxVal <= 0) maxVal = 1;

            cols.forEach((col, i) => {{
                const llmBar = col.querySelector('.chart-bar-llm');
                const toolBar = col.querySelector('.chart-bar-tool');
                const d = vals[i];
                llmBar.style.height = ((d.l / maxVal) * chartH) + 'px';
                toolBar.style.height = ((d.t / maxVal) * chartH) + 'px';
                const totalMs = d.v;
                col.dataset.total = formatMsDuration(totalMs);
            }});

            const sorted = vals.map(v => v.v).filter(v => v > 0).sort((a, b) => a - b);
            if (sorted.length > 0) {{
                const pxxMap = [
                    [50, 'p50'], [90, 'p90'], [95, 'p95'], [99, 'p99']
                ];
                pxxMap.forEach(([p, cls]) => {{
                    const val = percentile(sorted, p);
                    const pct = (val / maxVal) * 100;
                    const line = chart.querySelector('.chart-pxx-' + cls);
                    if (line) {{
                        line.style.bottom = pct + '%';
                        line.querySelector('.chart-pxx-label').textContent = cls.toUpperCase() + ': ' + formatMsDuration(val);
                    }}
                }});
            }}
        }}
        function percentile(sorted, p) {{
            if (!sorted.length) return 0;
            const k = (sorted.length - 1) * p / 100;
            const f = Math.floor(k);
            const c = f + 1;
            if (c >= sorted.length) return sorted[f];
            return sorted[f] + (k - f) * (sorted[c] - sorted[f]);
        }}
        function formatMsDuration(ms) {{
            const s = ms / 1000;
            if (s <= 0) return 'N/A';
            if (s < 1) return Math.round(ms) + 'ms';
            if (s < 60) return s.toFixed(1) + 's';
            const m = Math.floor(s / 60);
            const sec = Math.round(s % 60);
            return m + 'm ' + sec + 's';
        }}
        function sortToolTable(th, key) {{
            const table = th.closest('table');
            const tbody = table.querySelector('tbody') || table;
            const rows = Array.from(tbody.querySelectorAll('tr[data-name]'));
            const headers = table.querySelectorAll('th.sortable');
            const isAsc = th.classList.contains('sort-desc');
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            th.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            rows.sort((a, b) => {{
                let va, vb;
                if (key === 'name') {{ va = a.dataset.name; vb = b.dataset.name; }}
                else if (key === 'ratio' || key === 'calls') {{ va = +a.dataset.count; vb = +b.dataset.count; }}
                else if (key === 'total') {{ va = +a.dataset.totalMs; vb = +b.dataset.totalMs; }}
                else if (key === 'avg') {{ va = +a.dataset.avgMs; vb = +b.dataset.avgMs; }}
                if (typeof va === 'string') return isAsc ? va.localeCompare(vb) : vb.localeCompare(va);
                return isAsc ? va - vb : vb - va;
            }});
            rows.forEach(r => tbody.appendChild(r));
        }}
        document.addEventListener('DOMContentLoaded', function() {{
            const btn = document.getElementById('goTopBtn');
            if (!btn) return;
            window.addEventListener('scroll', function() {{
                if (window.scrollY > 300) {{
                    btn.classList.add('visible');
                }} else {{
                    btn.classList.remove('visible');
                }}
            }});
            btn.addEventListener('click', function() {{
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }});
        }});
    </script>
    <button id="goTopBtn" class="go-top-btn" title="Go to Top">&#8593;</button>
    <div id="chartTooltip" class="chart-tooltip"></div>
</body>
</html>
"""

SESSION_ROW_TEMPLATE = """
<tr>
    <td><input type="checkbox" class="session-cb" data-session-id="{session_id}" onchange="toggleSessionCompare(this)" /></td>
    <td><a href="{detail_file}">{session_id_short}</a></td>
    <td class="model">{model_name}</td>
    <td>{total_iterations}</td>
    <td class="time">{start_time} - {end_time}</td>
    <td class="first-msg" title="{first_message}">{first_message}</td>
    <td><a href="{detail_file}">View Details</a></td>
</tr>
"""

SESSION_DETAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session: {session_id_short}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f5f5f5; color: #333; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4a90d9; color: white; padding: 15px 20px; border-radius: 8px; margin-bottom: 20px; }}
        .header h1 {{ margin-bottom: 5px; }}
        .header .meta {{ font-size: 14px; opacity: 0.9; }}
        .back-link {{ margin-bottom: 15px; }}
        .back-link a {{ color: #4a90d9; }}
        .iteration-block {{ border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 15px; }}
        .iteration-header {{ background: #f8f9fa; padding: 10px 15px; font-weight: bold; border-bottom: 1px solid #e0e0e0; position: relative; }}
        .iteration-header .copy-btn {{ position: static; margin-left: 15px; padding: 4px 12px; opacity: 0.9; }}
        .time-stats {{ margin-left: 15px; color: #666; font-size: 12px; font-weight: normal; }}
        .iteration-content {{ padding: 15px; }}
        .json-container {{ background: #f8f8f8; border: 1px solid #ddd; border-radius: 6px; padding: 0; margin: 10px 0; overflow: hidden; position: relative; }}
        .json-content {{ font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; white-space: pre-wrap; word-break: break-all; overflow-x: auto; overflow-y: auto; max-height: 400px; padding: 15px; padding-top: 35px; padding-right: 50px; margin: 0; }}
        .copy-btn {{ position: absolute; top: 8px; right: 18px; padding: 4px 8px; background: #4a90d9; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; opacity: 0.8; z-index: 10; }}
        .copy-btn:hover {{ opacity: 1; background: #3a7bc8; }}
        .copy-btn.copied {{ background: #388e3c; }}
        .label {{ display: inline-block; background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-right: 10px; }}
        .label.response {{ background: #e8f5e9; color: #388e3c; }}
        .label.tool {{ background: #fff3e0; color: #f57c00; }}
        .label.reasoning {{ background: #fce4ec; color: #c2185b; }}
        .label.subagent {{ background: #f3e5f5; color: #7b1fa2; }}
        .collapsible {{ cursor: pointer; padding: 8px 12px; background: #e0e0e0; border-radius: 4px; margin-bottom: 8px; }}
        .collapsible:hover {{ background: #d0d0d0; }}
        .collapsible-content {{ display: none; }}
        .collapsible-content.expanded {{ display: block; }}
        .toggle-icon {{ font-size: 12px; transition: transform 0.2s; }}
        .toggle-icon.rotated {{ transform: rotate(90deg); }}
        .timestamp {{ color: #666; font-size: 12px; }}
        .char-count {{ color: #888; font-size: 11px; background: #f0f0f0; padding: 2px 6px; border-radius: 3px; margin-left: 10px; }}
.toggle-view-btn {{ margin-bottom: 10px; padding: 4px 12px; background: #4a90d9; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }}
.toggle-view-btn:hover {{ background: #3a7bc8; }}
.tool-view-names {{ display: none; }}
.tool-view-names.expanded {{ display: block; }}
.tool-view-full {{ display: none; }}
.tool-view-full.expanded {{ display: block; }}
.tool-names-grid {{ display: flex; flex-wrap: wrap; gap: 6px; padding: 10px; background: #f8f9fa; border-radius: 4px; }}
.tool-name-item {{ background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 3px; font-size: 12px; font-family: monospace; }}
/* Gantt Timeline */
.gantt-panel {{ background: white; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.gantt-legend {{ display: flex; gap: 16px; padding: 4px 0 8px; font-size: 12px; color: #666; }}
.gantt-legend-item {{ display: flex; align-items: center; gap: 4px; }}
.gantt-legend-color {{ display: inline-block; width: 14px; height: 10px; border-radius: 2px; }}
.gantt-chart {{ max-height: 500px; overflow-y: auto; padding-top: 5px; }}
.gantt-agent-header {{ font-size: 12px; font-weight: bold; color: #4a90d9; padding: 8px 0 2px 4px; border-bottom: 1px solid #e8e8e8; margin-top: 4px; }}
.gantt-row {{ display: flex; align-items: center; height: 28px; margin-bottom: 2px; }}
.gantt-label {{ width: 320px; flex-shrink: 0; font-size: 12px; color: #333; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding-right: 8px; font-family: 'Consolas', 'Monaco', monospace; }}
.gantt-tree {{ color: #aaa; }}
.gantt-track {{ flex: 1; position: relative; height: 20px; background: #f8f9fa; border-radius: 3px; }}
.gantt-bar {{ position: absolute; top: 1px; height: 18px; border-radius: 3px; cursor: pointer; transition: box-shadow 0.2s; display: flex; overflow: hidden; min-width: 4px; }}
.gantt-bar:hover {{ box-shadow: 0 0 0 2px #4a90d9; z-index: 1; }}
.gantt-seg {{ height: 100%; min-width: 1px; }}
.gantt-seg-llm {{ background: #4a90d9; }}
.gantt-seg-tool {{ background: #f57c00; }}
.gantt-seg-wait {{ background: #bdbdbd; }}
.gantt-bar.depth-parent {{ background: #e3f2fd; }}
.gantt-bar.depth-0 {{ background: #f3e5f5; }}
.gantt-bar.depth-1 {{ background: #ede7f6; }}
.gantt-bar.depth-2 {{ background: #e8def8; }}
/* Gantt Expand Button & Content */
.gantt-row-wrapper {{ margin-bottom: 2px; }}
.gantt-expand-btn {{ background: none; border: none; cursor: pointer; font-size: 9px; color: #888; padding: 0 6px 0 0; line-height: 1; }}
.gantt-expand-btn:hover {{ color: #4a90d9; }}
.gantt-expand-content {{ padding: 2px 0 6px 0; border-left: 2px solid #e0e0e0; margin-left: 8px; }}
.gantt-expand-content .gantt-row {{ height: 22px; }}
.gantt-expand-content .gantt-label {{ font-size: 11px; width: 310px; padding-left: 12px; }}
.gantt-expand-content .gantt-track {{ height: 16px; }}
.gantt-expand-content .gantt-bar {{ height: 14px; top: 1px; }}
/* Gantt Tooltip */
.gantt-tooltip {{ position: fixed; pointer-events: none; background: #1a1a2e; color: white; padding: 12px 16px; border-radius: 8px; font-size: 13px; line-height: 1.8; z-index: 2000; box-shadow: 0 4px 16px rgba(0,0,0,0.3); opacity: 0; transition: opacity 0.15s; max-width: 500px; }}
.gantt-tooltip.visible {{ opacity: 1; }}
.gantt-tooltip .tt-name {{ font-weight: bold; font-size: 14px; margin-bottom: 4px; color: #82b1ff; }}
.gantt-tooltip .tt-row {{ display: flex; justify-content: space-between; gap: 20px; }}
.gantt-tooltip .tt-label {{ color: #aaa; }}
.gantt-tooltip .tt-value {{ font-weight: bold; }}
.gantt-tooltip .tt-tools {{ color: #f57c00; font-size: 12px; font-weight: normal; word-break: break-all; }}
.gantt-tooltip .tt-content {{ margin-top: 8px; padding-top: 8px; border-top: 1px solid #333; white-space: pre-wrap; word-break: break-word; font-size: 12px; line-height: 1.6; max-height: 300px; overflow-y: auto; color: #ddd; }}
.gantt-tooltip .tt-bar {{ height: 6px; border-radius: 3px; background: #333; margin: 6px 0 2px; overflow: hidden; display: flex; }}
.gantt-tooltip .tt-bar-llm {{ background: #4a90d9; }}
.gantt-tooltip .tt-bar-tool {{ background: #f57c00; }}
/* Tab Navigation */
.tab-nav {{ display: flex; flex-wrap: wrap; gap: 0; margin-bottom: 0; border-bottom: 2px solid #e0e0e0; padding: 0 5px; }}
.tab-btn {{ padding: 10px 16px; border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; background: #f0f0f0; cursor: pointer; font-size: 13px; margin-bottom: -2px; color: #666; transition: all 0.2s; }}
.tab-btn:hover {{ background: #e8e8e8; }}
.tab-btn.active {{ background: white; color: #4a90d9; font-weight: bold; border-color: #e0e0e0; border-bottom-color: white; }}
.tab-badge {{ background: #e0e0e0; color: #666; padding: 2px 7px; border-radius: 10px; font-size: 11px; margin-left: 4px; }}
.tab-btn.active .tab-badge {{ background: #4a90d9; color: white; }}
.tab-panel {{ display: none; padding-top: 15px; }}
.tab-panel.active {{ display: block; }}
/* Timing Panel */
.timing-panel {{ background: white; border-radius: 8px; padding: 15px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.timing-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
.timing-header h3 {{ color: #4a90d9; font-size: 14px; }}
.timing-controls {{ display: flex; gap: 8px; }}
.sort-btn {{ padding: 4px 10px; background: #e0e0e0; border: none; border-radius: 4px; cursor: pointer; font-size: 12px; }}
.sort-btn:hover {{ background: #d0d0d0; }}
.sort-btn.active {{ background: #4a90d9; color: white; }}
.timing-list {{ max-height: 300px; overflow-y: auto; }}
.timing-item {{ display: flex; align-items: center; padding: 8px 12px; border-bottom: 1px solid #e0e0e0; cursor: pointer; }}
.timing-item:hover {{ background: #f8f9fa; }}
.timing-item-num {{ width: 130px; font-weight: bold; color: #4a90d9; }}
.timing-agent {{ font-size: 11px; color: #7b1fa2; font-weight: bold; display: block; line-height: 1; margin-bottom: 1px; }}
.timing-item-times {{ width: 260px; display: flex; }}
.timing-item-time {{ font-size: 12px; width: 85px; }}
.timing-item-time.llm {{ color: #388e3c; }}
.timing-item-time.tool {{ color: #f57c00; }}
.timing-item-time.total {{ color: #4a90d9; font-weight: bold; }}
.timing-item-content {{ flex: 1; font-size: 13px; color: #666; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.timing-item-content:hover {{ overflow: visible; white-space: normal; }}
.timing-item-tools {{ width: 160px; font-size: 11px; color: #f57c00; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 8px; }}
.timing-item-tools:hover {{ overflow: visible; white-space: normal; }}
.global-ref {{ font-size: 10px; color: #aaa; font-weight: normal; }}
/* Go to Top */
.go-top-btn {{ position: fixed; bottom: 30px; right: 30px; width: 44px; height: 44px; background: #4a90d9; color: white; border: none; border-radius: 50%; cursor: pointer; font-size: 20px; line-height: 44px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.2); opacity: 0; visibility: hidden; transition: opacity 0.3s, visibility 0.3s, background 0.2s; z-index: 1000; }}
.go-top-btn:hover {{ background: #3a7bc8; }}
.go-top-btn.visible {{ opacity: 1; visibility: visible; }}
/* Agent Block (single subagent collapsible) */
.agent-block {{ margin: 10px 0 15px 20px; border-left: 3px solid #7b1fa2; padding-left: 0; }}
.agent-block .collapsible {{ background: #f3e5f5; border-radius: 0 4px 4px 0; }}
.agent-block .collapsible:hover {{ background: #e1d5e7; }}
.agent-block .collapsible-content {{ padding: 10px 0 10px 10px; }}
/* Page Tab Navigation */
.page-tab-nav {{ display: flex; gap: 0; margin-bottom: 0; border-bottom: 2px solid #e0e0e0; padding: 0 5px; }}
.page-tab-btn {{ padding: 10px 20px; border: 1px solid transparent; border-bottom: none; border-radius: 8px 8px 0 0; background: #f0f0f0; cursor: pointer; font-size: 14px; margin-bottom: -2px; color: #666; transition: all 0.2s; }}
.page-tab-btn:hover {{ background: #e8e8e8; }}
.page-tab-btn.active {{ background: white; color: #4a90d9; font-weight: bold; border-color: #e0e0e0; border-bottom-color: white; }}
.page-tab-panel {{ display: none; padding-top: 15px; }}
.page-tab-panel.active {{ display: block; }}
/* Statistics Panel */
.stat-cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.stat-card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center; }}
.stat-card .stat-value {{ font-size: 24px; font-weight: bold; color: #4a90d9; }}
.stat-card .stat-label {{ font-size: 12px; color: #666; margin-top: 4px; }}
.stat-section {{ background: white; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
.stat-section h3 {{ color: #1a1a2e; margin-bottom: 15px; font-size: 16px; border-bottom: 2px solid #4a90d9; padding-bottom: 8px; }}
.stat-row {{ display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid #f0f0f0; }}
.stat-row:last-child {{ border-bottom: none; }}
.stat-row .stat-name {{ font-weight: 500; }}
.stat-row .stat-val {{ color: #4a90d9; font-weight: bold; }}
.tool-bar {{ height: 8px; background: #e0e0e0; border-radius: 4px; overflow: hidden; margin-top: 4px; }}
.tool-bar-fill {{ height: 100%; background: #4a90d9; border-radius: 4px; transition: width 0.3s; }}
.stat-section table {{ width: 100%; border-collapse: collapse; }}
.stat-section th {{ background: #4a90d9; color: white; padding: 10px 12px; text-align: left; font-size: 13px; }}
.stat-section td {{ padding: 10px 12px; border-bottom: 1px solid #e0e0e0; font-size: 13px; }}
.stat-section tr:hover {{ background: #f8f9fa; }}
.stat-section th.sortable {{ cursor: pointer; user-select: none; white-space: nowrap; }}
.stat-section th.sortable:hover {{ background: #3a7bc8; }}
.stat-section th.sortable.sort-asc::after {{ content: ' ▲'; font-size: 10px; }}
.stat-section th.sortable.sort-desc::after {{ content: ' ▼'; font-size: 10px; }}
/* Timing Chart */
.timing-chart-wrapper {{ margin-bottom: 10px; }}
.chart-legend {{ display: flex; gap: 16px; margin-bottom: 8px; font-size: 12px; color: #666; }}
.chart-legend-item {{ display: flex; align-items: center; gap: 4px; }}
.chart-legend-color {{ width: 12px; height: 12px; border-radius: 2px; }}
.chart-legend-llm {{ background: #4a90d9; }}
.chart-legend-tool {{ background: #f57c00; }}
.chart-toggle {{ cursor: pointer; padding: 2px 8px; border-radius: 4px; border: 1px solid transparent; transition: all 0.2s; user-select: none; }}
.chart-toggle:hover {{ background: #f0f0f0; }}
.chart-toggle.active {{ border-color: #ccc; }}
.chart-toggle:not(.active) {{ opacity: 0.4; }}
.timing-chart {{ display: flex; align-items: flex-end; gap: 2px; height: 200px; padding: 0 4px; border-bottom: 1px solid #e0e0e0; position: relative; }}
.timing-chart.dense {{ gap: 0; }}
.chart-bar-col {{ display: flex; flex-direction: column; align-items: center; flex: 1; min-width: 3px; cursor: pointer; }}
.timing-chart.dense .chart-bar-col {{ min-width: 0; }}
.chart-bar {{ display: flex; flex-direction: column; width: 100%; justify-content: flex-end; }}
.chart-bar-llm {{ background: #4a90d9; border-radius: 2px 2px 0 0; min-height: 1px; transition: opacity 0.15s, height 0.3s; }}
.chart-bar-tool {{ background: #f57c00; border-radius: 2px 2px 0 0; min-height: 1px; transition: opacity 0.15s, height 0.3s; }}
.chart-bar-col:hover .chart-bar-llm, .chart-bar-col:hover .chart-bar-tool {{ opacity: 0.8; }}
.timing-chart.hide-llm .chart-bar-llm {{ height: 0 !important; min-height: 0 !important; }}
.timing-chart.hide-tool .chart-bar-tool {{ height: 0 !important; min-height: 0 !important; }}
.chart-pxx-line {{ position: absolute; left: 0; right: 0; border-top: 1px dashed #999; pointer-events: none; z-index: 1; }}
.chart-pxx-label {{ position: absolute; right: 4px; top: -14px; font-size: 10px; color: #666; background: rgba(255,255,255,0.85); padding: 0 4px; border-radius: 2px; white-space: nowrap; }}
.chart-x-label {{ font-size: 9px; color: #999; margin-top: 2px; }}
.chart-tooltip {{ position: fixed; pointer-events: none; background: #1a1a2e; color: white; padding: 10px 14px; border-radius: 8px; font-size: 13px; line-height: 1.8; z-index: 2000; box-shadow: 0 4px 16px rgba(0,0,0,0.3); opacity: 0; transition: opacity 0.15s; }}
.chart-tooltip.visible {{ opacity: 1; }}
.chart-tooltip .tt-name {{ font-weight: bold; color: #82b1ff; margin-bottom: 2px; }}
.chart-tooltip .tt-row {{ display: flex; justify-content: space-between; gap: 16px; }}
.chart-tooltip .tt-label {{ color: #aaa; }}
.chart-tooltip .tt-value {{ font-weight: bold; }}
/* Parallel Group (tabbed subagents) */
.parallel-group {{ margin: 10px 0 15px 20px; border-left: 3px solid #7b1fa2; padding: 0; }}
.parallel-header {{ padding: 8px 12px; background: #f3e5f5; border-radius: 0 4px 0 0; }}
.parallel-group .tab-nav {{ border-bottom: 2px solid #e0e0e0; padding: 0 5px; background: #faf5fc; }}
.parallel-group .tab-panel {{ padding: 10px 0 10px 10px; }}
/* Depth colors for nested agents */
.agent-block.depth-1, .parallel-group.depth-1 {{ border-left-color: #9c27b0; }}
.agent-block.depth-1 .collapsible, .parallel-group.depth-1 .parallel-header {{ background: #ede7f6; }}
.agent-block.depth-2, .parallel-group.depth-2 {{ border-left-color: #ba68c8; }}
.agent-block.depth-2 .collapsible, .parallel-group.depth-2 .parallel-header {{ background: #e8def8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="back-link"><a href="index.html">&#8592; Back to Index</a></div>
        <div class="header">
            <h1>Session: {session_id_short}</h1>
            <div class="meta">Model: {model_name} | Iterations: {total_iterations} | {start_time} - {end_time}</div>
            <div class="meta">Duration: {session_duration} | LLM: {total_llm_duration} | Tool: {total_tool_duration} | Avg LLM: {avg_llm_per_iter}</div>
            <div class="meta">Iterations: {total_iterations_count} | Model Calls: {total_model_calls} | Tool Calls: {total_tool_calls}</div>
            <div class="meta">Tokens: {session_input_tokens:,} input | {session_output_tokens:,} output | {session_total_tokens:,} total | {session_cache_tokens:,} cache</div>
        </div>
        <div class="page-tab-nav">
            <button class="page-tab-btn active" onclick="switchPageTab('detail')">Detail</button>
            <button class="page-tab-btn" onclick="switchPageTab('statistics')">Statistics</button>
        </div>
        <div class="page-tab-panel active" id="tab-detail">
            {gantt_html}
            {timing_list_html}
            {iterations_html}
        </div>
        <div class="page-tab-panel" id="tab-statistics">
            {session_statistics_html}
        </div>
    </div>
    <script>
        function toggleCollapsible(element) {{
            const content = element.nextElementSibling;
            const icon = element.querySelector('.toggle-icon');
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                icon.classList.remove('rotated');
            }} else {{
                content.classList.add('expanded');
                icon.classList.add('rotated');
            }}
        }}
        function copyToClipboard(btn, contentId) {{
            const content = document.getElementById(contentId).textContent;
            navigator.clipboard.writeText(content).then(() => {{
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = 'Copy';
                    btn.classList.remove('copied');
                }}, 2000);
            }});
        }}
        function copyRequestBody(btn) {{
            const hiddenPre = btn.nextElementSibling;
            const content = hiddenPre.textContent;
            navigator.clipboard.writeText(content).then(() => {{
                btn.textContent = 'Copied!';
                btn.classList.add('copied');
                setTimeout(() => {{
                    btn.textContent = 'Copy Body';
                    btn.classList.remove('copied');
                }}, 2000);
            }});
        }}
        function toggleToolView(btn, namesId, fullId) {{
            const namesDiv = document.getElementById(namesId);
            const fullDiv = document.getElementById(fullId);
            if (namesDiv.classList.contains('expanded')) {{
                namesDiv.classList.remove('expanded');
                fullDiv.classList.add('expanded');
                btn.textContent = 'Toggle: Names';
            }} else {{
                namesDiv.classList.add('expanded');
                fullDiv.classList.remove('expanded');
                btn.textContent = 'Toggle: Full';
            }}
        }}
        function switchTab(agentKey) {{
            document.querySelectorAll('.tab-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.tab === agentKey);
            }});
            document.querySelectorAll('.tab-panel').forEach(panel => {{
                panel.classList.toggle('active', panel.dataset.agentKey === agentKey);
            }});
            document.querySelectorAll('.gantt-bar').forEach(bar => {{
                bar.style.boxShadow = bar.dataset.agentKey === agentKey
                    ? '0 0 0 2px #4a90d9' : '';
            }});
        }}
        function switchPageTab(tabId) {{
            document.querySelectorAll('.page-tab-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.getAttribute('onclick').includes("'" + tabId + "'"));
            }});
            document.querySelectorAll('.page-tab-panel').forEach(panel => {{
                panel.classList.toggle('active', panel.id === 'tab-' + tabId);
            }});
        }}
        function showChartTooltip(event, el) {{
            const tt = document.getElementById('chartTooltip');
            if (!tt) return;
            const seq = el.dataset.seq;
            const llm = el.dataset.llm;
            const tool = el.dataset.tool;
            const total = el.dataset.total;
            tt.innerHTML = `
                <div class="tt-name">#${{seq}}</div>
                <div class="tt-row"><span class="tt-label">LLM Time</span><span class="tt-value">${{llm}}</span></div>
                <div class="tt-row"><span class="tt-label">Tool Time</span><span class="tt-value">${{tool}}</span></div>
                <div class="tt-row"><span class="tt-label">Total</span><span class="tt-value">${{total}}</span></div>
            `;
            tt.style.left = (event.clientX + 12) + 'px';
            tt.style.top = (event.clientY - 10) + 'px';
            tt.classList.add('visible');
        }}
        function moveChartTooltip(event) {{
            const tt = document.getElementById('chartTooltip');
            if (tt) {{ tt.style.left = (event.clientX + 12) + 'px'; tt.style.top = (event.clientY - 10) + 'px'; }}
        }}
        function hideChartTooltip() {{
            const tt = document.getElementById('chartTooltip');
            if (tt) tt.classList.remove('visible');
        }}
        function toggleChartSeries(el) {{
            const series = el.dataset.series;
            el.classList.toggle('active');
            const wrapper = el.closest('.timing-chart-wrapper');
            const chart = wrapper ? wrapper.querySelector('.timing-chart') : null;
            if (!chart) return;
            const showLlm = wrapper.querySelector('[data-series="llm"]').classList.contains('active');
            const showTool = wrapper.querySelector('[data-series="tool"]').classList.contains('active');
            chart.classList.toggle('hide-llm', !showLlm);
            chart.classList.toggle('hide-tool', !showTool);

            const cols = chart.querySelectorAll('.chart-bar-col');
            const chartH = 200;
            let maxVal = 0;
            const vals = [];
            cols.forEach(col => {{
                const l = parseInt(col.dataset.llmMs) || 0;
                const t = parseInt(col.dataset.toolMs) || 0;
                const v = (showLlm ? l : 0) + (showTool ? t : 0);
                vals.push({{l, t, v}});
                if (v > maxVal) maxVal = v;
            }});
            if (maxVal <= 0) maxVal = 1;

            cols.forEach((col, i) => {{
                const llmBar = col.querySelector('.chart-bar-llm');
                const toolBar = col.querySelector('.chart-bar-tool');
                const d = vals[i];
                llmBar.style.height = ((d.l / maxVal) * chartH) + 'px';
                toolBar.style.height = ((d.t / maxVal) * chartH) + 'px';
                const totalMs = d.v;
                col.dataset.total = formatMsDuration(totalMs);
            }});

            const sorted = vals.map(v => v.v).filter(v => v > 0).sort((a, b) => a - b);
            if (sorted.length > 0) {{
                const pxxMap = [
                    [50, 'p50'], [90, 'p90'], [95, 'p95'], [99, 'p99']
                ];
                pxxMap.forEach(([p, cls]) => {{
                    const val = percentile(sorted, p);
                    const pct = (val / maxVal) * 100;
                    const line = chart.querySelector('.chart-pxx-' + cls);
                    if (line) {{
                        line.style.bottom = pct + '%';
                        line.querySelector('.chart-pxx-label').textContent = cls.toUpperCase() + ': ' + formatMsDuration(val);
                    }}
                }});
            }}
        }}
        function percentile(sorted, p) {{
            if (!sorted.length) return 0;
            const k = (sorted.length - 1) * p / 100;
            const f = Math.floor(k);
            const c = f + 1;
            if (c >= sorted.length) return sorted[f];
            return sorted[f] + (k - f) * (sorted[c] - sorted[f]);
        }}
        function formatMsDuration(ms) {{
            const s = ms / 1000;
            if (s <= 0) return 'N/A';
            if (s < 1) return Math.round(ms) + 'ms';
            if (s < 60) return s.toFixed(1) + 's';
            const m = Math.floor(s / 60);
            const sec = Math.round(s % 60);
            return m + 'm ' + sec + 's';
        }}
        function sortToolTable(th, key) {{
            const table = th.closest('table');
            const tbody = table.querySelector('tbody') || table;
            const rows = Array.from(tbody.querySelectorAll('tr[data-name]'));
            const headers = table.querySelectorAll('th.sortable');
            const isAsc = th.classList.contains('sort-desc');
            headers.forEach(h => h.classList.remove('sort-asc', 'sort-desc'));
            th.classList.add(isAsc ? 'sort-asc' : 'sort-desc');
            rows.sort((a, b) => {{
                let va, vb;
                if (key === 'name') {{ va = a.dataset.name; vb = b.dataset.name; }}
                else if (key === 'ratio' || key === 'calls') {{ va = +a.dataset.count; vb = +b.dataset.count; }}
                else if (key === 'total') {{ va = +a.dataset.totalMs; vb = +b.dataset.totalMs; }}
                else if (key === 'avg') {{ va = +a.dataset.avgMs; vb = +b.dataset.avgMs; }}
                if (typeof va === 'string') return isAsc ? va.localeCompare(vb) : vb.localeCompare(va);
                return isAsc ? va - vb : vb - va;
            }});
            rows.forEach(r => tbody.appendChild(r));
        }}
        function sortTimingList(sortType, clickedBtn) {{
            const timingPanel = clickedBtn.closest('.timing-panel');
            const list = timingPanel ? timingPanel.querySelector('.timing-list') : document.querySelector('.timing-list');
            if (!list) return;
            const controls = clickedBtn.closest('.timing-controls');
            if (controls) {{
                controls.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
                clickedBtn.classList.add('active');
            }}
            const items = Array.from(list.querySelectorAll('.timing-item'));
            if (sortType === 'iteration') {{
                items.sort((a, b) => parseInt(a.dataset.globalNum) - parseInt(b.dataset.globalNum));
            }} else if (sortType === 'llm') {{
                items.sort((a, b) => parseFloat(b.dataset.llm) - parseFloat(a.dataset.llm));
            }} else if (sortType === 'tool') {{
                items.sort((a, b) => parseFloat(b.dataset.tool) - parseFloat(a.dataset.tool));
            }} else if (sortType === 'total') {{
                items.sort((a, b) => parseFloat(b.dataset.total) - parseFloat(a.dataset.total));
            }}
            items.forEach(item => list.appendChild(item));
        }}
        function jumpToIteration(globalNum) {{
            const block = document.querySelector(`.iteration-block[data-global-iteration="${{globalNum}}"]`);
            if (!block) return;
            // 展开所有包含该 block 的折叠区域
            let el = block.parentElement;
            while (el) {{
                if (el.classList.contains('collapsible-content') && !el.classList.contains('expanded')) {{
                    el.classList.add('expanded');
                    const icon = el.previousElementSibling?.querySelector('.toggle-icon');
                    if (icon) icon.classList.add('rotated');
                }}
                if (el.classList.contains('tab-panel') && !el.classList.contains('active')) {{
                    const agentKey = el.dataset.agentKey;
                    if (agentKey) switchTab(agentKey);
                }}
                el = el.parentElement;
            }}
            requestAnimationFrame(() => {{
                block.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
                block.style.boxShadow = '0 0 0 3px #4a90d9';
                setTimeout(() => block.style.boxShadow = '', 2000);
            }});
        }}
        document.addEventListener('DOMContentLoaded', function() {{
            const btn = document.getElementById('goTopBtn');
            if (!btn) return;
            window.addEventListener('scroll', function() {{
                if (window.scrollY > 300) {{
                    btn.classList.add('visible');
                }} else {{
                    btn.classList.remove('visible');
                }}
            }});
            btn.addEventListener('click', function() {{
                window.scrollTo({{ top: 0, behavior: 'smooth' }});
            }});
        }});
        function showGanttTooltip(event, bar) {{
            const tt = document.getElementById('ganttTooltip');
            const name = bar.dataset.agentName;
            const fullContent = bar.dataset.fullContent;
            const toolCalls = bar.dataset.toolCalls;
            const reasoningChars = bar.dataset.reasoningChars || '0';
            const contentChars = bar.dataset.contentChars || '0';
            const toolCallsChars = bar.dataset.toolCallsChars || '0';
            const inputTokens = bar.dataset.inputTokens || '0';
            const outputTokens = bar.dataset.outputTokens || '0';
            const totalTokens = bar.dataset.totalTokens || '0';
            const cacheTokens = bar.dataset.cacheTokens || '0';
            const charsHtml = `
                <div class="tt-row"><span class="tt-label">Reasoning Chars</span><span class="tt-value">${{Number(reasoningChars).toLocaleString()}}</span></div>
                <div class="tt-row"><span class="tt-label">Content Chars</span><span class="tt-value">${{Number(contentChars).toLocaleString()}}</span></div>
                <div class="tt-row"><span class="tt-label">Tool Calls Chars</span><span class="tt-value">${{Number(toolCallsChars).toLocaleString()}}</span></div>
            `;
            const tokensHtml = `
                <div class="tt-row"><span class="tt-label">Input Tokens</span><span class="tt-value">${{Number(inputTokens).toLocaleString()}}</span></div>
                <div class="tt-row"><span class="tt-label">Output Tokens</span><span class="tt-value">${{Number(outputTokens).toLocaleString()}}</span></div>
                <div class="tt-row"><span class="tt-label">Cache Tokens</span><span class="tt-value">${{Number(cacheTokens).toLocaleString()}}</span></div>
                <div class="tt-row"><span class="tt-label">Total Tokens</span><span class="tt-value">${{Number(totalTokens).toLocaleString()}}</span></div>
            `;

            if (fullContent !== undefined && fullContent !== '') {{
                // Detail row: show timing stats + chars + tools + content
                const llm = bar.dataset.llm;
                const tool = bar.dataset.tool;
                const total = bar.dataset.total;
                const llmPct = bar.dataset.llmPct;
                const toolPct = bar.dataset.toolPct;
                const timeRange = bar.dataset.timeRange;
                const tcHtml = toolCalls
                    ? `<div class="tt-row"><span class="tt-label">Tools</span><span class="tt-value tt-tools">${{toolCalls}}</span></div>`
                    : '';
                tt.innerHTML = `
                    <div class="tt-name">${{name}}</div>
                    <div class="tt-bar"><div class="tt-bar-llm" style="width:${{llmPct}}%"></div><div class="tt-bar-tool" style="width:${{toolPct}}%"></div></div>
                    <div class="tt-row"><span class="tt-label">LLM Time</span><span class="tt-value">${{llm}}</span></div>
                    <div class="tt-row"><span class="tt-label">Tool Time</span><span class="tt-value">${{tool}}</span></div>
                    <div class="tt-row"><span class="tt-label">Total Time</span><span class="tt-value">${{total}}</span></div>
                    <div class="tt-row"><span class="tt-label">Time Range</span><span class="tt-value">${{timeRange}}</span></div>
                    ${{charsHtml}}
                    ${{tokensHtml}}
                    ${{tcHtml}}
                    <div class="tt-content">${{fullContent}}</div>
                `;
            }} else {{
                // Agent-level bar: show timing stats + chars
                const iters = bar.dataset.iterCount;
                const llm = bar.dataset.llm;
                const tool = bar.dataset.tool;
                const total = bar.dataset.total;
                const llmPct = bar.dataset.llmPct;
                const toolPct = bar.dataset.toolPct;
                const timeRange = bar.dataset.timeRange;
                tt.innerHTML = `
                    <div class="tt-name">${{name}}</div>
                    <div class="tt-row"><span class="tt-label">Iterations</span><span class="tt-value">${{iters}}</span></div>
                    <div class="tt-bar"><div class="tt-bar-llm" style="width:${{llmPct}}%"></div><div class="tt-bar-tool" style="width:${{toolPct}}%"></div></div>
                    <div class="tt-row"><span class="tt-label">LLM Time</span><span class="tt-value">${{llm}}</span></div>
                    <div class="tt-row"><span class="tt-label">Tool Time</span><span class="tt-value">${{tool}}</span></div>
                    <div class="tt-row"><span class="tt-label">Total Time</span><span class="tt-value">${{total}}</span></div>
                    <div class="tt-row"><span class="tt-label">Time Range</span><span class="tt-value">${{timeRange}}</span></div>
                    ${{charsHtml}}
                    ${{tokensHtml}}
                `;
            }}
            tt.classList.add('visible');
            moveGanttTooltip(event);
        }}
        function moveGanttTooltip(event) {{
            const tt = document.getElementById('ganttTooltip');
            let x = event.clientX + 15;
            let y = event.clientY + 15;
            if (x + tt.offsetWidth > window.innerWidth - 10) x = event.clientX - tt.offsetWidth - 15;
            if (y + tt.offsetHeight > window.innerHeight - 10) y = event.clientY - tt.offsetHeight - 15;
            tt.style.left = x + 'px';
            tt.style.top = y + 'px';
        }}
        function hideGanttTooltip() {{
            document.getElementById('ganttTooltip').classList.remove('visible');
        }}
        function toggleGanttExpand(id, btn) {{
            const el = document.getElementById(id);
            if (!el) return;
            if (el.style.display === 'none') {{
                el.style.display = 'block';
                if (btn) btn.innerHTML = '&#9660;';
            }} else {{
                el.style.display = 'none';
                if (btn) btn.innerHTML = '&#9654;';
            }}
        }}
    </script>
    <button id="goTopBtn" class="go-top-btn" title="Go to Top">&#8593;</button>
    <div id="ganttTooltip" class="gantt-tooltip"></div>
    <div id="chartTooltip" class="chart-tooltip"></div>
</body>
</html>
"""

ITERATION_DETAIL_TEMPLATE = """
<div class="iteration-block" data-iteration="{local_num}" data-global-iteration="{global_num}">
    <div class="iteration-header">
        #{local_num} {depth_indicator}
        <span class="time-stats">LLM: {llm_duration} | Tool: {tool_duration} | Tokens: {iter_input_tokens:,} in / {iter_output_tokens:,} out / {iter_total_tokens:,} total</span>
        {copy_body_btn}
        <pre style="display: none;" id="{body_id}">{body_json}</pre>
    </div>
    <div class="iteration-content">
        {request_html}
        {response_html}
    </div>
</div>
"""

TIMING_LIST_TEMPLATE = """
<div class="timing-panel">
    <div class="timing-header">
        <h3>Timing ({total_iterations} iterations)</h3>
        <div class="timing-controls">
            <button class="sort-btn active" data-sort="iteration" onclick="sortTimingList('iteration', this)">Iteration</button>
            <button class="sort-btn" data-sort="llm" onclick="sortTimingList('llm', this)">LLM Time</button>
            <button class="sort-btn" data-sort="tool" onclick="sortTimingList('tool', this)">Tool Time</button>
            <button class="sort-btn" data-sort="total" onclick="sortTimingList('total', this)">Total</button>
        </div>
    </div>
    <div class="timing-list" id="{timing_list_id}">
        {timing_items_html}
    </div>
</div>
"""

TIMING_ITEM_TEMPLATE = """
<div class="timing-item" data-num="{local_num}" data-global-num="{global_num}" data-llm="{llm_seconds}" data-tool="{tool_seconds}" data-total="{total_seconds}" onclick="jumpToIteration({global_num})">
    <div class="timing-item-num"><span class="timing-agent">{agent_label}</span> #{local_num} <span class="global-ref">({global_num})</span></div>
    <div class="timing-item-times">
        <span class="timing-item-time total">Total: {total_duration}</span>
        <span class="timing-item-time llm">LLM: {llm_duration}</span>
        <span class="timing-item-time tool">Tool: {tool_duration}</span>
    </div>
    <div class="timing-item-tools" title="{tool_names}">{tool_names}</div>
    <div class="timing-item-content" title="{content_full}">{content_preview}</div>
</div>
"""

TOOL_NAME_ITEM_TEMPLATE = """<span class="tool-name-item">{name}</span>"""

TOOLS_SECTION_TEMPLATE = """
<div style="margin-top: 10px;">
    <div class="collapsible" onclick="toggleCollapsible(this)">
        <span class="toggle-icon">&#9654;</span> Tools ({tool_count})
        <span class="char-count">{tools_chars} chars</span>
    </div>
    <div class="collapsible-content">
        <button class="toggle-view-btn" onclick="toggleToolView(this, '{names_id}', '{full_id}')">
            Toggle: Names
        </button>
        <div id="{names_id}" class="tool-view-names expanded">
            <div class="tool-names-grid">
                {tool_names_html}
            </div>
        </div>
        <div id="{full_id}" class="tool-view-full">
            {tools_html}
        </div>
    </div>
</div>
"""

GANTT_PANEL_TEMPLATE = """
<div class="gantt-panel">
    <div class="collapsible" onclick="toggleCollapsible(this)">
        <span class="toggle-icon rotated">&#9654;</span> Agent Timeline ({agent_count} rows, {total_duration})
    </div>
    <div class="collapsible-content expanded">
        <div class="gantt-legend">
            <span class="gantt-legend-item"><span class="gantt-legend-color" style="background:#4a90d9"></span>LLM Call</span>
            <span class="gantt-legend-item"><span class="gantt-legend-color" style="background:#f57c00"></span>Tool Execution</span>
        </div>
        <div class="gantt-chart">
            {gantt_bars_html}
        </div>
    </div>
</div>
"""

AGENT_BLOCK_TEMPLATE = """
<div class="agent-block depth-{depth_class}">
    <div class="collapsible" onclick="toggleCollapsible(this)">
        <span class="toggle-icon rotated">&#9654;</span>
        <span class="label subagent">{label}</span>
        <span class="char-count">{iteration_count} iters | {duration}</span>
    </div>
    <div class="collapsible-content expanded">
        {content_html}
    </div>
</div>
"""

PARALLEL_GROUP_TEMPLATE = """
<div class="parallel-group">
    <div class="parallel-header">
        <span class="label subagent">Parallel Agents ({agent_count})</span>
        <span class="char-count">{duration}</span>
    </div>
    {tab_nav_html}
    {tab_content_html}
</div>
"""

GANTT_BAR_TEMPLATE = """
<div class="gantt-row">
    <div class="gantt-label" title="{full_label}">{label}</div>
    <div class="gantt-track">
        <div class="gantt-bar depth-{depth_class}"
             style="left: {left_pct}%; width: {width_pct}%;"
             data-agent-key="{agent_key}"
             onclick="switchTab('{agent_key}')"
             title="{full_label}: {duration} ({iteration_count} iters)">
            <span class="gantt-bar-text">{bar_text}</span>
        </div>
    </div>
</div>
"""

TAB_NAV_TEMPLATE = """
<div class="tab-nav">
    {tab_buttons_html}
</div>
"""

TAB_BUTTON_TEMPLATE = """
<button class="tab-btn{active_class}" data-tab="{agent_key}" onclick="switchTab('{agent_key}')">
    {label} <span class="tab-badge">{iteration_count}</span>
</button>
"""

TAB_CONTENT_WRAPPER_TEMPLATE = """
<div class="tab-panels">
    {tab_panels_html}
</div>
"""

TAB_PANEL_TEMPLATE = """
<div class="tab-panel{active_class}" id="tab-{agent_key}" data-agent-key="{agent_key}">
    {timing_list_html}
    {iterations_html}
</div>
"""
