"""订单接入领域服务：管理订单批次的接入流程、状态流转与跨模块数据链路。

数据链路位置：订单接入是零售销售宽表与指标口径平台的核心处理模块之一，负责把订单批次的
接入结果写入销售事实装配，并消费口径复核台的产出记录，形成完整的跨模块数据流。
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


class OrderIngestService(BaseModuleService):
    MODULE = "order_ingest"
    ENTITY = "订单批次"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["批次编号", "渠道标识", "批次行数", "首单时间", "末单时间"]
    REQUIRED_FIELDS = ["批次编号", "渠道标识", "批次行数"]
    STATUS_ORDER = ["待接入", "已接入", "已退回"]
    ACTION_RULES = {"确认接入": "已接入", "退回批次": "已退回"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：订单接入跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把订单接入的接入结果写入销售事实装配，形成订单接入→销售事实装配的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"订单批次 {entry_id} 不存在"}
        rows = store.rows("fact_assemble")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"订单接入-{entry_id}",
            "来源批次": "order_ingest",
            "事实分区": str(entry_id),
            "status": "待装配",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已退回"
        entry["pending"] = False
        return {"ok": True, "message": "接入结果已写入销售事实装配", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取口径复核台的产出记录并汇总为订单接入消费台账。"""
        up_rows = [r for r in store.rows("calc_review") if r.get("status") == "已裁定"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "批次编号": f"消费-{r.get('id', 0)}",
                "渠道标识": str(r.get("事项编号", "")),
                "批次行数": "口径复核台",
                "status": "待接入",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条口径复核台记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理订单接入接入中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"订单批次 {entry_id} 不存在"}
        if entry.get("status") != "待接入":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已接入"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出订单接入数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"订单批次数据集",
            "operation": "接入",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
