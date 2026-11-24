"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class AnomalyScanService(BaseModuleService):
    MODULE = "anomaly_scan"
    ENTITY = "扫描任务"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["任务编号", "指标集合", "检测规则", "异动数", "扫描结论"]
    REQUIRED_FIELDS = ["任务编号", "指标集合", "检测规则"]
    STATUS_ORDER = ["待扫描", "扫描中", "已完成"]
    ACTION_RULES = {"启动扫描": "扫描中", "确认结论": "已完成"}
    NEGATIVE_ACTIONS = []
