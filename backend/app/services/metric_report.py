"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MetricReportService(BaseModuleService):
    MODULE = "metric_report"
    ENTITY = "报表文档"
    OPERATION_TERM = "归档"
    LIST_FIELDS = ["报表编号", "覆盖周期", "指标清单", "对比结论", "发布版本"]
    REQUIRED_FIELDS = ["报表编号", "覆盖周期", "指标清单"]
    STATUS_ORDER = ["草稿", "已发布", "已归档"]
    ACTION_RULES = {"发布报表": "已发布", "归档报表": "已归档"}
    NEGATIVE_ACTIONS = []
