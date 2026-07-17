"""
easy_issue_finder agent — find approachable open-source issues for newcomers.

Planned modules (see implementation plan)
-----------------------------------------
finder_runner.py       Agent loop (LLM + tools until N easy issues found)
github_issue_tools.py  In-process tools the LLM calls (wraps github_api)
result_validator.py    Parse and validate the model's JSON output

Prompts: ``prompts/easy_issue_finder/user.txt``
CLI: ``scripts/run_easy_issue_finder.py``
"""
