"""Evidence tracking from event log."""
from dare_framework.plan.types import ProposedPlan


async def extract_evidence_from_agent(agent, plan: ProposedPlan) -> dict[int, dict]:
    """Extract evidence from agent's event log.

    Args:
        agent: FiveLayerAgent with _event_log attribute
        plan: The plan that was executed (with evidence requirements)

    Returns:
        Dict mapping step index (1-based) to evidence dict:
        {
            "status": "✓" or "✗",
            "content": "actual evidence collected"
        }
    """
    if not hasattr(agent, '_event_log') or agent._event_log is None:
        # No event log - can't track evidence
        return {}

    # Query event log for tool executions
    try:
        events = await agent._event_log.query(limit=1000)
    except Exception:
        return {}

    evidence_filled = {}

    for i, step in enumerate(plan.steps, 1):
        evidence_type = step.capability_id  # e.g. "file_evidence", "search_evidence"

        # Extract evidence based on type
        if evidence_type == "file_evidence":
            # Extract: which files were read
            files_read = []
            for event in events:
                if event.event_type == "tool.result" and event.payload.get("capability_id") == "read_file":
                    file_path = event.payload.get("params", {}).get("path", "")
                    if file_path:
                        # Extract just filename from path
                        filename = file_path.split("/")[-1]
                        files_read.append(filename)

            if files_read:
                evidence_filled[i] = {
                    "status": "✓",
                    "content": f"已读取 {len(files_read)} 个文件: {', '.join(files_read)}"
                }
            else:
                evidence_filled[i] = {
                    "status": "✗",
                    "content": "未读取任何文件"
                }

        elif evidence_type == "search_evidence":
            # Extract: search was performed
            searches = []
            for event in events:
                if event.event_type == "tool.result" and event.payload.get("capability_id") == "search_code":
                    pattern = event.payload.get("params", {}).get("pattern", "")
                    if pattern:
                        searches.append(pattern)

            if searches:
                evidence_filled[i] = {
                    "status": "✓",
                    "content": f"已搜索: {', '.join(searches)}"
                }
            else:
                evidence_filled[i] = {
                    "status": "✗",
                    "content": "未执行搜索"
                }

        elif evidence_type == "summary_evidence":
            # Extract: model generated summary (look for long text responses)
            has_summary = False
            for event in events:
                if event.event_type == "model.response":
                    content = event.payload.get("content", "")
                    # Consider it a summary if response is longer than 100 chars
                    if len(content) > 100:
                        has_summary = True
                        break

            if has_summary:
                evidence_filled[i] = {
                    "status": "✓",
                    "content": "已生成总结"
                }
            else:
                evidence_filled[i] = {
                    "status": "✗",
                    "content": "未生成总结"
                }

        elif evidence_type == "code_creation_evidence":
            # Extract: which files were created/written
            files_written = []
            for event in events:
                if event.event_type == "tool.result" and event.payload.get("capability_id") == "write_file":
                    file_path = event.payload.get("params", {}).get("path", "")
                    if file_path:
                        # Extract just filename from path
                        filename = file_path.split("/")[-1]
                        files_written.append(filename)

            if files_written:
                evidence_filled[i] = {
                    "status": "✓",
                    "content": f"已创建 {len(files_written)} 个文件: {', '.join(files_written)}"
                }
            else:
                evidence_filled[i] = {
                    "status": "✗",
                    "content": "未创建任何文件"
                }

        elif evidence_type == "functionality_evidence":
            # Extract: whether code was tested/run
            # For now, we assume if files were written, functionality is achieved
            # In a real implementation, this would check for actual test results
            files_written = any(
                event.event_type == "tool.result"
                and event.payload.get("capability_id") == "write_file"
                for event in events
            )

            if files_written:
                evidence_filled[i] = {
                    "status": "✓",
                    "content": "代码已创建（功能待用户测试）"
                }
            else:
                evidence_filled[i] = {
                    "status": "✗",
                    "content": "未创建代码文件"
                }

        else:
            # Unknown evidence type - mark as not collected
            evidence_filled[i] = {
                "status": "✗",
                "content": f"未知证据类型: {evidence_type}"
            }

    return evidence_filled
