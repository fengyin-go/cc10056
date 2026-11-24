"""指标报表领域服务：管理报表文档的归档流程、状态流转与跨模块数据链路。

数据链路位置：指标报表是零售销售宽表与指标口径平台的核心处理模块之一，负责把报表文档的
归档结果写入订单解析，并消费异动扫描的产出记录，形成完整的跨模块数据流。
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


class MetricReportService(BaseModuleService):
    MODULE = "metric_report"
    ENTITY = "报表文档"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["报表编号", "覆盖周期", "指标清单", "对比结论", "发布版本"]
    REQUIRED_FIELDS = ["报表编号", "覆盖周期", "指标清单"]
    STATUS_ORDER = ["草稿", "已发布", "已归档"]
    ACTION_RULES = {"发布报表": "已发布", "归档报表": "已归档"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：指标报表跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把指标报表的归档结果写入订单解析，形成指标报表→订单解析的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"报表文档 {entry_id} 不存在"}
        rows = store.rows("order_parse")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"指标报表-{entry_id}",
            "渠道标识": "metric_report",
            "字段映射版本": str(entry_id),
            "status": "待解析",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已归档"
        entry["pending"] = False
        return {"ok": True, "message": "归档结果已写入订单解析", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取异动扫描的产出记录并汇总为指标报表消费台账。"""
        up_rows = [r for r in store.rows("anomaly_scan") if r.get("status") == "已完成"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "报表编号": f"消费-{r.get('id', 0)}",
                "覆盖周期": str(r.get("任务编号", "")),
                "指标清单": "异动扫描",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条异动扫描记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理指标报表归档中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"报表文档 {entry_id} 不存在"}
        if entry.get("status") != "草稿":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已发布"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出指标报表数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"报表文档数据集",
            "operation": "归档",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
