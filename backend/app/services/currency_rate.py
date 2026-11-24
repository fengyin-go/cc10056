"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CurrencyRateService(BaseModuleService):
    MODULE = "currency_rate"
    ENTITY = "汇率记录"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["记录编号", "币种对", "适用日期", "汇率值", "口径来源"]
    REQUIRED_FIELDS = ["记录编号", "币种对", "适用日期"]
    STATUS_ORDER = ["待生效", "已生效", "已废弃"]
    ACTION_RULES = {"生效汇率": "已生效", "废弃汇率": "已废弃"}
    NEGATIVE_ACTIONS = []
