"""订单清洗领域服务：管理清洗记录的清洗流程、状态流转与跨模块数据链路。

数据链路位置：订单清洗是零售销售宽表与指标口径平台的核心处理模块之一，负责把清洗记录的
清洗结果写入同环比对比，并消费商品映射的产出记录，形成完整的跨模块数据流。
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


class OrderCleanService(BaseModuleService):
    MODULE = "order_clean"
    ENTITY = "清洗记录"
    OPERATION_TERM = "清洗"
    LIST_FIELDS = ["记录编号", "重复批次", "缺失字段", "处理动作", "清洗版本"]
    REQUIRED_FIELDS = ["记录编号", "重复批次", "缺失字段"]
    STATUS_ORDER = ["待清洗", "已清洗", "已退单"]
    ACTION_RULES = {"执行清洗": "已清洗", "退回订单": "已退单"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：订单清洗跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把订单清洗的清洗结果写入同环比对比，形成订单清洗→同环比对比的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"清洗记录 {entry_id} 不存在"}
        rows = store.rows("compare_period")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"订单清洗-{entry_id}",
            "指标标识": "order_clean",
            "本期窗口": str(entry_id),
            "status": "待对比",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已退单"
        entry["pending"] = False
        return {"ok": True, "message": "清洗结果已写入同环比对比", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取商品映射的产出记录并汇总为订单清洗消费台账。"""
        up_rows = [r for r in store.rows("sku_map") if r.get("status") == "已失效"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "重复批次": str(r.get("条目编号", "")),
                "缺失字段": "商品映射",
                "status": "待清洗",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条商品映射记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理订单清洗清洗中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"清洗记录 {entry_id} 不存在"}
        if entry.get("status") != "待清洗":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已清洗"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出订单清洗数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"清洗记录数据集",
            "operation": "清洗",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
