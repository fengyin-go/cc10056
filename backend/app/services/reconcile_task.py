"""对账核对领域服务：管理对账任务的校验流程、状态流转与跨模块数据链路。

数据链路位置：对账核对是零售销售宽表与指标口径平台的核心处理模块之一，负责把对账任务的
校验结果写入销售渠道目录，并消费维度切片的产出记录，形成完整的跨模块数据流。
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


class ReconcileTaskService(BaseModuleService):
    MODULE = "reconcile_task"
    ENTITY = "对账任务"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["任务编号", "渠道账期", "平台口径", "差异金额", "对账结论"]
    REQUIRED_FIELDS = ["任务编号", "渠道账期", "平台口径"]
    STATUS_ORDER = ["待对账", "对账中", "已完成"]
    ACTION_RULES = {"启动对账": "对账中", "确认结论": "已完成"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：对账核对跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把对账核对的校验结果写入销售渠道目录，形成对账核对→销售渠道目录的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"对账任务 {entry_id} 不存在"}
        rows = store.rows("sales_channel")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "渠道名称": f"对账核对-{entry_id}",
            "渠道类型": "reconcile_task",
            "结算口径": str(entry_id),
            "status": "待启用",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已完成"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入销售渠道目录", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取维度切片的产出记录并汇总为对账核对消费台账。"""
        up_rows = [r for r in store.rows("dim_slice") if r.get("status") == "已停用"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "渠道账期": str(r.get("切片名称", "")),
                "平台口径": "维度切片",
                "status": "待对账",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条维度切片记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理对账核对校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"对账任务 {entry_id} 不存在"}
        if entry.get("status") != "待对账":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "对账中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出对账核对数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"对账任务数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
