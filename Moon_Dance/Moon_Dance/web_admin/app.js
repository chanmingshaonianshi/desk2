const { createApp, computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } = Vue;
const { ElMessage } = ElementPlus;

const TOKEN_KEY = "adminToken";
const API_KEY_KEY = "adminApiKey";

function getStoredAuth() {
  return {
    token: localStorage.getItem(TOKEN_KEY) || "",
    apiKey: localStorage.getItem(API_KEY_KEY) || "myh",
  };
}

function saveAuth({ token, apiKey }) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  if (apiKey) localStorage.setItem(API_KEY_KEY, apiKey);
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
}

async function parseResponse(response) {
  const payload = await response.json().catch(() => ({}));
  if (!response.ok || !payload.ok) {
    throw new Error(payload.message || `请求失败：${response.status}`);
  }
  return payload.data;
}

async function loginAdmin({ username, password, apiKey }) {
  const response = await fetch("/api/admin/login", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({ username, password }),
  });
  return parseResponse(response);
}

function createAdminApi({ token, apiKey }) {
  const headers = {
    "Content-Type": "application/json",
    "X-API-Key": apiKey,
    Authorization: `Bearer ${token}`,
  };
  const get = async (url) => parseResponse(await fetch(url, { headers }));
  return {
    summary: () => get("/api/admin/summary"),
    devices: () => get("/api/admin/devices"),
    regions: () => get("/api/admin/regions"),
    analytics: (days) => get(`/api/admin/analytics?days=${days}`),
    users: () => get("/api/admin/users"),
  };
}

const BaseChart = {
  name: "BaseChart",
  props: {
    option: { type: Object, required: true },
  },
  template: `<div ref="chartRef" class="chart"></div>`,
  setup(props) {
    const chartRef = ref(null);
    let chart = null;
    let resizeObserver = null;

    function renderChart() {
      if (!chartRef.value) return;
      if (!chart) chart = echarts.init(chartRef.value);
      chart.setOption(props.option, true);
      chart.resize();
    }

    onMounted(() => {
      nextTick(renderChart);
      resizeObserver = new ResizeObserver(() => chart?.resize());
      resizeObserver.observe(chartRef.value);
    });

    watch(() => props.option, () => nextTick(renderChart), { deep: true });

    onBeforeUnmount(() => {
      resizeObserver?.disconnect();
      chart?.dispose();
    });

    return { chartRef };
  },
};

const LoginView = {
  name: "LoginView",
  props: {
    apiKey: { type: String, default: "myh" },
  },
  emits: ["login-success"],
  template: `
    <div class="login-page">
      <el-card class="login-card" shadow="always">
        <template #header>
          <div class="login-title">
            <strong>Moon Dance</strong>
            <span>智能坐垫管理端</span>
          </div>
        </template>
        <el-form :model="form" label-position="top" @submit.prevent>
          <el-form-item label="管理员账号">
            <el-input v-model="form.username" autocomplete="username" placeholder="请输入账号" />
          </el-form-item>
          <el-form-item label="管理员密码">
            <el-input
              v-model="form.password"
              autocomplete="current-password"
              placeholder="请输入密码"
              show-password
              type="password"
              @keyup.enter="submit"
            />
          </el-form-item>
          <el-form-item label="X-API-Key">
            <el-input v-model="form.apiKey" placeholder="请输入接口 API Key" />
          </el-form-item>
          <el-button class="login-button" type="primary" :loading="loading" @click="submit">登录</el-button>
        </el-form>
      </el-card>
    </div>
  `,
  setup(props, { emit }) {
    const loading = ref(false);
    const form = reactive({
      username: "admin",
      password: "",
      apiKey: props.apiKey,
    });

    async function submit() {
      if (!form.username || !form.password || !form.apiKey) {
        ElMessage.warning("请填写账号、密码和 X-API-Key");
        return;
      }
      loading.value = true;
      try {
        const data = await loginAdmin(form);
        emit("login-success", { token: data.token, apiKey: form.apiKey });
      } catch (error) {
        ElMessage.error(error.message || "登录失败");
      } finally {
        loading.value = false;
      }
    }

    return { form, loading, submit };
  },
};

