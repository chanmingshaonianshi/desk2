<template>
  <div class="page-stack">
    <el-alert
      title="这里用于复盘设备使用趋势和省份运营表现，重点关注投放效果、活跃率和售后跟进优先级。"
      type="info"
      show-icon
      :closable="false"
    />

    <div class="analysis-summary">
      <div>
        <span>重点省份</span>
        <strong>{{ topRegion?.province || "暂无" }}</strong>
        <small>{{ topRegion ? `${topRegion.total} 台设备，活跃率 ${topRegion.activeRate}%` : "等待设备数据" }}</small>
      </div>
      <div>
        <span>离线压力最高</span>
        <strong>{{ riskRegion?.province || "暂无" }}</strong>
        <small>{{ riskRegion ? `${riskRegion.offline} 台离线，离线率 ${riskRegion.offlineRate}%` : "暂无离线地区" }}</small>
      </div>
      <div>
        <span>运营建议</span>
        <strong>{{ primaryAdvice }}</strong>
        <small>按省份设备数和活跃率自动生成</small>
      </div>
    </div>

    <div class="panel-grid">
      <el-card shadow="never">
        <template #header>使用质量评分趋势</template>
        <BaseChart :option="scoreOption" />
      </el-card>
      <el-card shadow="never">
        <template #header>入座时长趋势</template>
        <BaseChart :option="durationOption" />
      </el-card>
    </div>

    <div class="panel-grid">
      <el-card shadow="never">
        <template #header>省份设备数量排行</template>
        <BaseChart :option="regionRankOption" />
      </el-card>
      <el-card shadow="never">
        <template #header>省份在线/离线对比</template>
        <BaseChart :option="regionStatusOption" />
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div>
            <span>省份运营明细</span>
            <p class="card-subtitle">按省份汇总设备数量、在线状态和运营建议。</p>
          </div>
          <el-tag type="info">共 {{ regionTableRows.length }} 个省份</el-tag>
        </div>
      </template>

      <el-table :data="regionTableRows" stripe border>
        <el-table-column prop="province" label="省份" min-width="120" />
        <el-table-column prop="total" label="设备数" width="110" />
        <el-table-column prop="online" label="活跃设备" width="120" />
        <el-table-column prop="offline" label="离线设备" width="120" />
        <el-table-column label="活跃率" min-width="170">
          <template #default="{ row }">
            <el-progress :percentage="row.activeRate" :stroke-width="10" />
          </template>
        </el-table-column>
        <el-table-column label="运营建议" min-width="260">
          <template #default="{ row }">{{ adviceForRegion(row) }}</template>
        </el-table-column>
      </el-table>
    </el-card>

    <UserTable :users="users" />
  </div>
</template>

<script setup>
import { computed } from "vue";
import BaseChart from "../components/BaseChart.vue";
import UserTable from "../components/UserTable.vue";
import { adviceForRegion, buildRegionStats } from "../utils/operations";

const props = defineProps({
  analytics: {
    type: Object,
    default: () => ({ timeline: [] }),
  },
  users: {
    type: Array,
    default: () => [],
  },
  devices: {
    type: Array,
    default: () => [],
  },
  regions: {
    type: Array,
    default: () => [],
  },
});

const regionProvinceMap = {
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
  南京: "江苏",
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

const timeline = computed(() => props.analytics.timeline || []);
const dates = computed(() => timeline.value.map((item) => item.date.slice(5)));

function toProvince(region) {
  const text = String(region || "未知").trim();
  return regionProvinceMap[text] || text || "未知";
}

const normalizedDevices = computed(() => props.devices.map((device) => ({ ...device, region: toProvince(device.region) })));
const normalizedRegions = computed(() => props.regions.map((region) => ({ ...region, name: toProvince(region.name) })));
const regionDeviceStats = computed(() => buildRegionStats(normalizedDevices.value, normalizedRegions.value));

const regionTopRows = computed(() => regionDeviceStats.value.slice(0, 10));

const regionTableRows = computed(() => regionDeviceStats.value);
const topRegion = computed(() => regionDeviceStats.value[0]);
const riskRegion = computed(() => [...regionDeviceStats.value].sort((a, b) => b.offlineRate - a.offlineRate || b.offline - a.offline)[0]);
const primaryAdvice = computed(() => (topRegion.value ? adviceForRegion(topRegion.value) : "暂无运营建议"));

const scoreOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 42, right: 18, top: 24, bottom: 36 },
  xAxis: { type: "category", data: dates.value },
  yAxis: { type: "value", min: 0, max: 100 },
  series: [
    {
      type: "line",
      smooth: true,
      name: "使用质量评分",
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
      itemStyle: { color: "#3a6fd8" },
    },
  ],
}));

const regionRankOption = computed(() => ({
  tooltip: { trigger: "axis" },
  grid: { left: 72, right: 18, top: 24, bottom: 36 },
  xAxis: { type: "value" },
  yAxis: {
    type: "category",
    inverse: true,
    data: regionTopRows.value.map((item) => item.province),
  },
  series: [
    {
      type: "bar",
      name: "设备数",
      data: regionTopRows.value.map((item) => item.total),
      itemStyle: { color: "#3a6fd8" },
    },
  ],
}));

const regionStatusOption = computed(() => ({
  tooltip: { trigger: "axis" },
  legend: { top: 0 },
  grid: { left: 48, right: 18, top: 44, bottom: 42 },
  xAxis: {
    type: "category",
    data: regionTopRows.value.map((item) => item.province),
  },
  yAxis: { type: "value" },
  series: [
    {
      type: "bar",
      stack: "device-status",
      name: "活跃设备",
      data: regionTopRows.value.map((item) => item.online),
      itemStyle: { color: "#4f8f6b" },
    },
    {
      type: "bar",
      stack: "device-status",
      name: "离线设备",
      data: regionTopRows.value.map((item) => item.offline),
      itemStyle: { color: "#b8873b" },
    },
  ],
}));

</script>
