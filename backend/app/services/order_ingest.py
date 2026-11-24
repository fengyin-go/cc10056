"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class OrderIngestService(BaseModuleService):
    MODULE = "order_ingest"
    ENTITY = "订单批次"
    OPERATION_TERM = "接入"
    LIST_FIELDS = ["批次编号", "渠道标识", "批次行数", "首单时间", "末单时间"]
    REQUIRED_FIELDS = ["批次编号", "渠道标识", "批次行数"]
    STATUS_ORDER = ["待接入", "已接入", "已退回"]
    ACTION_RULES = {"确认接入": "已接入", "退回批次": "已退回"}
    NEGATIVE_ACTIONS = []
