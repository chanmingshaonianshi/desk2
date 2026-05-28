<template>
  <div class="map-panel">
    <div ref="chartRef" class="china-map"></div>
    <div class="map-rank">
      <div v-for="item in ranking" :key="item.name" class="map-rank-item">
        <div>
          <strong>{{ item.name }}</strong>
          <span>{{ item.value }} 台设备</span>
        </div>
        <el-progress :percentage="item.percentage" :show-text="false" />
      </div>
      <el-empty v-if="!ranking.length" description="暂无省份使用数据" />
    </div>
  </div>
</template>

<script setup>
import * as echarts from "echarts";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps({
  regions: {
    type: Array,
    default: () => [],
  },
});

const chartRef = ref(null);
let chart = null;
let resizeObserver = null;

const provinceMap = {
  北京: "北京",
  上海: "上海",
  天津: "天津",
  重庆: "重庆",
  河北: "河北",
  山西: "山西",
  辽宁: "辽宁",
  吉林: "吉林",
  黑龙江: "黑龙江",
  江苏: "江苏",
  浙江: "浙江",
  杭州: "浙江",
  安徽: "安徽",
  福建: "福建",
  江西: "江西",
  山东: "山东",
  河南: "河南",
  湖北: "湖北",
  武汉: "湖北",
  湖南: "湖南",
  广东: "广东",
  广州: "广东",
  深圳: "广东",
  海南: "海南",
  四川: "四川",
  成都: "四川",
  贵州: "贵州",
  云南: "云南",
  陕西: "陕西",
  西安: "陕西",
  甘肃: "甘肃",
  青海: "青海",
  台湾: "台湾",
  内蒙古: "内蒙古",
  广西: "广西",
  西藏: "西藏",
  宁夏: "宁夏",
  新疆: "新疆",
  香港: "香港",
  澳门: "澳门",
};

const mapData = computed(() => {
  const totals = {};
  props.regions.forEach((item) => {
    const province = provinceMap[item.name] || item.name;
    totals[province] = (totals[province] || 0) + Number(item.value || 0);
  });
  return Object.entries(totals).map(([name, value]) => ({ name, value }));
});

const maxValue = computed(() => Math.max(...mapData.value.map((item) => item.value), 1));

const ranking = computed(() => {
  return [...mapData.value]
    .sort((a, b) => b.value - a.value)
    .slice(0, 8)
    .map((item) => ({
      ...item,
      percentage: Math.round((item.value / maxValue.value) * 100),
    }));
});

async function ensureChinaMap() {
  if (echarts.getMap("china")) return;
  const sources = [
    "https://cdn.jsdelivr.net/gh/apache/echarts-website@asf-site/examples/data/asset/geo/China.json",
    "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
  ];
  for (const source of sources) {
    try {
      const response = await fetch(source);
      if (!response.ok) continue;
      const geoJson = await response.json();
      echarts.registerMap("china", geoJson);
      return;
    } catch (error) {
      console.warn("China map source failed:", source, error);
    }
  }
  throw new Error("中国地图数据加载失败");
}

async function renderChart() {
  if (!chartRef.value) return;
  await ensureChinaMap();
  if (!chart) chart = echarts.init(chartRef.value);
  chart.setOption(
    {
      tooltip: {
        trigger: "item",
        formatter: (params) => `${params.name}<br/>设备数：${params.value || 0} 台`,
      },
      visualMap: {
        min: 0,
        max: maxValue.value,
        left: 12,
        bottom: 16,
        text: ["高", "低"],
        calculable: true,
        inRange: {
          color: ["#e8f1ff", "#8bb8ff", "#2563eb"],
        },
      },
      series: [
        {
          name: "省份设备热度",
          type: "map",
          map: "china",
          roam: false,
          emphasis: {
            label: { show: true },
            itemStyle: { areaColor: "#f59e0b" },
          },
          itemStyle: {
            borderColor: "#ffffff",
            borderWidth: 1,
          },
          data: mapData.value,
        },
      ],
    },
    true
  );
  chart.resize();
}

onMounted(() => {
  nextTick(renderChart);
  resizeObserver = new ResizeObserver(() => chart?.resize());
  resizeObserver.observe(chartRef.value);
});

watch(mapData, () => nextTick(renderChart), { deep: true });

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  chart?.dispose();
});
</script>
