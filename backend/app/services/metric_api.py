"""指标服务领域服务：管理服务请求的写入流程、状态流转与跨模块数据链路。

数据链路位置：指标服务是零售销售宽表与指标口径平台的核心处理模块之一，负责把服务请求的
写入结果写入订单接入，并消费同环比对比的产出记录，形成完整的跨模块数据流。
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


class MetricApiService(BaseModuleService):
    MODULE = "metric_api"
    ENTITY = "服务请求"
    OPERATION_TERM = "写入"
    LIST_FIELDS = ["请求编号", "指标标识", "查询参数", "返回行数", "服务耗时"]
    REQUIRED_FIELDS = ["请求编号", "指标标识", "查询参数"]
    STATUS_ORDER = ["已受理", "已返回", "已缓存"]
    ACTION_RULES = {"执行查询": "已返回", "写入缓存": "已缓存"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：指标服务跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把指标服务的写入结果写入订单接入，形成指标服务→订单接入的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"服务请求 {entry_id} 不存在"}
        rows = store.rows("order_ingest")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "批次编号": f"指标服务-{entry_id}",
            "渠道标识": "metric_api",
            "批次行数": str(entry_id),
            "status": "待接入",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已缓存"
        entry["pending"] = False
        return {"ok": True, "message": "写入结果已写入订单接入", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取同环比对比的产出记录并汇总为指标服务消费台账。"""
        up_rows = [r for r in store.rows("compare_period") if r.get("status") == "已完成"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "请求编号": f"消费-{r.get('id', 0)}",
                "指标标识": str(r.get("任务编号", "")),
                "查询参数": "同环比对比",
                "status": "已受理",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条同环比对比记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理指标服务写入中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"服务请求 {entry_id} 不存在"}
        if entry.get("status") != "已受理":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已返回"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出指标服务数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"服务请求数据集",
            "operation": "写入",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
