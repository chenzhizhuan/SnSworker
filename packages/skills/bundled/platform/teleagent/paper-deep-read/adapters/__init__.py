# Paper Deep Read Adapters
#
# Platform-specific adapters for the paper_deep_read core package.
# Each adapter wraps the core package for a specific LLM/Agent platform.
#
# Available adapters:
#   workbuddy/          - WorkBuddy agent platform (SKILL.md)
#   openai_custom_gpt/  - ChatGPT Custom GPT (instructions.md)
#   openai_assistants/  - OpenAI Assistants API (assistant.py)
#   claude/             - Claude Project / CLAUDE.md
#   dify/               - Dify open-source platform (instructions.md + tools/)
#   coze/               - Coze / ByteDance agent platform (prompt.md)
#   langchain/          - LangChain tools integration (tools.py)
#   autogen/            - Microsoft AutoGen (tools.py)
#   crewai/             - CrewAI agent framework (agent.py)
#   cursor/             - Cursor IDE (.cursorrules)
