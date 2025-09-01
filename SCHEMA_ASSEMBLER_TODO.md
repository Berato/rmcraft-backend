# Schema Assembler Plan Implementation

- [x] Create this plan in `docs/`
- [x] Inventory agents that use `output_schema` (Found 8 agents)
- [x] Remove `output_schema` from sub-agents (8 instances updated)
- [x] Standardize prompts and generate configs for sub-agents (JSON-only, low temperature)
- [x] Implement `schema_assembler.py` that validates, repairs, and builds final Pydantic object
- [x] Update workflow to use schema assembler instead of manual merging
- [x] Wrap synchronous sub-agents as `AgentTool` where needed (Not needed - workflow structure is correct)
- [x] Add unit, fuzz, and integration tests for assembler and generators
- [x] Add metrics, structured logging, and rollout/monitoring plan
