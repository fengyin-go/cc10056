"""销售事实装配领域服务：管理装配任务的清洗流程、状态流转与跨模块数据链路。

数据链路位置：销售事实装配是零售销售宽表与指标口径平台的核心处理模块之一，负责把装配任务的
清洗结果写入异动扫描，并消费门店映射的产出记录，形成完整的跨模块数据流。
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


class FactAssembleService(BaseModuleService):
    MODULE = "fact_assemble"
    ENTITY = "装配任务"
    OPERATION_TERM = "清洗"
    LIST_FIELDS = ["任务编号", "来源批次", "事实分区", "装配行数", "装配版本"]
    REQUIRED_FIELDS = ["任务编号", "来源批次", "事实分区"]
    STATUS_ORDER = ["待装配", "装配中", "已完成"]
    ACTION_RULES = {"启动装配": "装配中", "确认完成": "已完成"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：销售事实装配跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把销售事实装配的清洗结果写入异动扫描，形成销售事实装配→异动扫描的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"装配任务 {entry_id} 不存在"}
        rows = store.rows("anomaly_scan")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "任务编号": f"销售事实装配-{entry_id}",
            "指标集合": "fact_assemble",
            "检测规则": str(entry_id),
            "status": "待扫描",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已完成"
        entry["pending"] = False
        return {"ok": True, "message": "清洗结果已写入异动扫描", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取门店映射的产出记录并汇总为销售事实装配消费台账。"""
        up_rows = [r for r in store.rows("store_map") if r.get("status") == "已失效"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "任务编号": f"消费-{r.get('id', 0)}",
                "来源批次": str(r.get("条目编号", "")),
                "事实分区": "门店映射",
                "status": "待装配",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条门店映射记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理销售事实装配清洗中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"装配任务 {entry_id} 不存在"}
        if entry.get("status") != "待装配":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "装配中"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出销售事实装配数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"装配任务数据集",
            "operation": "清洗",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
