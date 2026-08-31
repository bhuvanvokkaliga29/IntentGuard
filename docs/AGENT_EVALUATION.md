# Agent Evaluation & Proficiency Metrics

## 1. Empirical Metrics Calculation
Agent performance metrics are computed strictly from persisted execution records in SQLite (`AgentProficiencyEngine` in `backend/agent/proficiency.py`):

- **Task Success Rate**: $\frac{\text{Completed Runs}}{\text{Total Runs}}$
- **Tool Success Rate**: $\frac{\text{Successful Tool Calls}}{\text{Total Tool Calls}}$
- **Recovery Success Rate**: $\frac{\text{Recovered Faults}}{\text{Total Recoveries Attempted}}$
- **IntentGuard Rejection Rate**: $\frac{\text{FLAG + BLOCK Decisions}}{\text{Total Decisions}}$
- **Average Latency**: Mean duration from run initiation to IntentGuard decision.

## 2. Distinction: Agent Proficiency vs Payment Safety
A high task completion rate in an autonomous agent **does not imply financial safety**. In fact, an agent optimizing for `BEST_RATING` will successfully purchase out-of-scope confectionery unless IntentGuard intercepts the proposal.
