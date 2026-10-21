"""Session-only undo receipts. Never reconstruct delete authority from task files."""
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from .domain import Document, key
from .database import CommitUnknown, PreflightError
from .engine import account_lock


@dataclass
class UndoSession:
    config: object
    source: str
    task_id: str
    documents: list
    mapping: dict
    state: str = "ready"
    snapshot: dict = field(default_factory=dict)

    @classmethod
    def from_result(cls, config, source, result):
        rows = result.get("rows", [])
        # Unresolved commits must be resolved manually before any undo.
        if any(row.status == "待确认" for row in rows):
            return None
        grouped = defaultdict(list)
        for row in rows:
            grouped[key(row.voucher)].append(row)
        documents, mapping = [], {}
        for source_key, group in grouped.items():
            successful = [row for row in group if row.status == "导入成功"]
            if not successful:
                continue
            ids = {row.header_id for row in group}
            codes = {row.sa_code for row in group}
            if len(successful) != len(group) or len(ids) != 1 or not next(iter(ids)) or len(codes) != 1:
                return None
            documents.append(Document(group[0].voucher, deepcopy(group), group[0].sa_code))
            mapping[source_key] = (group[0].header_id, group[0].sa_code)
        if not documents or len({value[0] for value in mapping.values()}) != len(documents):
            return None
        return cls(config, str(source), result["task_id"], documents, mapping)

    def prepare(self, repository):
        if self.state != "ready":
            raise PreflightError("本次任务当前不可撤销")
        with account_lock(self.config):
            self.snapshot = repository.prepare_undo(self.documents, self.mapping)
        return self

    def execute(self, repository):
        if self.state != "ready" or not self.snapshot:
            raise PreflightError("请先核对撤销清单")
        with account_lock(self.config):
            try:
                result = repository.delete_import(self.documents, self.mapping, self.snapshot)
            except Exception as exc:
                if isinstance(exc, CommitUnknown):
                    self.state = "unknown"
                raise
        self.state = "done"
        return result
