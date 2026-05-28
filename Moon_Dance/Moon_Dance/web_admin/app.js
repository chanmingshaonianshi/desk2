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
  props: { option: { type: Object, required: true } },
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
  props: { apiKey: { type: String, default: "myh" } },
  emits: ["login-success"],
  template: `
    <div class="login-page">
      <el-card class="login-card" shadow="always">
        <template #header><div class="login-title"><strong>Moon Dance</strong><span>坐垫运营管理台</span></div></template>
        <el-form :model="form" label-position="top" @submit.prevent>
          <el-form-item label="管理员账号"><el-input v-model="form.username" autocomplete="username" placeholder="请输入账号" /></el-form-item>
          <el-form-item label="管理员密码"><el-input v-model="form.password" autocomplete="current-password" placeholder="请输入密码" show-password type="password" @keyup.enter="submit" /></el-form-item>
          <el-form-item label="X-API-Key"><el-input v-model="form.apiKey" placeholder="请输入接口 API Key" /></el-form-item>
          <el-button class="login-button" type="primary" :loading="loading" @click="submit">登录</el-button>
        </el-form>
      </el-card>
    </div>
  `,
  setup(props, { emit }) {
    const loading = ref(false);
    const form = reactive({ username: "admin", password: "", apiKey: props.apiKey });
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

const ChinaHeatMap = {
  name: "ChinaHeatMap",
  props: {
    regions: { type: Array, default: () => [] },
  },
  template: `
    <div class="map-panel">
      <div ref="chartRef" class="china-map"></div>
      <div class="map-rank">
        <div v-for="item in ranking" :key="item.name" class="map-rank-item">
          <div><strong>{{ item.name }}</strong><span>{{ item.value }} 台设备</span></div>
          <el-progress :percentage="item.percentage" :show-text="false"></el-progress>
        </div>
        <el-empty v-if="!ranking.length" description="暂无省份使用数据"></el-empty>
      </div>
    </div>
  `,
  setup(props) {
    const chartRef = ref(null);
    let chart = null;
    let resizeObserver = null;
    const provinceMap = {
      北京: "北京", 上海: "上海", 天津: "天津", 重庆: "重庆", 河北: "河北", 山西: "山西",
      辽宁: "辽宁", 吉林: "吉林", 黑龙江: "黑龙江", 江苏: "江苏", 浙江: "浙江", 杭州: "浙江",
      安徽: "安徽", 福建: "福建", 江西: "江西", 山东: "山东", 河南: "河南", 湖北: "湖北",
      武汉: "湖北", 湖南: "湖南", 广东: "广东", 广州: "广东", 深圳: "广东", 海南: "海南",
      四川: "四川", 成都: "四川", 贵州: "贵州", 云南: "云南", 陕西: "陕西", 西安: "陕西",
      甘肃: "甘肃", 青海: "青海", 台湾: "台湾", 内蒙古: "内蒙古", 广西: "广西", 西藏: "西藏",
      宁夏: "宁夏", 新疆: "新疆", 香港: "香港", 澳门: "澳门",
    };
    const mapData = computed(() => {
      const totals = {};
      props.regions.forEach((item) => {
        const province = provinceMap[item.name] || item.name;
        totals[province] = (totals[province] || 0) + Number(item.value || 0);
      });
      return Object.entries(totals).map(([name, value]) => ({ name, value }));
    });
    const maxValue = computed(() => Math.max(...mapData.value.map((item) => item.value), 1));
    const ranking = computed(() => [...mapData.value]
      .sort((a, b) => b.value - a.value)
      .slice(0, 8)
      .map((item) => ({ ...item, percentage: Math.round((item.value / maxValue.value) * 100) })));
    async function ensureChinaMap() {
      if (echarts.getMap("china")) return;
      const sources = [
        "https://cdn.jsdelivr.net/gh/apache/echarts-website@asf-site/examples/data/asset/geo/China.json",
        "https://geo.datav.aliyun.com/areas_v3/bound/100000_full.json",
      ];
      for (const source of sources) {
        try {
          const response = await fetch(source);
          if (!response.ok) continue;
          const geoJson = await response.json();
          echarts.registerMap("china", geoJson);
          return;
        } catch (error) {
          console.warn("China map source failed:", source, error);
        }
      }
      throw new Error("中国地图数据加载失败");
    }
    async function renderChart() {
      if (!chartRef.value) return;
      await ensureChinaMap();
      if (!chart) chart = echarts.init(chartRef.value);
      chart.setOption({
        tooltip: {
          trigger: "item",
          formatter: (params) => `${params.name}<br/>设备数：${params.value || 0} 台`,
        },
        visualMap: {
          min: 0,
          max: maxValue.value,
          left: 12,
          bottom: 16,
          text: ["高", "低"],
          calculable: true,
          inRange: { color: ["#e8f1ff", "#8bb8ff", "#2563eb"] },
        },
        series: [{
          name: "省份设备热度",
          type: "map",
          map: "china",
          roam: false,
          emphasis: { label: { show: true }, itemStyle: { areaColor: "#f59e0b" } },
          itemStyle: { borderColor: "#ffffff", borderWidth: 1 },
          data: mapData.value,
        }],
      }, true);
      chart.resize();
    }
    onMounted(() => {
      nextTick(renderChart);
      resizeObserver = new ResizeObserver(() => chart?.resize());
      resizeObserver.observe(chartRef.value);
    });
    watch(mapData, () => nextTick(renderChart), { deep: true });
    onBeforeUnmount(() => {
      resizeObserver?.disconnect();
      chart?.dispose();
    });
    return { chartRef, ranking };
  },
};

const DashboardView = {
  name: "DashboardView",
  components: { ChinaHeatMap },
  props: {
    summary: { type: Object, default: () => ({}) },
    devices: { type: Array, default: () => [] },
    regions: { type: Array, default: () => [] },
  },
  template: `
    <div class="page-stack">
      <div class="metric-grid seller-metrics">
        <el-card v-for="metric in metrics" :key="metric.label" shadow="never" class="metric-card">
          <span>{{ metric.label }}</span><strong>{{ metric.value }}</strong><small>{{ metric.hint }}</small>
        </el-card>
      </div>
      <div class="overview-grid">
        <el-card shadow="never" class="priority-card">
          <template #header><div class="card-header"><span>今日运营提醒</span><el-tag :type="followUpDevices.length ? 'warning' : 'success'">{{ followUpDevices.length ? followUpDevices.length + " 台待跟进" : "状态良好" }}</el-tag></div></template>
          <div class="notice-list">
            <div class="notice-item"><strong>{{ activeRate }}%</strong><span>当前设备活跃率，优先关注长期离线设备。</span></div>
            <div class="notice-item"><strong>{{ offlineCount }}</strong><span>台设备离线，建议售后确认供电、网络或绑定状态。</span></div>
            <div class="notice-item"><strong>{{ abnormalCount }}</strong><span>台设备出现坐姿异常，可作为用户使用指导或产品体验回访线索。</span></div>
          </div>
        </el-card>
        <el-card shadow="never">
          <template #header><div class="card-header"><span>省份使用热度</span><el-tag type="info">中国地图热力图</el-tag></div></template>
          <ChinaHeatMap :regions="regions"></ChinaHeatMap>
        </el-card>
      </div>
      <el-card shadow="never">
        <template #header><div class="card-header"><span>待跟进设备</span><span class="muted">离线和异常坐姿设备会优先显示</span></div></template>
        <el-table :data="followUpDevices" stripe border>
          <el-table-column prop="device_id" label="设备编号" min-width="130"></el-table-column>
          <el-table-column prop="region" label="地区" width="100"></el-table-column>
          <el-table-column label="绑定用户" min-width="140"><template #default="{ row }">{{ row.nickname || "未绑定" }}</template></el-table-column>
          <el-table-column label="在线状态" width="110"><template #default="{ row }"><el-tag :type="row.is_online ? 'success' : 'danger'">{{ row.is_online ? "在线" : "离线" }}</el-tag></template></el-table-column>
          <el-table-column label="坐姿状态" width="110"><template #default="{ row }"><el-tag :type="row.posture_status === 'normal' ? 'success' : 'warning'">{{ row.posture_status === "normal" ? "正常" : "异常" }}</el-tag></template></el-table-column>
          <el-table-column label="处理建议" min-width="220"><template #default="{ row }">{{ adviceFor(row) }}</template></el-table-column>
        </el-table>
        <el-empty v-if="!followUpDevices.length" description="暂无需要跟进的设备"></el-empty>
      </el-card>
    </div>
  `,
  setup(props) {
    const registeredCount = computed(() => props.summary.registered_devices || props.devices.length || 0);
    const onlineCount = computed(() => props.summary.online_devices || props.devices.filter((item) => item.is_online).length);
    const offlineCount = computed(() => Math.max(registeredCount.value - onlineCount.value, 0));
    const abnormalCount = computed(() => props.summary.bad_posture_devices || props.devices.filter((item) => item.posture_status !== "normal").length);
    const activeRate = computed(() => registeredCount.value ? Math.round((onlineCount.value / registeredCount.value) * 100) : 0);
    const followUpDevices = computed(() => props.devices.filter((item) => !item.is_online || item.posture_status !== "normal").sort((a, b) => Number(a.is_online) - Number(b.is_online)).slice(0, 8));
    const metrics = computed(() => [
      { label: "已售/已注册设备", value: registeredCount.value, hint: "已绑定或已上报的坐垫" },
      { label: "活跃设备", value: `${onlineCount.value} 台`, hint: `当前活跃率 ${activeRate.value}%` },
      { label: "离线待跟进", value: `${offlineCount.value} 台`, hint: "优先检查网络和供电" },
      { label: "使用异常设备", value: `${abnormalCount.value} 台`, hint: "可用于用户回访和指导" },
    ]);
    function adviceFor(device) {
      if (!device.is_online) return "联系客户确认设备供电、网络连接或是否已停止使用";
      if (device.posture_status !== "normal") return "建议客服回访，指导用户正确摆放坐垫和调整坐姿";
      return "持续观察";
    }
    return { metrics, activeRate, offlineCount, abnormalCount, followUpDevices, adviceFor };
  },
};

const DeviceView = {
  name: "DeviceView",
  props: { devices: { type: Array, default: () => [] } },
  template: `
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <div><span>设备售后台账</span><p class="card-subtitle">用于查看已售坐垫的运行状态、绑定用户和跟进建议</p></div>
          <el-segmented v-model="statusFilter" :options="filterOptions"></el-segmented>
        </div>
      </template>
      <el-table :data="filteredDevices" stripe border height="640">
        <el-table-column prop="device_id" label="设备编号" min-width="130" fixed></el-table-column>
        <el-table-column prop="region" label="地区" width="100"></el-table-column>
        <el-table-column label="绑定用户" min-width="140"><template #default="{ row }">{{ row.nickname || "未绑定" }}</template></el-table-column>
        <el-table-column label="在线状态" width="110"><template #default="{ row }"><el-tag :type="row.is_online ? 'success' : 'danger'">{{ row.is_online ? "在线" : "离线" }}</el-tag></template></el-table-column>
        <el-table-column label="坐姿状态" width="110"><template #default="{ row }"><el-tag :type="row.posture_status === 'normal' ? 'success' : 'warning'">{{ row.posture_status === "normal" ? "正常" : "异常" }}</el-tag></template></el-table-column>
        <el-table-column label="最后上报" min-width="150"><template #default="{ row }">{{ formatTime(row.last_update_ms) }}</template></el-table-column>
        <el-table-column label="处理建议" min-width="240"><template #default="{ row }">{{ adviceFor(row) }}</template></el-table-column>
        <el-table-column label="压力/偏差" min-width="180"><template #default="{ row }">左 {{ row.left_force_n }}N / 右 {{ row.right_force_n }}N / {{ percent(row.deviation_ratio) }}</template></el-table-column>
      </el-table>
    </el-card>
  `,
  setup(props) {
    const statusFilter = ref("all");
    const filterOptions = [{ label: "全部", value: "all" }, { label: "在线", value: "online" }, { label: "离线", value: "offline" }, { label: "异常", value: "abnormal" }];
    const filteredDevices = computed(() => {
      if (statusFilter.value === "online") return props.devices.filter((item) => item.is_online);
      if (statusFilter.value === "offline") return props.devices.filter((item) => !item.is_online);
      if (statusFilter.value === "abnormal") return props.devices.filter((item) => item.posture_status !== "normal");
      return props.devices;
    });
    const percent = (value) => `${((Number(value) || 0) * 100).toFixed(1)}%`;
    const formatTime = (value) => value ? new Date(value).toLocaleString("zh-CN", { hour12: false }) : "暂无上报";
    function adviceFor(device) {
      if (!device.is_online) return "优先确认客户设备是否断电、断网或未继续使用";
      if (device.posture_status !== "normal") return "建议售后回访，指导用户调整坐姿或重新校准坐垫";
      return "运行正常，暂无处理";
    }
    return { statusFilter, filterOptions, filteredDevices, percent, formatTime, adviceFor };
  },
};

const UserTable = {
  name: "UserTable",
  props: { users: { type: Array, default: () => [] } },
  template: `
    <el-card shadow="never">
      <template #header><div class="card-header"><div><span>用户统计</span><p class="card-subtitle">用于查看绑定用户、累计积分和提醒设置</p></div><el-tag type="info">共 {{ users.length }} 人</el-tag></div></template>
      <el-table :data="users" stripe border height="460">
        <el-table-column prop="id" label="ID" width="80"></el-table-column>
        <el-table-column label="昵称" min-width="160"><template #default="{ row }">{{ row.nickname || row.openid }}</template></el-table-column>
        <el-table-column label="绑定设备" min-width="140"><template #default="{ row }">{{ row.device_id || "-" }}</template></el-table-column>
        <el-table-column prop="total_score" label="累计分" width="110"></el-table-column>
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
    analytics: { type: Object, default: () => ({ timeline: [], pressure_points: [] }) },
    users: { type: Array, default: () => [] },
  },
  template: `
    <div class="page-stack">
      <el-alert title="这里保留详细健康和压力数据，用于售后复盘、产品体验分析和课程图表展示；首页只保留运营关键指标。" type="info" show-icon :closable="false"></el-alert>
      <div class="panel-grid">
        <el-card shadow="never"><template #header>健康评分趋势</template><BaseChart :option="scoreOption"></BaseChart></el-card>
        <el-card shadow="never"><template #header>入座时长柱状图</template><BaseChart :option="durationOption"></BaseChart></el-card>
      </div>
      <div class="panel-grid">
        <el-card shadow="never"><template #header>不良坐姿次数</template><BaseChart :option="badPostureOption"></BaseChart></el-card>
        <el-card shadow="never"><template #header>左右压力曲线</template><BaseChart :option="pressureOption"></BaseChart></el-card>
      </div>
      <UserTable :users="users"></UserTable>
    </div>
  `,
  setup(props) {
    const timeline = computed(() => props.analytics.timeline || []);
    const pressure = computed(() => props.analytics.pressure_points || []);
    const dates = computed(() => timeline.value.map((item) => item.date.slice(5)));
    const scoreOption = computed(() => ({ tooltip: { trigger: "axis" }, grid: { left: 42, right: 18, top: 24, bottom: 36 }, xAxis: { type: "category", data: dates.value }, yAxis: { type: "value", min: 0, max: 100 }, series: [{ type: "line", smooth: true, name: "健康分", data: timeline.value.map((item) => item.avg_health_score), lineStyle: { width: 3 } }] }));
    const durationOption = computed(() => ({ tooltip: { trigger: "axis" }, grid: { left: 52, right: 16, top: 24, bottom: 36 }, xAxis: { type: "category", data: dates.value }, yAxis: { type: "value" }, series: [{ type: "bar", name: "入座分钟", data: timeline.value.map((item) => item.total_seated_minutes), itemStyle: { color: "#2563eb" } }] }));
    const badPostureOption = computed(() => ({ tooltip: { trigger: "axis" }, grid: { left: 48, right: 16, top: 24, bottom: 36 }, xAxis: { type: "category", data: dates.value }, yAxis: { type: "value" }, series: [{ type: "bar", name: "异常次数", data: timeline.value.map((item) => item.bad_posture_count), itemStyle: { color: "#dc2626" } }] }));
    const pressureOption = computed(() => ({ tooltip: { trigger: "axis" }, legend: { top: 0 }, grid: { left: 48, right: 20, top: 44, bottom: 42 }, xAxis: { type: "category", data: pressure.value.map((item) => item.time) }, yAxis: { type: "value" }, series: [{ type: "line", smooth: true, name: "左压力", data: pressure.value.map((item) => item.left_force_n) }, { type: "line", smooth: true, name: "右压力", data: pressure.value.map((item) => item.right_force_n) }] }));
    return { scoreOption, durationOption, badPostureOption, pressureOption };
  },
};

createApp({
  components: { LoginView, DashboardView, DeviceView, AnalyticsView },
  template: `
    <LoginView v-if="!auth.token" :api-key="auth.apiKey" @login-success="handleLoginSuccess"></LoginView>
    <el-container v-else class="admin-shell">
      <el-aside width="244px" class="admin-aside">
        <div class="brand"><div class="brand-mark">M</div><div><strong>Moon Dance</strong><span>坐垫运营管理台</span></div></div>
        <el-menu :default-active="activeView" class="side-menu" background-color="#111827" text-color="#cbd5e1" active-text-color="#ffffff" @select="activeView = $event">
          <el-menu-item index="dashboard"><span>运营总览</span></el-menu-item>
          <el-menu-item index="devices"><span>设备台账</span></el-menu-item>
          <el-menu-item index="analytics"><span>数据分析</span></el-menu-item>
        </el-menu>
        <el-button class="logout-button" plain type="danger" @click="logout">退出登录</el-button>
      </el-aside>
      <el-container>
        <el-header class="admin-header" height="92px">
          <div><h1>{{ currentTitle }}</h1><p>{{ currentSubtitle }}</p></div>
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
          <DashboardView v-show="activeView === 'dashboard'" :summary="summary" :devices="devices" :regions="regions"></DashboardView>
          <DeviceView v-show="activeView === 'devices'" :devices="devices"></DeviceView>
          <AnalyticsView v-show="activeView === 'analytics'" :analytics="analytics" :users="users"></AnalyticsView>
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
    const pageMeta = {
      dashboard: { title: "运营总览", subtitle: "面向售卖方的设备活跃、离线异常、地区投放和售后跟进看板" },
      devices: { title: "设备台账", subtitle: "快速查看已售设备运行状态、绑定用户和售后处理建议" },
      analytics: { title: "数据分析", subtitle: "保留健康评分、坐姿质量和压力曲线，用于复盘使用质量" },
    };
    const currentTitle = computed(() => pageMeta[activeView.value]?.title || "管理端");
    const currentSubtitle = computed(() => pageMeta[activeView.value]?.subtitle || "");
    async function loadAll() {
      if (!auth.token) return;
      loading.value = true;
      try {
        const api = createAdminApi(auth);
        const [summaryData, devicesData, regionsData, analyticsData, usersData] = await Promise.all([api.summary(), api.devices(), api.regions(), api.analytics(days.value), api.users()]);
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
    return { auth, activeView, days, loading, summary, devices, regions, analytics, users, currentTitle, currentSubtitle, loadAll, handleLoginSuccess, logout };
  },
}).use(ElementPlus).mount("#app");
