"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class OrderCleanService(BaseModuleService):
    MODULE = "order_clean"
    ENTITY = "清洗记录"
    OPERATION_TERM = "清洗"
    LIST_FIELDS = ["记录编号", "重复批次", "缺失字段", "处理动作", "清洗版本"]
    REQUIRED_FIELDS = ["记录编号", "重复批次", "缺失字段"]
    STATUS_ORDER = ["待清洗", "已清洗", "已退单"]
    ACTION_RULES = {"执行清洗": "已清洗", "退回订单": "已退单"}
    NEGATIVE_ACTIONS = []
