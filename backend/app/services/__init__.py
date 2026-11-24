"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.sales_channel import SalesChannelService
from app.services.order_ingest import OrderIngestService
from app.services.order_parse import OrderParseService
from app.services.sku_map import SkuMapService
from app.services.store_map import StoreMapService
from app.services.currency_rate import CurrencyRateService
from app.services.order_clean import OrderCleanService
from app.services.fact_assemble import FactAssembleService
from app.services.wide_join import WideJoinService
from app.services.metric_def import MetricDefService
from app.services.metric_calc import MetricCalcService
from app.services.dim_slice import DimSliceService
from app.services.compare_period import ComparePeriodService
from app.services.anomaly_scan import AnomalyScanService
from app.services.reconcile_task import ReconcileTaskService
from app.services.metric_api import MetricApiService
from app.services.metric_report import MetricReportService
from app.services.lineage_note import LineageNoteService
from app.services.calc_review import CalcReviewService
from app.services.metric_overview import MetricOverviewService

SERVICES: dict[str, BaseModuleService] = {
    "sales_channel": SalesChannelService(),
    "order_ingest": OrderIngestService(),
    "order_parse": OrderParseService(),
    "sku_map": SkuMapService(),
    "store_map": StoreMapService(),
    "currency_rate": CurrencyRateService(),
    "order_clean": OrderCleanService(),
    "fact_assemble": FactAssembleService(),
    "wide_join": WideJoinService(),
    "metric_def": MetricDefService(),
    "metric_calc": MetricCalcService(),
    "dim_slice": DimSliceService(),
    "compare_period": ComparePeriodService(),
    "anomaly_scan": AnomalyScanService(),
    "reconcile_task": ReconcileTaskService(),
    "metric_api": MetricApiService(),
    "metric_report": MetricReportService(),
    "lineage_note": LineageNoteService(),
    "calc_review": CalcReviewService(),
    "metric_overview": MetricOverviewService(),
}


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)
