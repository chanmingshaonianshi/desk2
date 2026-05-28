<template>
  <div class="page-stack">
    <el-alert
      title="这里保留详细健康和压力数据，用于售后复盘、产品体验分析和课程图表展示；首页只保留运营关键指标。"
      type="info"
      show-icon
      :closable="false"
    />

    <div class="panel-grid">
      <el-card shadow="never">
        <template #header>健康评分趋势</template>
        <BaseChart :option="scoreOption" />
      </el-card>
      <el-card shadow="never">
        <template #header>入座时长柱状图</template>
        <BaseChart :option="durationOption" />
      </el-card>
    </div>

    <div class="panel-grid">
      <el-card shadow="never">
        <template #header>不良坐姿次数</template>
        <BaseChart :option="badPostureOption" />
      </el-card>
      <el-card shadow="never">
        <template #header>左右压力曲线</template>
        <BaseChart :option="pressureOption" />
      </el-card>
    </div>

    <UserTable :users="users" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import BaseChart from "../components/BaseChart.vue";
import UserTable from "../components/UserTable.vue";

const props = defineProps({
  analytics: {
    type: Object,
    default: () => ({ timeline: [], pressure_points: [] }),
  },
  users: {
    type: Array,
    default: () => [],
  },
});

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

const durationOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 52, right: 16, top: 24, bottom: 36 },
  xAxis: { type: "category", data: dates.value },
  yAxis: { type: "value" },
  series: [
    {
      type: "bar",
      name: "入座分钟",
      data: timeline.value.map((item) => item.total_seated_minutes),
      itemStyle: { color: "#2563eb" },
    },
  ],
}));

const badPostureOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 48, right: 16, top: 24, bottom: 36 },
  xAxis: { type: "category", data: dates.value },
  yAxis: { type: "value" },
  series: [
    {
      type: "bar",
      name: "异常次数",
      data: timeline.value.map((item) => item.bad_posture_count),
      itemStyle: { color: "#dc2626" },
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
