<template>
  <div class="page-stack">
    <div class="metric-grid seller-metrics">
      <el-card v-for="metric in metrics" :key="metric.label" shadow="never" class="metric-card">
        <span>{{ metric.label }}</span>
        <strong>{{ metric.value }}</strong>
        <small>{{ metric.hint }}</small>
      </el-card>
    </div>

    <div class="overview-grid">
      <el-card shadow="never" class="priority-card">
        <template #header>
          <div class="card-header">
            <span>今日运营提醒</span>
            <el-tag :type="followUpDevices.length ? 'warning' : 'success'">
              {{ followUpDevices.length ? `${followUpDevices.length} 台待跟进` : "状态良好" }}
            </el-tag>
          </div>
        </template>
        <div class="notice-list">
          <div class="notice-item">
            <strong>{{ activeRate }}%</strong>
            <span>当前设备活跃率，优先关注长期离线设备。</span>
          </div>
          <div class="notice-item">
            <strong>{{ offlineCount }}</strong>
            <span>台设备离线，建议售后确认供电、网络或绑定状态。</span>
          </div>
          <div class="notice-item">
            <strong>{{ abnormalCount }}</strong>
            <span>台设备出现坐姿异常，可作为用户使用指导或产品体验回访线索。</span>
          </div>
        </div>
      </el-card>

      <el-card shadow="never">
        <template #header>
          <div class="card-header">
            <span>地区设备使用情况</span>
            <el-tag type="info">按设备数量排序</el-tag>
          </div>
        </template>
        <div class="region-list">
          <div v-for="region in regionRanking" :key="region.name" class="region-item">
            <div>
              <strong>{{ region.name }}</strong>
              <span>{{ region.value }} 台设备</span>
            </div>
            <el-progress :percentage="region.percentage" :show-text="false" />
          </div>
          <el-empty v-if="!regionRanking.length" description="暂无地域数据" />
        </div>
      </el-card>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span>待跟进设备</span>
          <span class="muted">离线和异常坐姿设备会优先显示</span>
        </div>
      </template>
      <el-table :data="followUpDevices" stripe border>
        <el-table-column prop="device_id" label="设备编号" min-width="130" />
        <el-table-column prop="region" label="地区" width="100" />
        <el-table-column label="绑定用户" min-width="140">
          <template #default="{ row }">{{ row.nickname || "未绑定" }}</template>
        </el-table-column>
        <el-table-column label="在线状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.is_online ? 'success' : 'danger'">
              {{ row.is_online ? "在线" : "离线" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="坐姿状态" width="110">
          <template #default="{ row }">
            <el-tag :type="row.posture_status === 'normal' ? 'success' : 'warning'">
              {{ row.posture_status === "normal" ? "正常" : "异常" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="处理建议" min-width="220">
          <template #default="{ row }">{{ adviceFor(row) }}</template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!followUpDevices.length" description="暂无需要跟进的设备" />
    </el-card>
  </div>
</template>

<script setup>
import { computed } from "vue";

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
const activeRate = computed(() => {
  if (!registeredCount.value) return 0;
  return Math.round((onlineCount.value / registeredCount.value) * 100);
});

const followUpDevices = computed(() => {
  return props.devices
    .filter((item) => !item.is_online || item.posture_status !== "normal")
    .sort((a, b) => Number(a.is_online) - Number(b.is_online))
    .slice(0, 8);
});

const metrics = computed(() => [
  { label: "已售/已注册设备", value: registeredCount.value, hint: "已绑定或已上报的坐垫" },
  { label: "活跃设备", value: `${onlineCount.value} 台`, hint: `当前活跃率 ${activeRate.value}%` },
  { label: "离线待跟进", value: `${offlineCount.value} 台`, hint: "优先检查网络和供电" },
  { label: "使用异常设备", value: `${abnormalCount.value} 台`, hint: "可用于用户回访和指导" },
]);

const regionRanking = computed(() => {
  const max = Math.max(...props.regions.map((item) => item.value || 0), 1);
  return [...props.regions]
    .sort((a, b) => (b.value || 0) - (a.value || 0))
    .slice(0, 8)
    .map((item) => ({
      ...item,
      percentage: Math.round(((item.value || 0) / max) * 100),
    }));
});

function adviceFor(device) {
  if (!device.is_online) return "联系客户确认设备供电、网络连接或是否已停止使用";
  if (device.posture_status !== "normal") return "建议客服回访，指导用户正确摆放坐垫和调整坐姿";
  return "持续观察";
}
</script>
