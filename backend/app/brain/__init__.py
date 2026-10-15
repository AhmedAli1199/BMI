"""The Brain: BMI Brain's AI assistant (the AI Hub chat and the "Ask AI" button). Plan: docs/ai-hub-plan.md.

registry   - @brain_tool: plain Python tools with typed inputs, run as the asking person
knowledge  - the help guides (help/**.md) and the screen map (help/ui_map.json)
prompt     - the fixed instructions (kept identical between turns so the prompt cache stays warm)
agent      - the agent (Google's agent kit), model and thinking level per question
runner     - runs one turn: history + question in, streamed steps and text out, trace recorded
"""
