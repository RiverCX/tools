"""链路分析器 - 关联请求/响应并生成统计"""

from typing import Any, Dict, List, Optional, Tuple

from .models import (
    AnalysisResult,
    IterationTiming,
    LLMChain,
    LLMRequest,
    LLMResponse,
    Statistics,
    SubagentInfo,
)


class ChainAnalyzer:
    def __init__(
        self,
        requests: Dict[str, List[LLMRequest]],
        responses: Dict[str, List[LLMResponse]],
    ):
        self.requests = requests
        self.responses = responses
        self._parent_to_task_ids: Dict[str, List[Tuple[str, float]]] = {}
        self._task_id_to_parent: Dict[str, str] = {}

    def analyze(self) -> AnalysisResult:
        result = AnalysisResult()

        self._match_spawn_calls_to_task_ids()

        parent_sessions = self._identify_parent_sessions()
        subagent_sessions = self._identify_subagent_sessions()

        for session_id in parent_sessions:
            chain = self._build_parent_chain(session_id, subagent_sessions)
            if chain:
                result.sessions[session_id] = chain

        for session_id in subagent_sessions:
            # 新格式：session_id 本身就是唯一标识，直接检查是否在 _task_id_to_parent 中
            if "_subagent_" in session_id or "_fork_agent_" in session_id:
                if session_id in self._task_id_to_parent:
                    continue
            else:
                # 旧格式：检查 task_id 是否在 _task_id_to_parent 中
                task_id = self._extract_task_id_from_session(session_id)
                if task_id and task_id in self._task_id_to_parent:
                    continue
            chain = self._build_standalone_subagent_chain(session_id)
            if chain:
                result.sessions[session_id] = chain

        result.sorted_sessions = sorted(result.sessions.values(), key=lambda c: c.start_time)

        result.statistics = self._compute_statistics(result.sessions)

        return result

    def _match_spawn_calls_to_task_ids(self) -> None:
        # 新格式：从 session_id 直接提取父子关系
        for session_id in set(self.requests.keys()) | set(self.responses.keys()):
            # spawn_subagent 新格式：<parent>_subagent_<task_id>
            if "_subagent_" in session_id:
                parts = session_id.split("_subagent_")
                if len(parts) >= 2:
                    parent_session = parts[0]
                    if parent_session not in self._parent_to_task_ids:
                        self._parent_to_task_ids[parent_session] = []
                    self._parent_to_task_ids[parent_session].append((session_id, 0))
                    self._task_id_to_parent[session_id] = parent_session

            # fork_agent 新格式：<parent>_fork_agent_<task_id>
            if "_fork_agent_" in session_id:
                parts = session_id.split("_fork_agent_")
                if len(parts) >= 2:
                    parent_session = parts[0]
                    # parent 可能是部分 session_id，需要找到完整匹配
                    # 例如：parent = subagent_af7666eb，完整的是 sess_xxx_subagent_af7666eb
                    full_parent = self._find_full_session_id(parent_session)
                    if full_parent:
                        root_parent = self._find_root_parent(full_parent)
                        if root_parent not in self._parent_to_task_ids:
                            self._parent_to_task_ids[root_parent] = []
                        self._parent_to_task_ids[root_parent].append((session_id, 0))
                        self._task_id_to_parent[session_id] = (
                            full_parent  # 记录直接 parent（完整 session_id）
                        )
                    else:
                        # parent 不在已知 session 中，直接添加
                        if parent_session not in self._parent_to_task_ids:
                            self._parent_to_task_ids[parent_session] = []
                        self._parent_to_task_ids[parent_session].append((session_id, 0))
                        self._task_id_to_parent[session_id] = parent_session

    def _find_full_session_id(self, partial_id: str) -> Optional[str]:
        """从部分 session_id 找到完整匹配的 session_id"""
        all_sessions = set(self.requests.keys()) | set(self.responses.keys())
        for session_id in all_sessions:
            # 排除 fork session_id（因为它们包含 parent 但不是我们要找的）
            if "_fork_agent_" in session_id:
                continue
            # 检查是否以 partial_id 结尾（例如 sess_xxx_subagent_af7666eb 结尾是 subagent_af7666eb）
            if session_id.endswith(partial_id):
                return session_id
        return None

    def _find_root_parent(self, session_id: str) -> str:
        """递归向上找到真正的顶层父 session"""
        # session_id 格式：<parent>_subagent_<task_id> 或 <parent>_fork_agent_<task_id>
        if "_subagent_" in session_id or "_fork_agent_" in session_id:
            # 提取 parent 部分
            if "_subagent_" in session_id:
                parts = session_id.split("_subagent_")
            else:
                parts = session_id.split("_fork_agent_")
            parent = parts[0] if len(parts) >= 2 else session_id
            # 检查 parent 是否也是 subAgent
            if "_subagent_" in parent or "_fork_agent_" in parent:
                return self._find_root_parent(parent)
            return parent
        # 如果不是 subAgent，就是顶层父 session
        return session_id

    def _identify_parent_sessions(self) -> List[str]:
        parent_ids: List[str] = []
        for session_id in set(self.requests.keys()) | set(self.responses.keys()):
            # 排除 subagent session（包含 _subagent_ 或 _fork_agent_）
            if "_subagent_" not in session_id and "_fork_agent_" not in session_id:
                parent_ids.append(session_id)
        return parent_ids

    def _identify_subagent_sessions(self) -> List[str]:
        subagent_ids: List[str] = []
        for session_id in set(self.requests.keys()) | set(self.responses.keys()):
            # subagent session 格式：<parent>_subagent_<task_id> 或 <parent>_fork_agent_<task_id>
            if "_subagent_" in session_id or "_fork_agent_" in session_id:
                subagent_ids.append(session_id)
        return subagent_ids

    def _build_parent_chain(
        self, session_id: str, subagent_sessions: List[str]
    ) -> Optional[LLMChain]:
        reqs = self.requests.get(session_id, [])
        resps = self.responses.get(session_id, [])

        if not reqs and not resps:
            return None

        for req in reqs:
            req.source = "parent"
            req.source_label = "Main"

        for resp in resps:
            resp.source = "parent"
            resp.source_label = "Main"

        model_name = reqs[0].model_name if reqs else (resps[0].model_name if resps else "")

        related_subagents = self._find_related_subagents(session_id)

        subagent_infos: List[SubagentInfo] = []
        for task_id, spawn_time in related_subagents:
            # 确定 subAgent session_id
            # 新格式：task_id 就是完整的 session_id（包含 _subagent_ 或 _fork_agent_）
            # 旧格式 fork_agent: task_id = fork_fork_agent_xxxx
            # 旧格式 spawn_subagent: task_id = xxxx, session_id = subagent_{task_id}
            if "_subagent_" in task_id or "_fork_agent_" in task_id:
                subagent_session = task_id
            elif task_id.startswith("fork_fork_agent_"):
                subagent_session = task_id
            else:
                subagent_session = f"subagent_{task_id}"

            if subagent_session in subagent_sessions:
                subagent_reqs = self.requests.get(subagent_session, [])
                subagent_resps = self.responses.get(subagent_session, [])
                sub_start = subagent_reqs[0].timestamp if subagent_reqs else spawn_time
                sub_end = subagent_resps[-1].timestamp if subagent_resps else 0.0

                # 计算嵌套深度和路径
                depth, chain_path, direct_parent = self._compute_subagent_depth(task_id)

                subagent_infos.append(
                    SubagentInfo(
                        task_id=task_id,
                        session_id=subagent_session,
                        start_time=sub_start,
                        end_time=sub_end,
                        depth=depth,
                        parent_session_id=direct_parent,
                        chain_path=chain_path,
                    )
                )

        all_requests: List[LLMRequest] = list(reqs)
        all_responses: List[LLMResponse] = list(resps)

        for task_id, _ in related_subagents:
            # 确定 subAgent session_id
            # 新格式：task_id 就是完整的 session_id（包含 _subagent_ 或 _fork_agent_）
            if "_subagent_" in task_id or "_fork_agent_" in task_id:
                subagent_session = task_id
            elif task_id.startswith("fork_fork_agent_"):
                subagent_session = task_id
            else:
                subagent_session = f"subagent_{task_id}"

            # 计算嵌套深度和路径用于显示
            depth, chain_path, direct_parent = self._compute_subagent_depth(task_id)

            if subagent_session in self.requests:
                for req in self.requests[subagent_session]:
                    req.source = "subagent"
                    req.source_label = self._format_chain_label(chain_path, depth)
                    all_requests.append(req)
            if subagent_session in self.responses:
                for resp in self.responses[subagent_session]:
                    resp.source = "subagent"
                    resp.source_label = self._format_chain_label(chain_path, depth)
                    all_responses.append(resp)

        all_requests.sort(key=lambda r: r.timestamp)
        all_responses.sort(key=lambda r: r.timestamp)

        start_time = all_requests[0].timestamp if all_requests else 0
        end_time = all_responses[-1].timestamp if all_responses else 0

        # 计算时间统计
        iteration_timings = self._compute_iteration_timings(all_requests, all_responses)
        total_llm_duration = sum(t.llm_call_duration for t in iteration_timings)
        total_tool_duration = sum(t.tool_processing_duration for t in iteration_timings)

        return LLMChain(
            session_id=session_id,
            model_name=model_name,
            requests=all_requests,
            responses=all_responses,
            start_time=start_time,
            end_time=end_time,
            total_iterations=len(all_requests),
            subagents=subagent_infos,
            is_subagent=False,
            iteration_timings=iteration_timings,
            total_llm_duration_seconds=total_llm_duration,
            total_tool_duration_seconds=total_tool_duration,
        )

    def _compute_iteration_timings(
        self,
        requests: List[LLMRequest],
        responses: List[LLMResponse],
    ) -> List[IterationTiming]:
        """计算每个迭代的时间统计"""
        timings: List[IterationTiming] = []

        # 按 (session_id, iteration) 配对
        paired: Dict[Tuple[str, int], Dict] = {}

        for req in requests:
            key = (req.session_id, req.iteration)
            if key not in paired:
                paired[key] = {"request": None, "response": None, "timestamp": 0}
            paired[key]["request"] = req
            paired[key]["timestamp"] = req.timestamp

        for resp in responses:
            key = (resp.session_id, resp.iteration)
            if key not in paired:
                paired[key] = {"request": None, "response": None, "timestamp": 0}
            paired[key]["response"] = resp
            if paired[key]["timestamp"] == 0:
                paired[key]["timestamp"] = resp.timestamp

        # 按 timestamp 排序
        sorted_items = sorted(paired.values(), key=lambda x: x["timestamp"])

        # 构建 session_id -> prev_iteration 的映射，用于判断子 Agent 第一次请求
        session_first_iteration: Dict[str, int] = {}
        for i, item in enumerate(sorted_items):
            req = item["request"]
            if req:
                sid = req.session_id
                if sid not in session_first_iteration:
                    session_first_iteration[sid] = i

        for i, item in enumerate(sorted_items):
            req = item["request"]
            resp = item["response"]

            if not req and not resp:
                continue

            timing = IterationTiming(
                iteration_num=i + 1,
                session_id=req.session_id if req else (resp.session_id if resp else ""),
                request_timestamp=req.timestamp if req else 0,
                response_timestamp=resp.timestamp if resp else 0,
            )

            # 计算 llm_call_duration
            if req and resp:
                timing.llm_call_duration = resp.timestamp - req.timestamp

            # 计算 tool_processing_duration（查找下一个同 session 的请求）
            is_first_of_session = session_first_iteration.get(timing.session_id) == i

            if resp and i < len(sorted_items) - 1:
                # 找下一个同 session 的请求（跳过其他 session 的交错请求）
                for j in range(i + 1, len(sorted_items)):
                    next_item = sorted_items[j]
                    next_req = next_item["request"]
                    if next_req and next_req.session_id == timing.session_id:
                        gap = next_req.timestamp - resp.timestamp
                        # 如果 response 包含 spawn_subagent，排除 subAgent 运行时间
                        if self._has_spawn_subagent(resp):
                            # 只计算框架处理时间（response 到 subAgent 启动）
                            spawn_overhead = self._get_spawn_overhead(resp.timestamp, timing.session_id)
                            timing.tool_processing_duration = min(spawn_overhead, gap)
                        else:
                            timing.tool_processing_duration = gap
                        break

            # 判断是否为最后一次迭代
            timing.is_last_iteration = timing.tool_processing_duration == 0

            timings.append(timing)

        return timings

    def _has_spawn_subagent(self, resp: LLMResponse) -> bool:
        """检查 response 是否包含 spawn_subagent 类工具调用"""
        if not resp.tool_calls:
            return False
        for tc in resp.tool_calls:
            name = tc.get("name", "") or tc.get("function", {}).get("name", "")
            if "subagent" in name.lower() or "spawn" in name.lower() or "agent" in name.lower():
                return True
        return False

    def _get_spawn_overhead(self, response_timestamp: float, parent_session_id: str) -> float:
        """计算 spawn subagent 的框架处理时间（response 到第一个 subagent 启动）"""
        children = self._parent_to_task_ids.get(parent_session_id, [])
        if not children:
            return 0.0

        # 找到 response 之后启动的 subagent 中最早的时间
        min_start = float("inf")
        for child_session_id, _ in children:
            child_reqs = self.requests.get(child_session_id, [])
            if child_reqs:
                child_start = child_reqs[0].timestamp
                if child_start > response_timestamp - 1 and child_start < min_start:
                    min_start = child_start

        if min_start == float("inf"):
            return 0.0
        return max(min_start - response_timestamp, 0.0)

    def _compute_subagent_depth(self, task_id: str) -> Tuple[int, List[str], str]:
        """计算 subAgent 的嵌套深度和调用路径"""
        chain_path = []
        depth = 0

        # 从映射表获取完整的直接 parent（新格式下存储的是完整 session_id）
        direct_parent = self._task_id_to_parent.get(task_id) or ""

        # 添加当前 subAgent 到路径末尾
        current_short_name = self._short_task_id(task_id)
        if "_fork_agent_" in task_id:
            chain_path.append(f"Fork[{current_short_name}]")
        elif "_subagent_" in task_id:
            chain_path.append(f"Sub[{current_short_name}]")
        elif task_id.startswith("fork_fork_agent_"):
            chain_path.append(f"Fork[{current_short_name}]")
        else:
            chain_path.append(f"Sub[{current_short_name}]")

        current_task_id = task_id
        while True:
            # 从映射表获取 parent
            parent_session = self._task_id_to_parent.get(current_task_id)

            if not parent_session:
                chain_path.insert(0, "Main")
                break

            # 检查 parent 是否也是 subAgent（新格式）
            if "_subagent_" in parent_session or "_fork_agent_" in parent_session:
                short_name = self._short_task_id(parent_session)
                if "_fork_agent_" in parent_session:
                    chain_path.insert(0, f"Fork[{short_name}]")
                else:
                    chain_path.insert(0, f"Sub[{short_name}]")
                depth += 1
                current_task_id = parent_session
                continue

            # 旧格式判断
            if parent_session.startswith("subagent_subagent_"):
                parent_task_id = parent_session[len("subagent_") :]
                short_name = self._short_task_id(parent_task_id)
                chain_path.insert(0, f"Sub[{short_name}]")
                depth += 1
                current_task_id = parent_task_id
            elif parent_session.startswith("fork_fork_agent_"):
                short_name = self._short_task_id(parent_session)
                chain_path.insert(0, f"Fork[{short_name}]")
                depth += 1
                current_task_id = parent_session
            else:
                # 父是顶层 session
                chain_path.insert(0, "Main")
                break

        return depth, chain_path, direct_parent

    def _format_chain_label(self, chain_path: List[str], depth: int) -> str:
        """格式化调用链标签"""
        return " → ".join(chain_path)

    def _build_standalone_subagent_chain(self, session_id: str) -> Optional[LLMChain]:
        reqs = self.requests.get(session_id, [])
        resps = self.responses.get(session_id, [])

        if not reqs and not resps:
            return None

        for req in reqs:
            req.source = "subagent"
            req.source_label = "Subagent"

        for resp in resps:
            resp.source = "subagent"
            resp.source_label = "Subagent"

        model_name = reqs[0].model_name if reqs else (resps[0].model_name if resps else "")

        return LLMChain(
            session_id=session_id,
            model_name=model_name,
            requests=reqs,
            responses=resps,
            start_time=reqs[0].timestamp if reqs else 0,
            end_time=resps[-1].timestamp if resps else 0,
            total_iterations=len(reqs),
            is_subagent=True,
        )

    def _find_related_subagents(self, parent_session: str) -> List[Tuple[str, float]]:
        task_ids = self._parent_to_task_ids.get(parent_session, [])
        return sorted(task_ids, key=lambda x: x[1])

    def _short_task_id(self, task_id: str) -> str:
        if not task_id:
            return "unknown"
        # 优先检查 _fork_agent_（因为 fork_agent session_id 中可能包含 _subagent_）
        # 例如：xxx_subagent_a57b9eed_fork_agent_35121a76 应取 35121a76
        if "_fork_agent_" in task_id:
            parts = task_id.split("_fork_agent_")
            if len(parts) >= 2:
                return parts[-1][:12]
        # 新格式：<parent>_subagent_<task_id>
        if "_subagent_" in task_id:
            parts = task_id.split("_subagent_")
            if len(parts) >= 2:
                return parts[-1][:12]
        # 旧格式 fork_fork_agent_xxxx
        if task_id.startswith("fork_fork_agent_"):
            suffix = task_id[len("fork_fork_agent_") :]
            return f"fork_{suffix[:8]}"
        # 旧格式 subagent_xxxx
        parts = task_id.split("_")
        if len(parts) >= 2:
            return parts[-1][:12]
        return task_id[:12]

    def _extract_task_id_from_session(self, session_id: str) -> Optional[str]:
        # 新格式：<parent>_subagent_<task_id>
        if "_subagent_" in session_id:
            # 提取 subagent_<task_id> 部分
            parts = session_id.split("_subagent_")
            if len(parts) >= 2:
                return f"subagent_{parts[-1]}"
        # 旧格式：subagent_xxxx
        if session_id.startswith("subagent_"):
            return session_id[len("subagent_") :]
        # fork 格式：fork_fork_agent_xxxx
        if session_id.startswith("fork_fork_agent_"):
            return session_id  # 整个 session_id 作为 task_id
        return None

    def _compute_statistics(self, sessions: Dict[str, LLMChain]) -> Statistics:
        stats = Statistics()

        parent_chains = [s for s in sessions.values() if not s.is_subagent]
        stats.total_sessions = len(parent_chains)

        total_llm_time = 0.0
        total_tool_time = 0.0
        total_duration = 0.0
        total_iterations_count = 0

        for chain in sessions.values():
            if not chain.is_subagent:
                stats.total_requests += len(chain.requests)
                stats.total_responses += len(chain.responses)
                stats.total_iterations += chain.total_iterations

                model = chain.model_name
                stats.sessions_by_model[model] = stats.sessions_by_model.get(model, 0) + 1

                # 时间统计
                total_llm_time += chain.total_llm_duration_seconds
                total_tool_time += chain.total_tool_duration_seconds
                total_iterations_count += len(chain.iteration_timings)

                # Session 总耗时
                if chain.start_time and chain.end_time:
                    total_duration += chain.end_time - chain.start_time

        stats.total_duration_seconds = total_duration
        stats.total_llm_time_seconds = total_llm_time
        stats.total_tool_time_seconds = total_tool_time

        # 计算平均值
        if total_iterations_count > 0:
            stats.avg_llm_time_seconds = total_llm_time / total_iterations_count
            stats.avg_tool_time_seconds = total_tool_time / total_iterations_count

        return stats
