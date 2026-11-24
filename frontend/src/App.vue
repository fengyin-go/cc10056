<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">零售销售宽表与指标口径平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">接入多渠道销售订单，完成解析、映射、清洗与宽表装配，按指标口径计算同环比并对账的数据分析平台</span>
        <span class="head-user">当前值班：数据工程组</span>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
const navItems = [{ label: "运营概览", path: "/" }, { label: "销售渠道目录", path: "/sales_channel" }, { label: "订单接入", path: "/order_ingest" }, { label: "订单解析", path: "/order_parse" }, { label: "商品映射", path: "/sku_map" }, { label: "门店映射", path: "/store_map" }, { label: "汇率换算", path: "/currency_rate" }, { label: "订单清洗", path: "/order_clean" }, { label: "销售事实装配", path: "/fact_assemble" }, { label: "宽表关联", path: "/wide_join" }, { label: "指标定义", path: "/metric_def" }, { label: "指标计算", path: "/metric_calc" }, { label: "维度切片", path: "/dim_slice" }, { label: "同环比对比", path: "/compare_period" }, { label: "异动扫描", path: "/anomaly_scan" }, { label: "对账核对", path: "/reconcile_task" }, { label: "指标服务", path: "/metric_api" }, { label: "指标报表", path: "/metric_report" }, { label: "口径血缘说明", path: "/lineage_note" }, { label: "口径复核台", path: "/calc_review" }, { label: "指标总览", path: "/metric_overview" }]
</script>
