"""宽表关联领域服务：管理关联任务的关联流程、状态流转与跨模块数据链路。

数据链路位置：宽表关联是零售销售宽表与指标口径平台的核心处理模块之一，负责把关联任务的
关联结果写入对账核对，并消费汇率换算的产出记录，形成完整的跨模块数据流。
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


class WideJoinService(BaseModuleService):
    MODULE = "wide_join"
    ENTITY = "关联任务"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["任务编号", "事实分区", "维表组合", "关联键集", "未命中率"]
    REQUIRED_FIELDS = ["任务编号", "事实分区", "维表组合"]
    STATUS_ORDER = ["待关联", "关联中", "已完成"]
    ACTION_RULES = {"启动关联": "关联中", "确认完成": "已完成"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：宽表关联跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把宽表关联的关联结果写入对账核对，形成宽表关联→对账核对的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"关联任务 {entry_id} 不存在"}
        rows = store.rows("reconcile_task")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"宽表关联-{entry_id}",
            "渠道账期": "wide_join",
            "平台口径": str(entry_id),
            "status": "待对账",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已完成"
        entry["pending"] = False
        return {"ok": True, "message": "关联结果已写入对账核对", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取汇率换算的产出记录并汇总为宽表关联消费台账。"""
        up_rows = [r for r in store.rows("currency_rate") if r.get("status") == "已废弃"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "事实分区": str(r.get("记录编号", "")),
                "维表组合": "汇率换算",
                "status": "待关联",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条汇率换算记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理宽表关联关联中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"关联任务 {entry_id} 不存在"}
        if entry.get("status") != "待关联":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "关联中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出宽表关联数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"关联任务数据集",
            "operation": "关联",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
