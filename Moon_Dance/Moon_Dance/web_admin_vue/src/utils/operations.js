const MINUTE_MS = 60 * 1000;
const HOUR_MS = 60 * MINUTE_MS;
const DAY_MS = 24 * HOUR_MS;

export const riskOrder = {
  high: 0,
  warning: 1,
  attention: 2,
  normal: 3,
  unknown: 4,
};

export function formatDateTime(value) {
  if (!value) return "暂无上报";
  return new Date(value).toLocaleString("zh-CN", { hour12: false });
}

export function percent(value, digits = 1) {
  return `${((Number(value) || 0) * 100).toFixed(digits)}%`;
}

export function formatOfflineDuration(value, now = Date.now()) {
  if (!value) return "从未上报";
  const diff = Math.max(now - Number(value), 0);
  if (diff < MINUTE_MS) return "1 分钟内";
  if (diff < HOUR_MS) return `${Math.floor(diff / MINUTE_MS)} 分钟`;
  if (diff < DAY_MS) return `${Math.floor(diff / HOUR_MS)} 小时`;
  return `${Math.floor(diff / DAY_MS)} 天`;
}

export function getDeviceRisk(device, now = Date.now()) {
  const lastUpdate = Number(device?.last_update_ms || 0);
  const offlineMs = lastUpdate ? Math.max(now - lastUpdate, 0) : Number.POSITIVE_INFINITY;
  const isAbnormal = device?.posture_status !== "normal";

  if (!lastUpdate) {
    return {
      level: "high",
      label: "高风险",
      tagType: "danger",
      priority: 0,
      reason: "设备暂无上报记录",
    };
  }

  if (offlineMs >= DAY_MS || (!device?.is_online && isAbnormal)) {
    return {
      level: "high",
      label: "高风险",
      tagType: "danger",
      priority: 0,
      reason: "长时间离线或同时存在异常状态",
    };
  }

  if (offlineMs >= HOUR_MS) {
    return {
      level: "warning",
      label: "警告",
      tagType: "warning",
      priority: 1,
      reason: "设备超过 1 小时未上报",
    };
  }

  if (offlineMs >= 10 * MINUTE_MS || !device?.is_online || isAbnormal) {
    return {
      level: "attention",
      label: "关注",
      tagType: "warning",
      priority: 2,
      reason: isAbnormal ? "设备存在异常使用状态" : "设备上报间隔偏长",
    };
  }

  return {
    level: "normal",
    label: "正常",
    tagType: "success",
    priority: 3,
    reason: "设备近期上报正常",
  };
}

export function adviceForDevice(device) {
  const risk = getDeviceRisk(device);
  if (risk.level === "high") return "优先联系客户，确认设备供电、网络连接和是否继续使用";
  if (risk.level === "warning") return "建议售后在当日内回访，排查网络或绑定状态";
  if (risk.level === "attention") {
    if (device?.posture_status !== "normal") return "建议客服回访，指导用户调整坐垫摆放和使用方式";
    return "持续观察上报状态，必要时提醒客户检查设备";
  }
  return "运行正常，暂无处理";
}

export function enrichDevice(device, now = Date.now()) {
  const risk = getDeviceRisk(device, now);
  return {
    ...device,
    riskLevel: risk.level,
    riskLabel: risk.label,
    riskTagType: risk.tagType,
    followUpPriority: risk.priority,
    riskReason: risk.reason,
    offlineDurationText: formatOfflineDuration(device?.last_update_ms, now),
    lastUpdateText: formatDateTime(device?.last_update_ms),
    operationAdvice: adviceForDevice(device),
    boundStatus: device?.user_id || device?.nickname ? "bound" : "unbound",
  };
}

export function buildRegionStats(devices = [], regions = []) {
  const stats = new Map();

  function ensure(name) {
    const province = String(name || "未知").trim() || "未知";
    if (!stats.has(province)) {
      stats.set(province, { province, total: 0, online: 0, offline: 0, highRisk: 0 });
    }
    return stats.get(province);
  }

  devices.forEach((device) => {
    const row = ensure(device.region);
    const enriched = device.riskLevel ? device : enrichDevice(device);
    row.total += 1;
    if (device.is_online) row.online += 1;
    else row.offline += 1;
    if (enriched.riskLevel === "high") row.highRisk += 1;
  });

  regions.forEach((region) => {
    const row = ensure(region.name);
    const total = Number(region.value || 0);
    if (!devices.length) {
      row.total += total;
      row.offline = Math.max(row.total - row.online, 0);
    } else if (total > row.total) {
      row.total = total;
      row.offline = Math.max(total - row.online, 0);
    }
  });

  return [...stats.values()]
    .map((row) => ({
      ...row,
      activeRate: row.total ? Math.round((row.online / row.total) * 100) : 0,
      offlineRate: row.total ? Math.round((row.offline / row.total) * 100) : 0,
    }))
    .sort((a, b) => b.total - a.total || b.online - a.online);
}

export function adviceForRegion(row) {
  if (!row?.total) return "暂无设备数据，等待设备绑定或上报";
  if (row.total >= 5 && row.offlineRate >= 50) return "设备量较高且离线率偏高，建议优先安排售后排查";
  if (row.total >= 5 && row.activeRate >= 70) return "活跃表现较好，可继续扩大投放和渠道覆盖";
  if (row.total < 5 && row.activeRate >= 70) return "设备量不高但活跃表现好，可作为潜力投放区域";
  if (row.activeRate < 30) return "活跃率偏低，建议暂缓扩量并排查网络、供电和使用问题";
  return "活跃表现稳定，建议结合客户反馈持续观察";
}

export function downloadCsv(filename, rows) {
  const content = rows
    .map((row) =>
      row
        .map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`)
        .join(",")
    )
    .join("\n");
  const blob = new Blob([`\uFEFF${content}`], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
