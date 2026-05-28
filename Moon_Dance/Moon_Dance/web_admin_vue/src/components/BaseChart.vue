<template>
  <div ref="chartRef" class="chart"></div>
</template>

<script setup>
import * as echarts from "echarts";
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  option: {
    type: Object,
    required: true,
  },
});

const chartRef = ref(null);
let chart = null;
let resizeObserver = null;

function renderChart() {
  if (!chartRef.value) return;
  if (!chart) {
    chart = echarts.init(chartRef.value);
  }
  chart.setOption(props.option, true);
  chart.resize();
}

onMounted(() => {
  nextTick(renderChart);
  resizeObserver = new ResizeObserver(() => chart?.resize());
  resizeObserver.observe(chartRef.value);
});

watch(
  () => props.option,
  () => nextTick(renderChart),
  { deep: true }
);

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
});
</script>
