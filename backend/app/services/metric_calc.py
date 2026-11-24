"""指标计算领域服务：管理计算任务的计算流程、状态流转与跨模块数据链路。

数据链路位置：指标计算是零售销售宽表与指标口径平台的核心处理模块之一，负责把计算任务的
计算结果写入指标报表，并消费销售事实装配的产出记录，形成完整的跨模块数据流。
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


class MetricCalcService(BaseModuleService):
    MODULE = "metric_calc"
    ENTITY = "计算任务"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["任务编号", "指标标识", "计算窗口", "输入分区", "结果集版本"]
    REQUIRED_FIELDS = ["任务编号", "指标标识", "计算窗口"]
    STATUS_ORDER = ["待计算", "计算中", "已完成", "需重算"]
    ACTION_RULES = {"启动计算": "计算中", "触发重算": "需重算"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：指标计算跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把指标计算的计算结果写入指标报表，形成指标计算→指标报表的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"计算任务 {entry_id} 不存在"}
        rows = store.rows("metric_report")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "报表编号": f"指标计算-{entry_id}",
            "覆盖周期": "metric_calc",
            "指标清单": str(entry_id),
            "status": "草稿",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "需重算"
        entry["pending"] = False
        return {"ok": True, "message": "计算结果已写入指标报表", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取销售事实装配的产出记录并汇总为指标计算消费台账。"""
        up_rows = [r for r in store.rows("fact_assemble") if r.get("status") == "已完成"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "指标标识": str(r.get("任务编号", "")),
                "计算窗口": "销售事实装配",
                "status": "待计算",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条销售事实装配记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理指标计算计算中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"计算任务 {entry_id} 不存在"}
        if entry.get("status") != "待计算":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "计算中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出指标计算数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"计算任务数据集",
            "operation": "计算",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
