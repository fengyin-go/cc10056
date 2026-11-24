# 零售销售宽表与指标口径平台

接入多渠道销售订单，完成解析、映射、清洗与宽表装配，按指标口径计算同环比并对账的数据分析平台

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/WorkbenchView.vue|tsx  全部模块共享工作台
│   ├── src/data/modules.ts              18个业务模块配置
│   ├── src/api/              统一请求封装
│   └── vite.config.ts        dev server 配置（open: false）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/resource.py  通用查询/导出/登记/动作接口
│   ├── app/services/<key>.py    每个模块独立领域逻辑
│   ├── app/services/base.py     共享服务骨架
│   └── app/store.py          内存数据仓库与示例数据
├── .gitignore
└── docker-compose.yml
```

## 启动

### 后端

```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./run.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`

### 前端

```bash
cd frontend
npm ci
npm run dev
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端 `http://127.0.0.1:8000`。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 销售渠道目录 | `sales_channel` | 渠道 | 渠道名称、渠道类型、结算口径 |
| 订单接入 | `order_ingest` | 订单批次 | 批次编号、渠道标识、批次行数 |
| 订单解析 | `order_parse` | 解析记录 | 记录编号、渠道标识、字段映射版本 |
| 商品映射 | `sku_map` | 映射条目 | 条目编号、渠道商品码、标准商品码 |
| 门店映射 | `store_map` | 门店条目 | 条目编号、渠道门店码、标准门店码 |
| 汇率换算 | `currency_rate` | 汇率记录 | 记录编号、币种对、适用日期 |
| 订单清洗 | `order_clean` | 清洗记录 | 记录编号、重复批次、缺失字段 |
| 销售事实装配 | `fact_assemble` | 装配任务 | 任务编号、来源批次、事实分区 |
| 宽表关联 | `wide_join` | 关联任务 | 任务编号、事实分区、维表组合 |
| 指标定义 | `metric_def` | 指标定义 | 指标名称、计算公式、统计粒度 |
| 指标计算 | `metric_calc` | 计算任务 | 任务编号、指标标识、计算窗口 |
| 维度切片 | `dim_slice` | 切片定义 | 切片名称、维度组合、切片条件 |
| 同环比对比 | `compare_period` | 对比任务 | 任务编号、指标标识、本期窗口 |
| 异动扫描 | `anomaly_scan` | 扫描任务 | 任务编号、指标集合、检测规则 |
| 对账核对 | `reconcile_task` | 对账任务 | 任务编号、渠道账期、平台口径 |
| 指标服务 | `metric_api` | 服务请求 | 请求编号、指标标识、查询参数 |
| 指标报表 | `metric_report` | 报表文档 | 报表编号、覆盖周期、指标清单 |
| 口径血缘说明 | `lineage_note` | 血缘条目 | 条目编号、指标标识、依赖表清单 |
| 口径复核台 | `calc_review` | 复核事项 | 事项编号、争议指标、原口径 |
| 指标总览 | `metric_overview` | 概览条目 | 条目名称、统计口径、当前值 |

## 约定

- 全部模块共享`frontend/src/views/WorkbenchView.vue|tsx`和一套资源路由。
- 每个模块仍保留独立`backend/app/services/<模块>.py`；纯前端保留
  `frontend/src/domain/<模块>.ts`，用于承载真实业务差异并维持36题位容量。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。

领域：数据工程
子方向：数据分析与数据应用
