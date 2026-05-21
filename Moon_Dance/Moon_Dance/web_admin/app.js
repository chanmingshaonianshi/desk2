const { createApp, nextTick } = Vue;

createApp({
  data() {
    return {
      nav: [
        { key: "overview", label: "数据总览", icon: "⌁" },
        { key: "devices", label: "设备管理", icon: "▦" },
        { key: "analytics", label: "统计分析", icon: "▥" },
      ],
      view: "overview",
      days: "30",
      apiKey: localStorage.getItem("adminApiKey") || "myh",
      token: localStorage.getItem("adminToken") || "",
      loginForm: { username: "admin", password: "" },
      error: "",
      loading: false,
      summary: {},
      devices: [],
      regions: [],
      analytics: { timeline: [], pressure_points: [] },
      users: [],
      charts: {},
    };
  },
  computed: {
    currentTitle() {
      return this.nav.find(item => item.key === this.view)?.label || "管理端";
    },
    metrics() {
      return [
        { label: "注册设备", value: this.summary.registered_devices || 0, hint: "已绑定或已上报" },
        { label: "在线设备", value: this.summary.online_devices || 0, hint: "60 秒内有数据" },
        { label: "异常坐姿", value: this.summary.bad_posture_devices || 0, hint: "偏差大于 10%" },
        { label: "平均健康分", value: this.summary.avg_health_score || 0, hint: "按日汇总统计" },
      ];
    },
  },
  watch: {
    view() {
      nextTick(() => this.renderCharts());
    },
  },
  mounted() {
    if (this.token) this.loadAll();
  },
  methods: {
    headers() {
      return {
        "Content-Type": "application/json",
        "X-API-Key": this.apiKey,
        "Authorization": `Bearer ${this.token}`,
      };
    },
    async request(url, options = {}) {
      const res = await fetch(url, {
        ...options,
        headers: { ...this.headers(), ...(options.headers || {}) },
      });
      const payload = await res.json();
      if (!payload.ok) throw new Error(payload.message || "请求失败");
      return payload.data;
    },
    async login() {
      this.error = "";
      try {
        const res = await fetch("/api/admin/login", {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": this.apiKey },
          body: JSON.stringify(this.loginForm),
        });
        const payload = await res.json();
        if (!payload.ok) throw new Error(payload.message || "登录失败");
        this.token = payload.data.token;
        localStorage.setItem("adminToken", this.token);
        localStorage.setItem("adminApiKey", this.apiKey);
        await this.loadAll();
      } catch (err) {
        this.error = err.message;
      }
    },
    logout() {
      this.token = "";
      localStorage.removeItem("adminToken");
    },
    async loadAll() {
      if (!this.token) return;
      this.loading = true;
      this.error = "";
      try {
        const [summary, devices, regions, analytics, users] = await Promise.all([
          this.request("/api/admin/summary"),
          this.request("/api/admin/devices"),
          this.request("/api/admin/regions"),
          this.request(`/api/admin/analytics?days=${this.days}`),
          this.request("/api/admin/users"),
        ]);
        this.summary = summary;
        this.devices = devices.devices || [];
        this.regions = regions.regions || [];
        this.analytics = analytics;
        this.users = users.users || [];
        await nextTick();
        this.renderCharts();
      } catch (err) {
        this.error = err.message;
        if (String(err.message).includes("Token")) this.logout();
      } finally {
        this.loading = false;
      }
    },
    chart(refName) {
      const el = this.$refs[refName];
      if (!el) return null;
      if (!this.charts[refName]) this.charts[refName] = echarts.init(el);
      return this.charts[refName];
    },
    renderCharts() {
      const timeline = this.analytics.timeline || [];
      const dates = timeline.map(item => item.date.slice(5));
      this.chart("scoreChart")?.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 42, right: 18, top: 24, bottom: 36 },
        xAxis: { type: "category", data: dates },
        yAxis: { type: "value", min: 0, max: 100 },
        series: [{ type: "line", smooth: true, name: "健康分", data: timeline.map(item => item.avg_health_score), lineStyle: { width: 3 } }],
      });
      this.chart("regionChart")?.setOption({
        tooltip: { trigger: "item" },
        series: [{ type: "pie", radius: ["45%", "72%"], data: this.regions, label: { formatter: "{b}: {c}" } }],
      });
      const pressure = this.analytics.pressure_points || [];
      this.chart("pressureChart")?.setOption({
        tooltip: { trigger: "axis" },
        legend: { top: 0 },
        grid: { left: 48, right: 20, top: 44, bottom: 42 },
        xAxis: { type: "category", data: pressure.map(item => item.time) },
        yAxis: { type: "value" },
        series: [
          { type: "line", smooth: true, name: "左压力", data: pressure.map(item => item.left_force_n) },
          { type: "line", smooth: true, name: "右压力", data: pressure.map(item => item.right_force_n) },
        ],
      });
      this.chart("durationChart")?.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 52, right: 16, top: 24, bottom: 36 },
        xAxis: { type: "category", data: dates },
        yAxis: { type: "value" },
        series: [{ type: "bar", name: "入座分钟", data: timeline.map(item => item.total_seated_minutes), itemStyle: { color: "#2563eb" } }],
      });
      this.chart("badChart")?.setOption({
        tooltip: { trigger: "axis" },
        grid: { left: 48, right: 16, top: 24, bottom: 36 },
        xAxis: { type: "category", data: dates },
        yAxis: { type: "value" },
        series: [{ type: "bar", name: "异常次数", data: timeline.map(item => item.bad_posture_count), itemStyle: { color: "#dc2626" } }],
      });
      Object.values(this.charts).forEach(chart => chart.resize());
    },
    percent(value) {
      return `${((Number(value) || 0) * 100).toFixed(1)}%`;
    },
  },
}).mount("#app");
