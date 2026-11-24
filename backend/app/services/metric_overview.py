"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MetricOverviewService(BaseModuleService):
    MODULE = "metric_overview"
    ENTITY = "概览条目"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["条目名称", "统计口径", "当前值", "趋势方向", "更新周期"]
    REQUIRED_FIELDS = ["条目名称", "统计口径", "当前值"]
    STATUS_ORDER = ["正常", "关注", "异常"]
    ACTION_RULES = {"刷新条目": "正常", "确认异常": "关注"}
    NEGATIVE_ACTIONS = []
