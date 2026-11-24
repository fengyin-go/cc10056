"""口径血缘说明领域服务：管理血缘条目的转换流程、状态流转与跨模块数据链路。

数据链路位置：口径血缘说明是零售销售宽表与指标口径平台的核心处理模块之一，负责把血缘条目的
转换结果写入商品映射，并消费对账核对的产出记录，形成完整的跨模块数据流。
"""
from __future__ import annotations


from datetime import datetime, timezone
from typing import Any

from app.services.base import BaseModuleService
from app.store import store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_id(rows: list) -> int:
    return max((int(r.get("id", 0)) for r in rows), default=0) + 1


class LineageNoteService(BaseModuleService):
    MODULE = "lineage_note"
    ENTITY = "血缘条目"
    OPERATION_TERM = "转换"
    LIST_FIELDS = ["条目编号", "指标标识", "依赖表清单", "转换说明", "口径版本"]
    REQUIRED_FIELDS = ["条目编号", "指标标识", "依赖表清单"]
    STATUS_ORDER = ["待梳理", "已梳理", "已失效"]
    ACTION_RULES = {"梳理条目": "已梳理", "失效条目": "已失效"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：口径血缘说明跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把口径血缘说明的转换结果写入商品映射，形成口径血缘说明→商品映射的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"血缘条目 {entry_id} 不存在"}
        rows = store.rows("sku_map")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "条目编号": f"口径血缘说明-{entry_id}",
            "渠道商品码": "lineage_note",
            "标准商品码": str(entry_id),
            "status": "候选",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已失效"
        entry["pending"] = False
        return {"ok": True, "message": "转换结果已写入商品映射", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取对账核对的产出记录并汇总为口径血缘说明消费台账。"""
        up_rows = [r for r in store.rows("reconcile_task") if r.get("status") == "已完成"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "条目编号": f"消费-{r.get('id', 0)}",
                "指标标识": str(r.get("任务编号", "")),
                "依赖表清单": "对账核对",
                "status": "待梳理",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条对账核对记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理口径血缘说明转换中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"血缘条目 {entry_id} 不存在"}
        if entry.get("status") != "待梳理":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已梳理"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出口径血缘说明数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"血缘条目数据集",
            "operation": "转换",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
