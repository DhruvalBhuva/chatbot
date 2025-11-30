# backend/tools/search_tool.py

from langchain_community.tools import DuckDuckGoSearchRun

search_tool = DuckDuckGoSearchRun(region="us-en")
