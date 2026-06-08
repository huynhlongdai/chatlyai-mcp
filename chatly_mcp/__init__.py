"""Chatly MCP - remote-control ChatlyAI (Vyro) accounts via MCP.

PoC that logs in through CloakBrowser (to pass Cloudflare Turnstile), then
drives ChatlyAI's internal Vyro API directly with the captured bearer token.
"""

__version__ = "0.1.0"
