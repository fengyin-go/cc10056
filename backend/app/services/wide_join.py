"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class WideJoinService(BaseModuleService):
    MODULE = "wide_join"
    ENTITY = "关联任务"
    OPERATION_TERM = "关联"
    LIST_FIELDS = ["任务编号", "事实分区", "维表组合", "关联键集", "未命中率"]
    REQUIRED_FIELDS = ["任务编号", "事实分区", "维表组合"]
    STATUS_ORDER = ["待关联", "关联中", "已完成"]
    ACTION_RULES = {"启动关联": "关联中", "确认完成": "已完成"}
    NEGATIVE_ACTIONS = []
