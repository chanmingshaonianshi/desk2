<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <div>
          <span>设备售后台账</span>
          <p class="card-subtitle">用于查看已售坐垫的运行状态、绑定用户和跟进建议</p>
        </div>
        <el-segmented v-model="statusFilter" :options="filterOptions" />
      </div>
    </template>

    <el-table :data="filteredDevices" stripe border height="640">
      <el-table-column prop="device_id" label="设备编号" min-width="130" fixed />
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
      <el-table-column label="最后上报" min-width="150">
        <template #default="{ row }">{{ formatTime(row.last_update_ms) }}</template>
      </el-table-column>
      <el-table-column label="处理建议" min-width="240">
        <template #default="{ row }">{{ adviceFor(row) }}</template>
      </el-table-column>
      <el-table-column label="压力/偏差" min-width="180">
        <template #default="{ row }">
          左 {{ row.left_force_n }}N / 右 {{ row.right_force_n }}N / {{ percent(row.deviation_ratio) }}
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  devices: {
    type: Array,
    default: () => [],
  },
});

const statusFilter = ref("all");
const filterOptions = [
  { label: "全部", value: "all" },
  { label: "在线", value: "online" },
  { label: "离线", value: "offline" },
  { label: "异常", value: "abnormal" },
];

const filteredDevices = computed(() => {
  if (statusFilter.value === "online") return props.devices.filter((item) => item.is_online);
  if (statusFilter.value === "offline") return props.devices.filter((item) => !item.is_online);
  if (statusFilter.value === "abnormal") return props.devices.filter((item) => item.posture_status !== "normal");
  return props.devices;
});

function percent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

function formatTime(value) {
  if (!value) return "暂无上报";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

function adviceFor(device) {
  if (!device.is_online) return "优先确认客户设备是否断电、断网或未继续使用";
  if (device.posture_status !== "normal") return "建议售后回访，指导用户调整坐姿或重新校准坐垫";
  return "运行正常，暂无处理";
}
</script>
