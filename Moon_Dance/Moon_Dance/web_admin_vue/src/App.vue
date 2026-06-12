<template>
  <LoginView
    v-if="!auth.token"
    :api-key="auth.apiKey"
    @login-success="handleLoginSuccess"
  />

  <el-container v-else class="admin-shell">
    <el-aside width="244px" class="admin-aside">
      <div class="brand">
        <img class="brand-mark" :src="logoUrl" alt="Moon Dance Logo" />
        <div>
          <strong>明月律动</strong>
          <span>设备运营台</span>
        </div>
      </div>

      <el-menu
        :default-active="activeView"
        class="side-menu"
        background-color="#1c2d3f"
        text-color="#c3ccda"
        active-text-color="#ffffff"
        @select="activeView = $event"
      >
        <el-menu-item index="dashboard">
          <el-icon><DataBoard /></el-icon>
          <span>运营总览</span>
        </el-menu-item>
        <el-menu-item index="devices">
          <el-icon><Tickets /></el-icon>
          <span>设备台账</span>
        </el-menu-item>
        <el-menu-item index="analytics">
          <el-icon><TrendCharts /></el-icon>
          <span>数据分析</span>
        </el-menu-item>
      </el-menu>

      <el-button class="logout-button" plain type="danger" @click="logout">退出登录</el-button>
    </el-aside>

    <el-container>
      <el-header class="admin-header" height="82px">
        <div>
          <h1>{{ currentTitle }}</h1>
          <p>{{ currentSubtitle }}</p>
        </div>
        <div class="header-actions">
          <el-select v-model="days" class="days-select" @change="loadAll">
            <el-option label="近 7 天" :value="7" />
            <el-option label="近 30 天" :value="30" />
            <el-option label="近 90 天" :value="90" />
          </el-select>
          <el-button type="primary" :loading="loading" @click="loadAll">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </el-header>

      <el-main v-loading="loading" class="admin-main">
        <DashboardView
          v-show="activeView === 'dashboard'"
          :summary="summary"
          :devices="devices"
          :regions="regions"
        />
        <DeviceView
          v-show="activeView === 'devices'"
          :devices="devices"
        />
        <AnalyticsView
          v-show="activeView === 'analytics'"
          :analytics="analytics"
          :users="users"
          :devices="devices"
          :regions="regions"
        />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { DataBoard, Refresh, Tickets, TrendCharts } from "@element-plus/icons-vue";
import LoginView from "./views/LoginView.vue";
import DashboardView from "./views/DashboardView.vue";
import DeviceView from "./views/DeviceView.vue";
import AnalyticsView from "./views/AnalyticsView.vue";
import { clearAuth, createAdminApi, getStoredAuth, saveAuth } from "./api/admin";

const storedAuth = getStoredAuth();
const auth = reactive({
  token: storedAuth.token,
  apiKey: storedAuth.apiKey,
});
const activeView = ref("dashboard");
const days = ref(30);
const loading = ref(false);
const summary = ref({});
const devices = ref([]);
const regions = ref([]);
const analytics = ref({ timeline: [], pressure_points: [] });
const users = ref([]);
const logoUrl = `${import.meta.env.BASE_URL}moon-dance-logo.jpg`;

const pageMeta = {
  dashboard: {
    title: "今日运营",
    subtitle: "查看待跟进设备、离线风险和地区使用热度，支撑售后与运营决策",
  },
  devices: {
    title: "设备台账",
    subtitle: "按设备状态、地区和风险等级检索已售坐垫，定位需要处理的设备",
  },
  analytics: {
    title: "运营复盘",
    subtitle: "按时间和省份复盘设备使用情况，判断投放效果与售后重点",
  },
};

const currentTitle = computed(() => pageMeta[activeView.value]?.title || "管理端");
const currentSubtitle = computed(() => pageMeta[activeView.value]?.subtitle || "");

async function loadAll() {
  if (!auth.token) return;
  loading.value = true;
  try {
    const api = createAdminApi(auth);
    const [summaryData, devicesData, regionsData, analyticsData, usersData] = await Promise.all([
      api.summary(),
      api.devices(),
      api.regions(),
      api.analytics(days.value),
      api.users(),
    ]);
    summary.value = summaryData;
    devices.value = devicesData.devices || [];
    regions.value = regionsData.regions || [];
    analytics.value = analyticsData;
    users.value = usersData.users || [];
  } catch (error) {
    ElMessage.error(error.message || "数据加载失败");
    if (String(error.message || "").includes("Token")) {
      logout();
    }
  } finally {
    loading.value = false;
  }
}

function handleLoginSuccess({ token, apiKey }) {
  auth.token = token;
  auth.apiKey = apiKey;
  saveAuth({ token, apiKey });
  ElMessage.success("登录成功");
  loadAll();
}

function logout() {
  auth.token = "";
  clearAuth();
}

onMounted(() => {
  if (auth.token) {
    loadAll();
  }
});
</script>
