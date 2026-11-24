"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ReconcileTaskService(BaseModuleService):
    MODULE = "reconcile_task"
    ENTITY = "对账任务"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["任务编号", "渠道账期", "平台口径", "差异金额", "对账结论"]
    REQUIRED_FIELDS = ["任务编号", "渠道账期", "平台口径"]
    STATUS_ORDER = ["待对账", "对账中", "已完成"]
    ACTION_RULES = {"启动对账": "对账中", "确认结论": "已完成"}
    NEGATIVE_ACTIONS = []
