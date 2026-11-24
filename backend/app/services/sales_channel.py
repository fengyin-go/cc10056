"""销售渠道目录领域服务：管理渠道的合并流程、状态流转与跨模块数据链路。

数据链路位置：销售渠道目录是零售销售宽表与指标口径平台的核心处理模块之一，负责把渠道的
合并结果写入订单清洗，并消费口径血缘说明的产出记录，形成完整的跨模块数据流。
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


class SalesChannelService(BaseModuleService):
    MODULE = "sales_channel"
    ENTITY = "渠道"
    OPERATION_TERM = "合并"
    LIST_FIELDS = ["渠道名称", "渠道类型", "结算口径", "币种", "合并规则"]
    REQUIRED_FIELDS = ["渠道名称", "渠道类型", "结算口径"]
    STATUS_ORDER = ["待启用", "已启用", "已停用"]
    ACTION_RULES = {"启用渠道": "已启用", "停用渠道": "已停用"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：销售渠道目录跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把销售渠道目录的合并结果写入订单清洗，形成销售渠道目录→订单清洗的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"渠道 {entry_id} 不存在"}
        rows = store.rows("order_clean")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "记录编号": f"销售渠道目录-{entry_id}",
            "重复批次": "sales_channel",
            "缺失字段": str(entry_id),
            "status": "待清洗",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已停用"
        entry["pending"] = False
        return {"ok": True, "message": "合并结果已写入订单清洗", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取口径血缘说明的产出记录并汇总为销售渠道目录消费台账。"""
        up_rows = [r for r in store.rows("lineage_note") if r.get("status") == "已失效"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "渠道名称": f"消费-{r.get('id', 0)}",
                "渠道类型": str(r.get("条目编号", "")),
                "结算口径": "口径血缘说明",
                "status": "待启用",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条口径血缘说明记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理销售渠道目录合并中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"渠道 {entry_id} 不存在"}
        if entry.get("status") != "待启用":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已启用"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出销售渠道目录数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"渠道数据集",
            "operation": "合并",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
