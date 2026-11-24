"""汇率换算领域服务：管理汇率记录的校验流程、状态流转与跨模块数据链路。

数据链路位置：汇率换算是零售销售宽表与指标口径平台的核心处理模块之一，负责把汇率记录的
校验结果写入维度切片，并消费订单解析的产出记录，形成完整的跨模块数据流。
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


class CurrencyRateService(BaseModuleService):
    MODULE = "currency_rate"
    ENTITY = "汇率记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "币种对", "适用日期", "汇率值", "口径来源"]
    REQUIRED_FIELDS = ["记录编号", "币种对", "适用日期"]
    STATUS_ORDER = ["待生效", "已生效", "已废弃"]
    ACTION_RULES = {"生效汇率": "已生效", "废弃汇率": "已废弃"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：汇率换算跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把汇率换算的校验结果写入维度切片，形成汇率换算→维度切片的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"汇率记录 {entry_id} 不存在"}
        rows = store.rows("dim_slice")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "切片名称": f"汇率换算-{entry_id}",
            "维度组合": "currency_rate",
            "切片条件": str(entry_id),
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已废弃"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入维度切片", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取订单解析的产出记录并汇总为汇率换算消费台账。"""
        up_rows = [r for r in store.rows("order_parse") if r.get("status") == "部分失败"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "币种对": str(r.get("记录编号", "")),
                "适用日期": "订单解析",
                "status": "待生效",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条订单解析记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理汇率换算校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"汇率记录 {entry_id} 不存在"}
        if entry.get("status") != "待生效":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已生效"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出汇率换算数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"汇率记录数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
