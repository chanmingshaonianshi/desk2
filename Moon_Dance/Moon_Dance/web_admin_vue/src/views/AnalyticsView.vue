<template>
  <div class="page-stack">
    <div class="panel-grid">
      <el-card shadow="never">
        <template #header>入座时长柱状图</template>
        <BaseChart :option="durationOption" />
      </el-card>
      <el-card shadow="never">
        <template #header>不良坐姿次数</template>
        <BaseChart :option="badPostureOption" />
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
    default: () => ({ timeline: [] }),
  },
  users: {
    type: Array,
    default: () => [],
  },
});

const timeline = computed(() => props.analytics.timeline || []);
const dates = computed(() => timeline.value.map((item) => item.date.slice(5)));

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
</script>
