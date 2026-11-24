"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MetricDefService(BaseModuleService):
    MODULE = "metric_def"
    ENTITY = "指标定义"
    OPERATION_TERM = "计算"
    LIST_FIELDS = ["指标名称", "计算公式", "统计粒度", "过滤条件", "口径版本"]
    REQUIRED_FIELDS = ["指标名称", "计算公式", "统计粒度"]
    STATUS_ORDER = ["草稿", "已发布", "已下线"]
    ACTION_RULES = {"发布指标": "已发布", "下线指标": "已下线"}
    NEGATIVE_ACTIONS = ["下线指标"]
