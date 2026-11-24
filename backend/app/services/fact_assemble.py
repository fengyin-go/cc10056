"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FactAssembleService(BaseModuleService):
    MODULE = "fact_assemble"
    ENTITY = "装配任务"
    OPERATION_TERM = "清洗"
    LIST_FIELDS = ["任务编号", "来源批次", "事实分区", "装配行数", "装配版本"]
    REQUIRED_FIELDS = ["任务编号", "来源批次", "事实分区"]
    STATUS_ORDER = ["待装配", "装配中", "已完成"]
    ACTION_RULES = {"启动装配": "装配中", "确认完成": "已完成"}
    NEGATIVE_ACTIONS = []
