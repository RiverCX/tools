"""CLI主入口"""

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from .analyzer import ChainAnalyzer
from .loader import LogLoader, find_latest_log
from .models import AnalysisResult
from .parser import TraceParser
from .reporter import HTMLReporter


class LLMTraceAnalyzer:
    def __init__(self, log_file_path: str):
        self.file_path = log_file_path

    def run(
        self,
        output_path: str = "llm_trace_report.html",
        verbose: bool = False,
        session_filter: Optional[str] = None,
    ) -> bool:
        try:
            loader = LogLoader(self.file_path)
            traces = loader.load()
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return False

        if session_filter:
            traces = self._filter_traces_for_session(traces, session_filter)

        if not traces:
            print("No LLM_IO_TRACE entries found in log file.")
            return False

        parser = TraceParser(traces)
        requests, responses = parser.parse()

        analyzer = ChainAnalyzer(requests, responses)
        result = analyzer.analyze()

        if session_filter:
            result = self._filter_result_for_session(result, session_filter)

        if verbose:
            self._print_summary(result)

        reporter = HTMLReporter(self.file_path)
        reporter.generate(result, output_path)
        print(f"Report generated: {output_path}")

        return True

    def _filter_traces_for_session(self, traces: list, session_filter: str) -> list:
        parent_traces = [t for t in traces if t["session_id"] == session_filter]

        subagent_session_ids = set()
        self._collect_subagent_sessions(session_filter, traces, subagent_session_ids)

        subagent_traces = [t for t in traces if t["session_id"] in subagent_session_ids]

        return parent_traces + subagent_traces

    def _collect_subagent_sessions(
        self,
        parent_session: str,
        traces: list,
        collected: set,
    ) -> None:
        """递归收集所有相关的 subAgent session"""
        # session_id 包含父 session ID，如 <parent>_subagent_<task_id> 或 <parent>_fork_agent_<task_id>
        for t in traces:
            sid = t.get("session_id", "")
            if sid.startswith(parent_session + "_subagent_") or sid.startswith(
                parent_session + "_fork_agent_"
            ):
                if sid not in collected and sid != parent_session:
                    collected.add(sid)
                    # 递归处理 subAgent 可能调用的其他 subAgent
                    self._collect_subagent_sessions(sid, traces, collected)

    def _filter_result_for_session(
        self, result: AnalysisResult, session_filter: str
    ) -> AnalysisResult:
        from .models import AnalysisResult

        filtered = AnalysisResult()
        if session_filter in result.sessions:
            filtered.sessions[session_filter] = result.sessions[session_filter]
        filtered.sorted_sessions = list(filtered.sessions.values())
        filtered.statistics = result.statistics
        return filtered

    def _print_summary(self, result: AnalysisResult) -> None:
        stats = result.statistics
        print("\n=== LLM Trace Analysis Summary ===")
        print(f"Total sessions: {stats.total_sessions}")
        print(f"Total requests: {stats.total_requests}")
        print(f"Total responses: {stats.total_responses}")
        print(f"Total iterations: {stats.total_iterations}")

        if stats.sessions_by_model:
            print("\nSessions by model:")
            for model, count in stats.sessions_by_model.items():
                print(f"  - {model}: {count} sessions")

        print("=" * 40)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze LLM_IO_TRACE logs and generate visualization report",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  lt                              # Analyze latest log
  lt -O                           # Analyze and open report in browser
  lt <log_file>                   # Analyze specific log file
  lt <log_file> -o my_report -O   # Specify output and open in browser
  lt --session <session_id>       # Filter by session
  lt -v                           # Show verbose summary
        """,
    )

    parser.add_argument(
        "log_file",
        nargs="?",
        help="Log file path (default: find latest app.log)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="llm_trace_report",
        help="Output report directory name (default: llm_trace_report)",
    )
    parser.add_argument(
        "--session",
        "-s",
        help="Filter by session_id",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show verbose summary in terminal",
    )
    parser.add_argument(
        "--open",
        "-O",
        action="store_true",
        help="Open report in browser after generation",
    )

    args = parser.parse_args()

    log_path: Path
    if args.log_file:
        log_path = Path(args.log_file)
    else:
        found_path = find_latest_log()
        if found_path is None:
            default_path = Path.home() / ".office-claw" / ".jiuwenclaw" / ".logs" / "app.log"
            print(f"Error: No log file found. Default path: {default_path}")
            sys.exit(1)
        log_path = found_path
        print(f"Using log file: {log_path}")

    # 确定输出路径：默认在日志文件所在目录生成报告
    output_path: str
    if args.output == "llm_trace_report":
        # 使用默认值时，报告生成在日志文件所在目录
        output_path = str(log_path.parent / "llm_trace_report")
    else:
        output_path = args.output

    analyzer = LLMTraceAnalyzer(str(log_path))
    success = analyzer.run(
        output_path=output_path,
        verbose=args.verbose,
        session_filter=args.session,
    )

    if success and args.open:
        # 打开生成的 index.html
        index_file = Path(output_path) / "index.html"
        if index_file.exists():
            webbrowser.open(str(index_file))

    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
