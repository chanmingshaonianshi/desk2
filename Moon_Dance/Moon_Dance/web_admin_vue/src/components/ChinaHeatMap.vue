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
  北京: "北京市",
  上海: "上海市",
  天津: "天津市",
  重庆: "重庆市",
  河北: "河北省",
  山西: "山西省",
  辽宁: "辽宁省",
  吉林: "吉林省",
  黑龙江: "黑龙江省",
  江苏: "江苏省",
  浙江: "浙江省",
  杭州: "浙江省",
  安徽: "安徽省",
  福建: "福建省",
  江西: "江西省",
  山东: "山东省",
  河南: "河南省",
  湖北: "湖北省",
  武汉: "湖北省",
  湖南: "湖南省",
  广东: "广东省",
  广州: "广东省",
  深圳: "广东省",
  海南: "海南省",
  四川: "四川省",
  成都: "四川省",
  贵州: "贵州省",
  云南: "云南省",
  陕西: "陕西省",
  西安: "陕西省",
  甘肃: "甘肃省",
  青海: "青海省",
  台湾: "台湾省",
  内蒙古: "内蒙古自治区",
  广西: "广西壮族自治区",
  西藏: "西藏自治区",
  宁夏: "宁夏回族自治区",
  新疆: "新疆维吾尔自治区",
  香港: "香港特别行政区",
  澳门: "澳门特别行政区",
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
  const response = await fetch(`${import.meta.env.BASE_URL}maps/china.json`);
  if (!response.ok) {
    throw new Error(`中国地图数据加载失败：${response.status}`);
  }
  const geoJson = await response.json();
  echarts.registerMap("china", geoJson);
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
