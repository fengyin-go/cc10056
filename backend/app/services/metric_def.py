"""指标定义领域服务：管理指标定义的计算流程、状态流转与跨模块数据链路。

数据链路位置：指标定义是零售销售宽表与指标口径平台的核心处理模块之一，负责把指标定义的
计算结果写入指标服务，并消费订单清洗的产出记录，形成完整的跨模块数据流。
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


class MetricDefService(BaseModuleService):
    MODULE = "metric_def"
    ENTITY = "指标定义"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["指标名称", "计算公式", "统计粒度", "过滤条件", "口径版本"]
    REQUIRED_FIELDS = ["指标名称", "计算公式", "统计粒度"]
    STATUS_ORDER = ["草稿", "已发布", "已下线"]
    ACTION_RULES = {"发布指标": "已发布", "下线指标": "已下线"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：指标定义跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把指标定义的计算结果写入指标服务，形成指标定义→指标服务的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"指标定义 {entry_id} 不存在"}
        rows = store.rows("metric_api")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "请求编号": f"指标定义-{entry_id}",
            "指标标识": "metric_def",
            "查询参数": str(entry_id),
            "status": "已受理",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已下线"
        entry["pending"] = False
        return {"ok": True, "message": "计算结果已写入指标服务", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取订单清洗的产出记录并汇总为指标定义消费台账。"""
        up_rows = [r for r in store.rows("order_clean") if r.get("status") == "已退单"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "指标名称": f"消费-{r.get('id', 0)}",
                "计算公式": str(r.get("记录编号", "")),
                "统计粒度": "订单清洗",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条订单清洗记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理指标定义计算中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"指标定义 {entry_id} 不存在"}
        if entry.get("status") != "草稿":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已发布"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出指标定义数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"指标定义数据集",
            "operation": "计算",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
