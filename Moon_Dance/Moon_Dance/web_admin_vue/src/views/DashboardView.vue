<template>
  <div class="page-stack">
    <section class="ops-strip">
      <div v-for="metric in metrics" :key="metric.label" class="ops-strip-item" :class="metric.tone">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </div>
      <div class="ops-strip-summary">
        <span>今日处理重点</span>
        <strong>{{ todayFocus }}</strong>
      </div>
    </section>

    <div class="workbench-grid">
      <el-card shadow="never" class="follow-card">
        <template #header>
          <div class="card-header">
            <div>
              <span>待跟进设备</span>
              <p class="card-subtitle">按风险等级和离线时长排序，优先处理高风险设备。</p>
            </div>
            <el-tag :type="highRiskCount ? 'danger' : followUpDevices.length ? 'warning' : 'success'">
              {{ highRiskCount ? `${highRiskCount} 台高风险` : followUpDevices.length ? `${followUpDevices.length} 台待跟进` : "状态稳定" }}
            </el-tag>
          </div>
        </template>

        <div class="follow-list" v-if="followUpDevices.length">
          <div v-for="device in followUpDevices" :key="device.device_id" class="follow-item">
            <div>
              <strong>{{ device.device_id }}</strong>
              <span>{{ device.region }} · {{ device.nickname || "未绑定用户" }}</span>
            </div>
            <el-tag :type="device.riskTagType">{{ device.riskLabel }}</el-tag>
            <small>上报间隔：{{ device.offlineDurationText }}</small>
            <p>{{ device.operationAdvice }}</p>
          </div>
        </div>
        <el-empty v-else description="暂无需要跟进的设备" />
      </el-card>

      <el-card shadow="never" class="map-card">
        <template #header>
          <div class="card-header">
            <div>
              <span>地区使用热度</span>
              <p class="card-subtitle">用于判断各省份设备投放和活跃表现。</p>
            </div>
            <el-tag type="info">地图热力图</el-tag>
          </div>
        </template>
        <ChinaHeatMap :regions="regions" />
      </el-card>
    </div>

    <div class="decision-grid">
      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <span>运营建议</span>
              <p class="card-subtitle">根据地区设备数、活跃率和离线情况生成处理方向。</p>
            </div>
            <el-tag type="info">Top {{ regionAdviceRows.length }}</el-tag>
          </div>
        </template>
        <div class="region-advice-list">
          <div v-for="row in regionAdviceRows" :key="row.province" class="region-advice-item">
            <strong>{{ row.province }}</strong>
            <span>{{ row.total }} 台设备 · 活跃率 {{ row.activeRate }}% · 离线 {{ row.offline }} 台</span>
            <p>{{ adviceForRegion(row) }}</p>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <div>
              <span>设备状态摘要</span>
              <p class="card-subtitle">用于快速判断当前设备资产运行结构。</p>
            </div>
            <el-tag type="info">运营口径</el-tag>
          </div>
        </template>
        <div class="status-board">
          <div>
            <span>活跃率</span>
            <strong>{{ activeRate }}%</strong>
          </div>
          <div>
            <span>离线设备</span>
            <strong>{{ offlineCount }}</strong>
          </div>
          <div>
            <span>高风险设备</span>
            <strong>{{ highRiskCount }}</strong>
          </div>
          <div>
            <span>未绑定设备</span>
            <strong>{{ unboundCount }}</strong>
          </div>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup>
import { computed } from "vue";
import ChinaHeatMap from "../components/ChinaHeatMap.vue";
import { adviceForRegion, buildRegionStats, enrichDevice } from "../utils/operations";

const props = defineProps({
  summary: {
    type: Object,
    default: () => ({}),
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

const registeredCount = computed(() => props.summary.registered_devices || props.devices.length || 0);
const onlineCount = computed(() => props.summary.online_devices || props.devices.filter((item) => item.is_online).length);
const offlineCount = computed(() => Math.max(registeredCount.value - onlineCount.value, 0));
const abnormalCount = computed(() => props.summary.bad_posture_devices || props.devices.filter((item) => item.posture_status !== "normal").length);
const enrichedDevices = computed(() => props.devices.map((item) => enrichDevice(item)));
const highRiskCount = computed(() => enrichedDevices.value.filter((item) => item.riskLevel === "high").length);
const unboundCount = computed(() => enrichedDevices.value.filter((item) => item.boundStatus === "unbound").length);
const activeRate = computed(() => {
  if (!registeredCount.value) return 0;
  return Math.round((onlineCount.value / registeredCount.value) * 100);
});

const followUpDevices = computed(() => {
  return enrichedDevices.value
    .filter((item) => item.riskLevel !== "normal")
    .sort((a, b) => a.followUpPriority - b.followUpPriority || Number(a.last_update_ms || 0) - Number(b.last_update_ms || 0))
    .slice(0, 8);
});

const metrics = computed(() => [
  { label: "已注册设备", value: registeredCount.value, hint: "已绑定或已上报", tone: "neutral" },
  { label: "活跃设备", value: `${onlineCount.value} 台`, hint: `活跃率 ${activeRate.value}%`, tone: "success" },
  { label: "离线待查", value: `${offlineCount.value} 台`, hint: "检查网络和供电", tone: "warning" },
  { label: "高风险设备", value: `${highRiskCount.value} 台`, hint: "优先售后跟进", tone: "danger" },
]);

const regionAdviceRows = computed(() => buildRegionStats(enrichedDevices.value, props.regions).slice(0, 4));

const todayFocus = computed(() => {
  if (highRiskCount.value) return "优先处理高风险离线设备";
  if (offlineCount.value) return "排查离线设备上报状态";
  if (abnormalCount.value) return "安排异常使用回访";
  return "维持当前运营节奏";
});
</script>
