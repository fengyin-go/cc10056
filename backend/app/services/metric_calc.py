"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MetricCalcService(BaseModuleService):
    MODULE = "metric_calc"
    ENTITY = "计算任务"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["任务编号", "指标标识", "计算窗口", "输入分区", "结果集版本"]
    REQUIRED_FIELDS = ["任务编号", "指标标识", "计算窗口"]
    STATUS_ORDER = ["待计算", "计算中", "已完成", "需重算"]
    ACTION_RULES = {"启动计算": "计算中", "触发重算": "需重算"}
    NEGATIVE_ACTIONS = []
