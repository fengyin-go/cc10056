"""异动扫描领域服务：管理扫描任务的校验流程、状态流转与跨模块数据链路。

数据链路位置：异动扫描是零售销售宽表与指标口径平台的核心处理模块之一，负责把扫描任务的
校验结果写入指标总览，并消费指标计算的产出记录，形成完整的跨模块数据流。
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


class AnomalyScanService(BaseModuleService):
    MODULE = "anomaly_scan"
    ENTITY = "扫描任务"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["任务编号", "指标集合", "检测规则", "异动数", "扫描结论"]
    REQUIRED_FIELDS = ["任务编号", "指标集合", "检测规则"]
    STATUS_ORDER = ["待扫描", "扫描中", "已完成"]
    ACTION_RULES = {"启动扫描": "扫描中", "确认结论": "已完成"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：异动扫描跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把异动扫描的校验结果写入指标总览，形成异动扫描→指标总览的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"扫描任务 {entry_id} 不存在"}
        rows = store.rows("metric_overview")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "条目名称": f"异动扫描-{entry_id}",
            "统计口径": "anomaly_scan",
            "当前值": str(entry_id),
            "status": "正常",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已完成"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入指标总览", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取指标计算的产出记录并汇总为异动扫描消费台账。"""
        up_rows = [r for r in store.rows("metric_calc") if r.get("status") == "需重算"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "指标集合": str(r.get("任务编号", "")),
                "检测规则": "指标计算",
                "status": "待扫描",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条指标计算记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理异动扫描校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"扫描任务 {entry_id} 不存在"}
        if entry.get("status") != "待扫描":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "扫描中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出异动扫描数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"扫描任务数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
