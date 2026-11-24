"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class LineageNoteService(BaseModuleService):
    MODULE = "lineage_note"
    ENTITY = "血缘条目"
    OPERATION_TERM = "转换"
    LIST_FIELDS = ["条目编号", "指标标识", "依赖表清单", "转换说明", "口径版本"]
    REQUIRED_FIELDS = ["条目编号", "指标标识", "依赖表清单"]
    STATUS_ORDER = ["待梳理", "已梳理", "已失效"]
    ACTION_RULES = {"梳理条目": "已梳理", "失效条目": "已失效"}
    NEGATIVE_ACTIONS = []
