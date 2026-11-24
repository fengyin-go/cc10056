"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DimSliceService(BaseModuleService):
    MODULE = "dim_slice"
    ENTITY = "切片定义"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["切片名称", "维度组合", "切片条件", "样本量", "生效标记"]
    REQUIRED_FIELDS = ["切片名称", "维度组合", "切片条件"]
    STATUS_ORDER = ["草稿", "已生效", "已停用"]
    ACTION_RULES = {"生效切片": "已生效", "停用切片": "已停用"}
    NEGATIVE_ACTIONS = ["停用切片"]
