<template>
  <div class="page-stack">
    <div class="metric-grid">
      <el-card v-for="metric in metrics" :key="metric.label" shadow="never" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </el-card>
    </div>

    <div class="panel-grid">
      <el-card shadow="never">
        <template #header>健康评分趋势</template>
        <BaseChart :option="scoreOption" />
      </el-card>
      <el-card shadow="never">
        <template #header>地域分布</template>
        <BaseChart :option="regionOption" />
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>左右压力曲线</template>
      <BaseChart :option="pressureOption" />
    </el-card>
  </div>
</template>

<script setup>
import { computed } from "vue";
import BaseChart from "../components/BaseChart.vue";

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({}),
  },
  regions: {
    type: Array,
    default: () => [],
  },
  analytics: {
    type: Object,
    default: () => ({ timeline: [], pressure_points: [] }),
  },
});

const metrics = computed(() => [
  { label: "注册设备", value: props.summary.registered_devices || 0, hint: "已绑定或已上报" },
  { label: "在线设备", value: props.summary.online_devices || 0, hint: "60 秒内有数据" },
  { label: "异常坐姿", value: props.summary.bad_posture_devices || 0, hint: "偏差大于 10%" },
  { label: "平均健康分", value: props.summary.avg_health_score || 0, hint: "按日汇总统计" },
]);

const timeline = computed(() => props.analytics.timeline || []);
const pressure = computed(() => props.analytics.pressure_points || []);
const dates = computed(() => timeline.value.map((item) => item.date.slice(5)));

const scoreOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 42, right: 18, top: 24, bottom: 36 },
  xAxis: { type: "category", data: dates.value },
  yAxis: { type: "value", min: 0, max: 100 },
  series: [
    {
      type: "line",
      smooth: true,
      name: "健康分",
      data: timeline.value.map((item) => item.avg_health_score),
      lineStyle: { width: 3 },
    },
  ],
}));

const regionOption = computed(() => ({
  tooltip: { trigger: "item" },
  series: [
    {
      type: "pie",
      radius: ["45%", "72%"],
      data: props.regions,
      label: { formatter: "{b}: {c}" },
    },
  ],
}));

const pressureOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0 },
  grid: { left: 48, right: 20, top: 44, bottom: 42 },
  xAxis: { type: "category", data: pressure.value.map((item) => item.time) },
  yAxis: { type: "value" },
  series: [
    { type: "line", smooth: true, name: "左压力", data: pressure.value.map((item) => item.left_force_n) },
    { type: "line", smooth: true, name: "右压力", data: pressure.value.map((item) => item.right_force_n) },
  ],
}));
</script>
