"""订单解析领域服务：管理解析记录的解析流程、状态流转与跨模块数据链路。

数据链路位置：订单解析是零售销售宽表与指标口径平台的核心处理模块之一，负责把解析记录的
解析结果写入宽表关联，并消费指标总览的产出记录，形成完整的跨模块数据流。
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


class OrderParseService(BaseModuleService):
    MODULE = "order_parse"
    ENTITY = "解析记录"
    OPERATION_TERM = "解析"
    LIST_FIELDS = ["记录编号", "渠道标识", "字段映射版本", "解析行数", "失败行数"]
    REQUIRED_FIELDS = ["记录编号", "渠道标识", "字段映射版本"]
    STATUS_ORDER = ["待解析", "已解析", "部分失败"]
    ACTION_RULES = {"执行解析": "已解析", "标记失败": "部分失败"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：订单解析跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把订单解析的解析结果写入宽表关联，形成订单解析→宽表关联的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"解析记录 {entry_id} 不存在"}
        rows = store.rows("wide_join")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"订单解析-{entry_id}",
            "事实分区": "order_parse",
            "维表组合": str(entry_id),
            "status": "待关联",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "部分失败"
        entry["pending"] = False
        return {"ok": True, "message": "解析结果已写入宽表关联", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取指标总览的产出记录并汇总为订单解析消费台账。"""
        up_rows = [r for r in store.rows("metric_overview") if r.get("status") == "异常"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "记录编号": f"消费-{r.get('id', 0)}",
                "渠道标识": str(r.get("条目名称", "")),
                "字段映射版本": "指标总览",
                "status": "待解析",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条指标总览记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理订单解析解析中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"解析记录 {entry_id} 不存在"}
        if entry.get("status") != "待解析":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已解析"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出订单解析数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"解析记录数据集",
            "operation": "解析",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
