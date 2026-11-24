"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class StoreMapService(BaseModuleService):
    MODULE = "store_map"
    ENTITY = "门店条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["条目编号", "渠道门店码", "标准门店码", "区域归属", "生效时间"]
    REQUIRED_FIELDS = ["条目编号", "渠道门店码", "标准门店码"]
    STATUS_ORDER = ["候选", "已生效", "已失效"]
    ACTION_RULES = {"生效条目": "已生效", "失效条目": "已失效"}
    NEGATIVE_ACTIONS = []
