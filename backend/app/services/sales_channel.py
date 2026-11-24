"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SalesChannelService(BaseModuleService):
    MODULE = "sales_channel"
    ENTITY = "渠道"
    OPERATION_TERM = "合并"
    LIST_FIELDS = ["渠道名称", "渠道类型", "结算口径", "币种", "合并规则"]
    REQUIRED_FIELDS = ["渠道名称", "渠道类型", "结算口径"]
    STATUS_ORDER = ["待启用", "已启用", "已停用"]
    ACTION_RULES = {"启用渠道": "已启用", "停用渠道": "已停用"}
    NEGATIVE_ACTIONS = ["停用渠道"]
