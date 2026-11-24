"""同环比对比领域服务：管理对比任务的计算流程、状态流转与跨模块数据链路。

数据链路位置：同环比对比是零售销售宽表与指标口径平台的核心处理模块之一，负责把对比任务的
计算结果写入口径复核台，并消费指标定义的产出记录，形成完整的跨模块数据流。
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


class ComparePeriodService(BaseModuleService):
    MODULE = "compare_period"
    ENTITY = "对比任务"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["任务编号", "指标标识", "本期窗口", "对照窗口", "差异结论"]
    REQUIRED_FIELDS = ["任务编号", "指标标识", "本期窗口"]
    STATUS_ORDER = ["待对比", "对比中", "已完成"]
    ACTION_RULES = {"启动对比": "对比中", "确认结论": "已完成"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：同环比对比跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把同环比对比的计算结果写入口径复核台，形成同环比对比→口径复核台的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"对比任务 {entry_id} 不存在"}
        rows = store.rows("calc_review")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "事项编号": f"同环比对比-{entry_id}",
            "争议指标": "compare_period",
            "原口径": str(entry_id),
            "status": "待复核",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已完成"
        entry["pending"] = False
        return {"ok": True, "message": "计算结果已写入口径复核台", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取指标定义的产出记录并汇总为同环比对比消费台账。"""
        up_rows = [r for r in store.rows("metric_def") if r.get("status") == "已下线"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "指标标识": str(r.get("指标名称", "")),
                "本期窗口": "指标定义",
                "status": "待对比",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条指标定义记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理同环比对比计算中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"对比任务 {entry_id} 不存在"}
        if entry.get("status") != "待对比":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "对比中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出同环比对比数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"对比任务数据集",
            "operation": "计算",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
