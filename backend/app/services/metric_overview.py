"""指标总览领域服务：管理概览条目的校验流程、状态流转与跨模块数据链路。

数据链路位置：指标总览是零售销售宽表与指标口径平台的核心处理模块之一，负责把概览条目的
校验结果写入汇率换算，并消费指标报表的产出记录，形成完整的跨模块数据流。
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


class MetricOverviewService(BaseModuleService):
    MODULE = "metric_overview"
    ENTITY = "概览条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["条目名称", "统计口径", "当前值", "趋势方向", "更新周期"]
    REQUIRED_FIELDS = ["条目名称", "统计口径", "当前值"]
    STATUS_ORDER = ["正常", "关注", "异常"]
    ACTION_RULES = {"刷新条目": "正常", "确认异常": "关注"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：指标总览跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把指标总览的校验结果写入汇率换算，形成指标总览→汇率换算的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"概览条目 {entry_id} 不存在"}
        rows = store.rows("currency_rate")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"指标总览-{entry_id}",
            "币种对": "metric_overview",
            "适用日期": str(entry_id),
            "status": "待生效",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "异常"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入汇率换算", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取指标报表的产出记录并汇总为指标总览消费台账。"""
        up_rows = [r for r in store.rows("metric_report") if r.get("status") == "已归档"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "条目名称": f"消费-{r.get('id', 0)}",
                "统计口径": str(r.get("报表编号", "")),
                "当前值": "指标报表",
                "status": "正常",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条指标报表记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理指标总览校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"概览条目 {entry_id} 不存在"}
        if entry.get("status") != "正常":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "关注"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出指标总览数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"概览条目数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
