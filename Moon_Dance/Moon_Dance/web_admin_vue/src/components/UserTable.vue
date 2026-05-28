<template>
  <el-card shadow="never">
    <template #header>
      <div class="card-header">
        <div>
          <span>用户统计</span>
          <p class="card-subtitle">用于查看绑定用户、累计积分和提醒设置</p>
        </div>
        <el-tag type="info">共 {{ users.length }} 人</el-tag>
      </div>
    </template>

    <el-table :data="users" stripe border height="460">
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column label="昵称" min-width="160">
        <template #default="{ row }">{{ row.nickname || row.openid }}</template>
      </el-table-column>
      <el-table-column label="绑定设备" min-width="140">
        <template #default="{ row }">{{ row.device_id || "-" }}</template>
      </el-table-column>
      <el-table-column prop="total_score" label="累计分" width="110" />
      <el-table-column label="久坐阈值" width="130">
        <template #default="{ row }">{{ row.sedentary_threshold_min }} 分钟</template>
      </el-table-column>
      <el-table-column label="提醒" width="100">
        <template #default="{ row }">
          <el-tag :type="row.reminder_enabled ? 'success' : 'info'">
            {{ row.reminder_enabled ? "开启" : "关闭" }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="榜单可见" width="110">
        <template #default="{ row }">
          <el-tag :type="row.visible_in_leaderboard ? 'success' : 'info'">
            {{ row.visible_in_leaderboard ? "是" : "否" }}
          </el-tag>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>

<script setup>
defineProps({
  users: {
    type: Array,
    default: () => [],
  },
});
</script>
