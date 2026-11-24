"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class MetricApiService(BaseModuleService):
    MODULE = "metric_api"
    ENTITY = "服务请求"
    OPERATION_TERM = "写入"
    LIST_FIELDS = ["请求编号", "指标标识", "查询参数", "返回行数", "服务耗时"]
    REQUIRED_FIELDS = ["请求编号", "指标标识", "查询参数"]
    STATUS_ORDER = ["已受理", "已返回", "已缓存"]
    ACTION_RULES = {"执行查询": "已返回", "写入缓存": "已缓存"}
    NEGATIVE_ACTIONS = []
