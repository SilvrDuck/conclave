from .base import DocsAdapter
from .github_issues import GitHubIssuesDocs
from .inmemory import InMemoryDocs
from .obsidian import ObsidianVaultDocs
from .senate_proxy import SenateProxyDocs
from .sqlite_impl import SqliteDocs

__all__ = [
    "DocsAdapter",
    "GitHubIssuesDocs",
    "InMemoryDocs",
    "ObsidianVaultDocs",
    "SenateProxyDocs",
    "SqliteDocs",
]