const DashboardView = {
  name: "DashboardView",
  components: { BaseChart },
  props: {
    summary: { type: Object, default: () => ({}) },
    regions: { type: Array, default: () => [] },
    analytics: { type: Object, default: () => ({ timeline: [], pressure_points: [] }) },
  },
  template: `
    <div class="page-stack">
      <div class="metric-grid">
        <el-card v-for="metric in metrics" :key="metric.label" shadow="never" class="metric-card">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </el-card>
      </div>
      <div class="panel-grid">
        <el-card shadow="never"><template #header>健康评分趋势</template><BaseChart :option="scoreOption" /></el-card>
        <el-card shadow="never"><template #header>地域分布</template><BaseChart :option="regionOption" /></el-card>
      </div>
      <el-card shadow="never"><template #header>左右压力曲线</template><BaseChart :option="pressureOption" /></el-card>
    </div>
  `,
  setup(props) {
    const metrics = computed(() => [
      { label: "注册设备", value: props.summary.registered_devices || 0, hint: "已绑定或已上报" },
      { label: "在线设备", value: props.summary.online_devices || 0, hint: "60 秒内有数据" },
      { label: "异常坐姿", value: props.summary.bad_posture_devices || 0, hint: "偏差大于 10%" },
      { label: "平均健康分", value: props.summary.avg_health_score || 0, hint: "按日汇总统计" },
    ]);
    const timeline = computed(() => props.analytics.timeline || []);
    const pressure = computed(() => props.analytics.pressure_points || []);
    const dates = computed(() => timeline.value.map((item) => item.date.slice(5)));
    const scoreOption = computed(() => ({
      tooltip: { trigger: "axis" },
      grid: { left: 42, right: 18, top: 24, bottom: 36 },
      xAxis: { type: "category", data: dates.value },
      yAxis: { type: "value", min: 0, max: 100 },
      series: [{ type: "line", smooth: true, name: "健康分", data: timeline.value.map((item) => item.avg_health_score), lineStyle: { width: 3 } }],
    }));
    const regionOption = computed(() => ({
      tooltip: { trigger: "item" },
      series: [{ type: "pie", radius: ["45%", "72%"], data: props.regions, label: { formatter: "{b}: {c}" } }],
    }));
    const pressureOption = computed(() => ({
      tooltip: { trigger: "axis" },
      legend: { top: 0 },
      grid: { left: 48, right: 20, top: 44, bottom: 42 },
      xAxis: { type: "category", data: pressure.value.map((item) => item.time) },
      yAxis: { type: "value" },
      series: [
        { type: "line", smooth: true, name: "左压力", data: pressure.value.map((item) => item.left_force_n) },
        { type: "line", smooth: true, name: "右压力", data: pressure.value.map((item) => item.right_force_n) },
      ],
    }));
    return { metrics, scoreOption, regionOption, pressureOption };
  },
};

const DeviceView = {
  name: "DeviceView",
  props: {
    devices: { type: Array, default: () => [] },
  },
  template: `
    <el-card shadow="never">
      <template #header><div class="card-header"><span>设备列表</span><el-tag type="info">共 {{ devices.length }} 台</el-tag></div></template>
      <el-table :data="devices" stripe border height="640">
        <el-table-column prop="device_id" label="设备" min-width="130" fixed />
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><el-tag :type="row.is_online ? 'success' : 'danger'">{{ row.is_online ? "在线" : "离线" }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="region" label="地域" width="100" />
        <el-table-column label="用户" min-width="130"><template #default="{ row }">{{ row.nickname || "-" }}</template></el-table-column>
        <el-table-column prop="left_force_n" label="左压力(N)" width="120" />
        <el-table-column prop="right_force_n" label="右压力(N)" width="120" />
        <el-table-column label="偏差" width="100"><template #default="{ row }">{{ percent(row.deviation_ratio) }}</template></el-table-column>
        <el-table-column label="坐姿" width="100">
          <template #default="{ row }"><el-tag :type="row.posture_status === 'normal' ? 'success' : 'warning'">{{ row.posture_status === "normal" ? "标准" : "异常" }}</el-tag></template>
        </el-table-column>
      </el-table>
    </el-card>
  `,
  setup() {
    return {
      percent: (value) => `${((Number(value) || 0) * 100).toFixed(1)}%`,
    };
  },
};

const UserTable = {
  name: "UserTable",
  props: {
    users: { type: Array, default: () => [] },
  },
  template: `
    <el-card shadow="never">
      <template #header><div class="card-header"><span>用户统计</span><el-tag type="info">共 {{ users.length }} 人</el-tag></div></template>
      <el-table :data="users" stripe border height="460">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column label="昵称" min-width="160"><template #default="{ row }">{{ row.nickname || row.openid }}</template></el-table-column>
        <el-table-column label="绑定设备" min-width="140"><template #default="{ row }">{{ row.device_id || "-" }}</template></el-table-column>
        <el-table-column prop="total_score" label="累计分" width="110" />
        <el-table-column label="久坐阈值" width="130"><template #default="{ row }">{{ row.sedentary_threshold_min }} 分钟</template></el-table-column>
        <el-table-column label="提醒" width="100"><template #default="{ row }"><el-tag :type="row.reminder_enabled ? 'success' : 'info'">{{ row.reminder_enabled ? "开启" : "关闭" }}</el-tag></template></el-table-column>
        <el-table-column label="榜单可见" width="110"><template #default="{ row }"><el-tag :type="row.visible_in_leaderboard ? 'success' : 'info'">{{ row.visible_in_leaderboard ? "是" : "否" }}</el-tag></template></el-table-column>
      </el-table>
    </el-card>
  `,
};

