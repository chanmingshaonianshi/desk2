<template>
  <el-card shadow="never" class="ledger-card">
    <template #header>
      <div class="card-header">
        <div>
          <span>设备售后台账</span>
          <p class="card-subtitle">用于检索已售坐垫、识别离线风险和处理售后跟进。</p>
        </div>
        <el-button type="primary" plain @click="exportReport">
          <el-icon><Download /></el-icon>
          导出报表
        </el-button>
      </div>
    </template>

    <div class="ledger-toolbar">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索设备编号 / 用户"
        class="toolbar-input"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-select v-model="regionFilter" clearable placeholder="地区" class="toolbar-select">
        <el-option v-for="region in regionOptions" :key="region" :label="region" :value="region" />
      </el-select>
      <el-select v-model="statusFilter" placeholder="在线状态" class="toolbar-select">
        <el-option label="全部状态" value="all" />
        <el-option label="在线" value="online" />
        <el-option label="离线" value="offline" />
      </el-select>
      <el-select v-model="riskFilter" placeholder="风险等级" class="toolbar-select">
        <el-option label="全部风险" value="all" />
        <el-option label="正常" value="normal" />
        <el-option label="关注" value="attention" />
        <el-option label="警告" value="warning" />
        <el-option label="高风险" value="high" />
      </el-select>
      <el-select v-model="boundFilter" placeholder="绑定状态" class="toolbar-select">
        <el-option label="全部绑定" value="all" />
        <el-option label="已绑定" value="bound" />
        <el-option label="未绑定" value="unbound" />
      </el-select>
    </div>

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
      <el-table-column label="风险等级" width="110">
        <template #default="{ row }">
          <el-tag :type="row.riskTagType">{{ row.riskLabel }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="当前状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.posture_status === 'normal' ? 'success' : 'warning'">
            {{ row.posture_status === "normal" ? "正常" : "异常" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="最后上报" min-width="150">
        <template #default="{ row }">{{ row.lastUpdateText }}</template>
      </el-table-column>
      <el-table-column label="未稳定上报" width="130">
        <template #default="{ row }">{{ row.offlineDurationText }}</template>
      </el-table-column>
      <el-table-column label="处理建议" min-width="240">
        <template #default="{ row }">{{ row.operationAdvice }}</template>
      </el-table-column>
      <el-table-column label="压力摘要" min-width="180">
        <template #default="{ row }">
          左 {{ row.left_force_n }}N / 右 {{ row.right_force_n }}N / {{ percent(row.deviation_ratio) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link @click="openDetail(row)">详情</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-drawer v-model="detailVisible" size="420px" title="设备详情" class="device-drawer">
      <template v-if="selectedDevice">
        <div class="drawer-status">
          <div>
            <span>设备编号</span>
            <strong>{{ selectedDevice.device_id }}</strong>
          </div>
          <el-tag :type="selectedDevice.riskTagType">{{ selectedDevice.riskLabel }}</el-tag>
        </div>

        <el-descriptions :column="1" border>
          <el-descriptions-item label="所属地区">{{ selectedDevice.region }}</el-descriptions-item>
          <el-descriptions-item label="绑定用户">{{ selectedDevice.nickname || "未绑定" }}</el-descriptions-item>
          <el-descriptions-item label="在线状态">{{ selectedDevice.is_online ? "在线" : "离线" }}</el-descriptions-item>
          <el-descriptions-item label="最后上报">{{ selectedDevice.lastUpdateText }}</el-descriptions-item>
          <el-descriptions-item label="未稳定上报">{{ selectedDevice.offlineDurationText }}</el-descriptions-item>
          <el-descriptions-item label="状态原因">{{ selectedDevice.riskReason }}</el-descriptions-item>
          <el-descriptions-item label="压力摘要">
            左 {{ selectedDevice.left_force_n }}N / 右 {{ selectedDevice.right_force_n }}N / 偏差 {{ percent(selectedDevice.deviation_ratio) }}
          </el-descriptions-item>
        </el-descriptions>

        <div class="drawer-advice">
          <span>售后建议</span>
          <p>{{ selectedDevice.operationAdvice }}</p>
        </div>
      </template>
    </el-drawer>
  </el-card>
</template>

<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";
import { Download, Search } from "@element-plus/icons-vue";
import { downloadCsv, enrichDevice, percent, riskOrder } from "../utils/operations";

const props = defineProps({
  devices: {
    type: Array,
    default: () => [],
  },
});

const keyword = ref("");
const regionFilter = ref("");
const statusFilter = ref("all");
const riskFilter = ref("all");
const boundFilter = ref("all");
const detailVisible = ref(false);
const selectedDevice = ref(null);

const enrichedDevices = computed(() =>
  props.devices
    .map((item) => enrichDevice(item))
    .sort((a, b) => riskOrder[a.riskLevel] - riskOrder[b.riskLevel] || String(a.device_id).localeCompare(String(b.device_id)))
);

const regionOptions = computed(() => [...new Set(enrichedDevices.value.map((item) => item.region).filter(Boolean))].sort());

const filteredDevices = computed(() => {
  const key = keyword.value.trim().toLowerCase();
  return enrichedDevices.value.filter((item) => {
    const matchesKeyword =
      !key ||
      String(item.device_id || "").toLowerCase().includes(key) ||
      String(item.nickname || "").toLowerCase().includes(key);
    const matchesRegion = !regionFilter.value || item.region === regionFilter.value;
    const matchesStatus =
      statusFilter.value === "all" ||
      (statusFilter.value === "online" && item.is_online) ||
      (statusFilter.value === "offline" && !item.is_online);
    const matchesRisk = riskFilter.value === "all" || item.riskLevel === riskFilter.value;
    const matchesBound = boundFilter.value === "all" || item.boundStatus === boundFilter.value;
    return matchesKeyword && matchesRegion && matchesStatus && matchesRisk && matchesBound;
  });
});

function openDetail(device) {
  selectedDevice.value = device;
  detailVisible.value = true;
}

function exportReport() {
  if (!filteredDevices.value.length) {
    ElMessage.warning("当前筛选条件下没有可导出的设备");
    return;
  }
  const rows = [
    ["设备编号", "地区", "绑定用户", "在线状态", "风险等级", "最后上报", "未稳定上报", "处理建议"],
    ...filteredDevices.value.map((item) => [
      item.device_id,
      item.region,
      item.nickname || "未绑定",
      item.is_online ? "在线" : "离线",
      item.riskLabel,
      item.lastUpdateText,
      item.offlineDurationText,
      item.operationAdvice,
    ]),
  ];
  downloadCsv(`设备运营报表-${new Date().toISOString().slice(0, 10)}.csv`, rows);
  ElMessage.success("报表已导出");
}
</script>
