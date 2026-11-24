"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CalcReviewService(BaseModuleService):
    MODULE = "calc_review"
    ENTITY = "复核事项"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["事项编号", "争议指标", "原口径", "建议口径", "复核结论"]
    REQUIRED_FIELDS = ["事项编号", "争议指标", "原口径"]
    STATUS_ORDER = ["待复核", "复核中", "已裁定"]
    ACTION_RULES = {"开始复核": "复核中", "提交裁定": "已裁定"}
    NEGATIVE_ACTIONS = []
