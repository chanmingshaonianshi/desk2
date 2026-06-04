<template>
  <div class="page-stack">
    <el-alert
      title="这里展示设备使用趋势和省份运营情况，帮助运营人员判断投放效果、活跃情况和售后跟进重点。"
      type="info"
      show-icon
      :closable="false"
    />

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

const regionDeviceStats = computed(() => {
  const stats = new Map();

  function ensure(province) {
    if (!stats.has(province)) {
      stats.set(province, { province, total: 0, online: 0, offline: 0 });
    }
    return stats.get(province);
  }

  props.devices.forEach((device) => {
    const item = ensure(toProvince(device.region));
    item.total += 1;
    if (device.is_online) {
      item.online += 1;
    } else {
      item.offline += 1;
    }
  });

  props.regions.forEach((region) => {
    const item = ensure(toProvince(region.name));
    const total = Number(region.value || 0);
    if (!props.devices.length) {
      item.total += total;
      item.offline = Math.max(item.total - item.online, 0);
    } else if (total > item.total) {
      item.total = total;
      item.offline = Math.max(total - item.online, 0);
    }
  });

  return [...stats.values()]
    .map((item) => ({
      ...item,
      activeRate: item.total ? Math.round((item.online / item.total) * 100) : 0,
    }))
    .sort((a, b) => b.total - a.total || b.online - a.online);
});

const regionTopRows = computed(() => regionDeviceStats.value.slice(0, 10));

const regionTableRows = computed(() => regionDeviceStats.value);

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
      itemStyle: { color: "#2563eb" },
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
      itemStyle: { color: "#2563eb" },
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
      itemStyle: { color: "#16a34a" },
    },
    {
      type: "bar",
      stack: "device-status",
      name: "离线设备",
      data: regionTopRows.value.map((item) => item.offline),
      itemStyle: { color: "#f59e0b" },
    },
  ],
}));

function adviceForRegion(row) {
  if (!row.total) return "暂无设备数据，等待设备绑定或上报。";
  if (row.activeRate >= 70) return "活跃表现较好，可继续扩大投放和渠道覆盖。";
  if (row.activeRate >= 30) return "活跃率一般，建议结合离线设备做客服回访。";
  return "活跃率偏低，优先排查网络、供电和售后跟进情况。";
}
</script>
