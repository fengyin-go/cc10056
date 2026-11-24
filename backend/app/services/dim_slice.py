"""维度切片领域服务：管理切片定义的校验流程、状态流转与跨模块数据链路。

数据链路位置：维度切片是零售销售宽表与指标口径平台的核心处理模块之一，负责把切片定义的
校验结果写入口径血缘说明，并消费宽表关联的产出记录，形成完整的跨模块数据流。
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


class DimSliceService(BaseModuleService):
    MODULE = "dim_slice"
    ENTITY = "切片定义"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["切片名称", "维度组合", "切片条件", "样本量", "生效标记"]
    REQUIRED_FIELDS = ["切片名称", "维度组合", "切片条件"]
    STATUS_ORDER = ["草稿", "已生效", "已停用"]
    ACTION_RULES = {"生效切片": "已生效", "停用切片": "已停用"}
    NEGATIVE_ACTIONS = []

    # ---- 业务扩展：维度切片跨模块数据链路 ----

    def push_to_downstream(self, entry_id: int) -> dict[str, Any]:
        """把维度切片的校验结果写入口径血缘说明，形成维度切片→口径血缘说明的跨模块数据链路。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"切片定义 {entry_id} 不存在"}
        rows = store.rows("lineage_note")
        new_id = _next_id(rows)
        rows.append({
            "id": new_id,
            "条目编号": f"维度切片-{entry_id}",
            "指标标识": "dim_slice",
            "依赖表清单": str(entry_id),
            "status": "待梳理",
            "pending": True,
            "abnormal": False,
        })
        entry["status"] = "已停用"
        entry["pending"] = False
        return {"ok": True, "message": "校验结果已写入口径血缘说明", "downstream_id": new_id}

    def consume_from_upstream(self) -> dict[str, Any]:
        """读取宽表关联的产出记录并汇总为维度切片消费台账。"""
        up_rows = [r for r in store.rows("wide_join") if r.get("status") == "已完成"]
        rows = store.rows(self.MODULE)
        receipt_id = _next_id(rows)
        for idx, r in enumerate(up_rows[:5], start=1):
            rows.append({
                "id": receipt_id + idx - 1,
                "切片名称": f"消费-{r.get('id', 0)}",
                "维度组合": str(r.get("任务编号", "")),
                "切片条件": "宽表关联",
                "status": "草稿",
                "pending": True,
                "abnormal": False,
            })
        return {"ok": True, "message": f"已消费{len(up_rows[:5])}条宽表关联记录", "consumed": len(up_rows[:5])}

    def recover_interrupted(self, entry_id: int) -> dict[str, Any]:
        """处理维度切片校验中断：续写未完成记录，不覆盖上次完整结果。"""
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return {"ok": False, "message": f"切片定义 {entry_id} 不存在"}
        if entry.get("status") != "草稿":
            return {"ok": False, "message": "仅中断中的记录可恢复"}
        entry["status"] = "已生效"
        entry["recovered_at"] = _now_iso()
        entry["pending"] = False
        return {"ok": True, "message": "已从中断点续写", "recovered": True, "entry_id": entry_id}

    def quality_snapshot(self) -> dict[str, Any]:
        """输出维度切片数据集质量快照，供跨模块审计与容量锚点回查。"""
        rows = store.rows(self.MODULE)
        by_status = {s: sum(1 for r in rows if r.get("status") == s) for s in self.STATUS_ORDER}
        return {
            "module": self.MODULE,
            "entity": self.ENTITY,
            "artifact": f"切片定义数据集",
            "operation": "校验",
            "total": len(rows),
            "by_status": by_status,
            "abnormal": sum(1 for r in rows if r.get("abnormal")),
            "snapshot_at": _now_iso(),
        }
