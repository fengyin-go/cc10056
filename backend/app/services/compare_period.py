"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ComparePeriodService(BaseModuleService):
    MODULE = "compare_period"
    ENTITY = "对比任务"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["任务编号", "指标标识", "本期窗口", "对照窗口", "差异结论"]
    REQUIRED_FIELDS = ["任务编号", "指标标识", "本期窗口"]
    STATUS_ORDER = ["待对比", "对比中", "已完成"]
    ACTION_RULES = {"启动对比": "对比中", "确认结论": "已完成"}
    NEGATIVE_ACTIONS = []