const AnalyticsView = {
  name: "AnalyticsView",
  components: { BaseChart, UserTable },
  props: {
    analytics: { type: Object, default: () => ({ timeline: [] }) },
    users: { type: Array, default: () => [] },
  },
  template: `
    <div class="page-stack">
      <div class="panel-grid">
        <el-card shadow="never"><template #header>入座时长柱状图</template><BaseChart :option="durationOption" /></el-card>
        <el-card shadow="never"><template #header>不良坐姿次数</template><BaseChart :option="badPostureOption" /></el-card>
      </div>
      <UserTable :users="users" />
    </div>
  `,
  setup(props) {
    const timeline = computed(() => props.analytics.timeline || []);
    const dates = computed(() => timeline.value.map((item) => item.date.slice(5)));
    const durationOption = computed(() => ({
      tooltip: { trigger: "axis" },
      grid: { left: 52, right: 16, top: 24, bottom: 36 },
      xAxis: { type: "category", data: dates.value },
      yAxis: { type: "value" },
      series: [{ type: "bar", name: "入座分钟", data: timeline.value.map((item) => item.total_seated_minutes), itemStyle: { color: "#2563eb" } }],
    }));
    const badPostureOption = computed(() => ({
      tooltip: { trigger: "axis" },
      grid: { left: 48, right: 16, top: 24, bottom: 36 },
      xAxis: { type: "category", data: dates.value },
      yAxis: { type: "value" },
      series: [{ type: "bar", name: "异常次数", data: timeline.value.map((item) => item.bad_posture_count), itemStyle: { color: "#dc2626" } }],
    }));
    return { durationOption, badPostureOption };
  },
};

createApp({
  components: { LoginView, DashboardView, DeviceView, AnalyticsView },
  template: `
    <LoginView v-if="!auth.token" :api-key="auth.apiKey" @login-success="handleLoginSuccess" />
    <el-container v-else class="admin-shell">
      <el-aside width="236px" class="admin-aside">
        <div class="brand"><div class="brand-mark">M</div><div><strong>Moon Dance</strong><span>智能坐垫管理端</span></div></div>
        <el-menu :default-active="activeView" class="side-menu" background-color="#111827" text-color="#cbd5e1" active-text-color="#ffffff" @select="activeView = $event">
          <el-menu-item index="dashboard"><span>数据总览</span></el-menu-item>
          <el-menu-item index="devices"><span>设备管理</span></el-menu-item>
          <el-menu-item index="analytics"><span>统计分析</span></el-menu-item>
        </el-menu>
        <el-button class="logout-button" plain type="danger" @click="logout">退出登录</el-button>
      </el-aside>
      <el-container>
        <el-header class="admin-header" height="84px">
          <div><h1>{{ currentTitle }}</h1><p>设备运行、地域分布、坐姿压力和用户健康数据聚合分析</p></div>
          <div class="header-actions">
            <el-select v-model="days" class="days-select" @change="loadAll">
              <el-option label="近 7 天" :value="7"></el-option>
              <el-option label="近 30 天" :value="30"></el-option>
              <el-option label="近 90 天" :value="90"></el-option>
            </el-select>
            <el-button type="primary" :loading="loading" @click="loadAll">刷新</el-button>
          </div>
        </el-header>
        <el-main v-loading="loading" class="admin-main">
          <DashboardView v-show="activeView === 'dashboard'" :summary="summary" :regions="regions" :analytics="analytics" />
          <DeviceView v-show="activeView === 'devices'" :devices="devices" />
          <AnalyticsView v-show="activeView === 'analytics'" :analytics="analytics" :users="users" />
        </el-main>
      </el-container>
    </el-container>
  `,
  setup() {
    const storedAuth = getStoredAuth();
    const auth = reactive({ token: storedAuth.token, apiKey: storedAuth.apiKey });
    const activeView = ref("dashboard");
    const days = ref(30);
    const loading = ref(false);
    const summary = ref({});
    const devices = ref([]);
    const regions = ref([]);
    const analytics = ref({ timeline: [], pressure_points: [] });
    const users = ref([]);
    const titleMap = { dashboard: "数据总览", devices: "设备管理", analytics: "统计分析" };
    const currentTitle = computed(() => titleMap[activeView.value] || "管理端");

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
        if (String(error.message || "").includes("Token")) logout();
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
      if (auth.token) loadAll();
    });

    return {
      auth,
      activeView,
      days,
      loading,
      summary,
      devices,
      regions,
      analytics,
      users,
      currentTitle,
      loadAll,
      handleLoginSuccess,
      logout,
    };
  },
}).use(ElementPlus).mount("#app");
