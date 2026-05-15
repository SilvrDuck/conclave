"""agenda.md parser.

Format (per spec §4.1):

    ## doing
    - [alice-42] pagination on GET /users/{id}  · since 14:02  · eta ~30min

    ## next
    - [alice-43] migrate session store to redis

    ## blocked-on
    - [alice-41] waiting on bob to finish auth token rotation
"""

from __future__ import annotations

import re

from ..core import AgendaItem, AgendaSection, PodName, utc_now
from ..core.ids import AgendaItemId

_SECTION_RE = re.compile(r"^##\s+(doing|next|blocked-on)\s*$", re.IGNORECASE)
_ITEM_RE = re.compile(
    r"^-\s*\[(?P<id>[^\]]+)\]\s*(?P<text>.+?)(?:\s*·\s*since\s+(?P<since>\S+))?"
    r"(?:\s*·\s*eta\s+(?P<eta>\S+))?\s*$"
)


def parse_agenda(pod: PodName, text: str) -> list[AgendaItem]:
    items: list[AgendaItem] = []
    section: AgendaSection | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        m_section = _SECTION_RE.match(line)
        if m_section:
            section_name = m_section.group(1).lower().replace("-", "_")
            section = AgendaSection(section_name)
            continue
        if section is None:
            continue
        m_item = _ITEM_RE.match(line)
        if not m_item:
            continue
        items.append(
            AgendaItem(
                id=AgendaItemId(m_item.group("id").strip()),
                pod=pod,
                section=section,
                text=m_item.group("text").strip(),
                eta=m_item.group("eta"),
                updated_at=utc_now(),
            )
        )
    return items


__all__ = ["parse_agenda"]
