"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class OrderParseService(BaseModuleService):
    MODULE = "order_parse"
    ENTITY = "解析记录"
    OPERATION_TERM = "解析"
    LIST_FIELDS = ["记录编号", "渠道标识", "字段映射版本", "解析行数", "失败行数"]
    REQUIRED_FIELDS = ["记录编号", "渠道标识", "字段映射版本"]
    STATUS_ORDER = ["待解析", "已解析", "部分失败"]
    ACTION_RULES = {"执行解析": "已解析", "标记失败": "部分失败"}
    NEGATIVE_ACTIONS = []
