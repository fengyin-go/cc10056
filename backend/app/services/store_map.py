"""门店映射领域服务：管理门店条目的校验流程、状态流转与跨模块数据链路。

数据链路位置：门店映射是零售销售宽表与指标口径平台的核心处理模块之一，负责把门店条目的
校验结果写入指标计算，并消费订单接入的产出记录，形成完整的跨模块数据流。
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


class StoreMapService(BaseModuleService):
    MODULE = "store_map"
    ENTITY = "门店条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["条目编号", "渠道门店码", "标准门店码", "区域归属", "生效时间"]
    REQUIRED_FIELDS = ["条目编号", "渠道门店码", "标准门店码"]
    STATUS_ORDER = ["候选", "已生效", "已失效"]
    ACTION_RULES = {"生效条目": "已生效", "失效条目": "已失效"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：门店映射跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把门店映射的校验结果写入指标计算，形成门店映射→指标计算的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"门店条目 {entry_id} 不存在"}
        rows = store.rows("metric_calc")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"门店映射-{entry_id}",
            "指标标识": "store_map",
            "计算窗口": str(entry_id),
            "status": "待计算",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已失效"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入指标计算", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取订单接入的产出记录并汇总为门店映射消费台账。"""
        up_rows = [r for r in store.rows("order_ingest") if r.get("status") == "已退回"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "条目编号": f"消费-{r.get('id', 0)}",
                "渠道门店码": str(r.get("批次编号", "")),
                "标准门店码": "订单接入",
                "status": "候选",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条订单接入记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理门店映射校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"门店条目 {entry_id} 不存在"}
        if entry.get("status") != "候选":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已生效"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出门店映射数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"门店条目数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
