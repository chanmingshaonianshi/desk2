<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <span>设备列表</span>
        <el-tag type="info">共 {{ devices.length }} 台</el-tag>
      </div>
    </template>

    <el-table :data="devices" stripe border height="640">
      <el-table-column prop="device_id" label="设备" min-width="130" fixed />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_online ? 'success' : 'danger'">
            {{ row.is_online ? "在线" : "离线" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="region" label="地域" width="100" />
      <el-table-column label="用户" min-width="130">
        <template #default="{ row }">{{ row.nickname || "-" }}</template>
      </el-table-column>
      <el-table-column prop="left_force_n" label="左压力(N)" width="120" />
      <el-table-column prop="right_force_n" label="右压力(N)" width="120" />
      <el-table-column label="偏差" width="100">
        <template #default="{ row }">{{ percent(row.deviation_ratio) }}</template>
      </el-table-column>
      <el-table-column label="坐姿" width="100">
        <template #default="{ row }">
          <el-tag :type="row.posture_status === 'normal' ? 'success' : 'warning'">
            {{ row.posture_status === "normal" ? "标准" : "异常" }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
defineProps({
  devices: {
    type: Array,
    default: () => [],
  },
});

function percent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}
</script>
