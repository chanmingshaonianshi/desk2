<template>
  <div class="login-page">
    <section class="login-intro">
      <div class="login-kicker">Moon Dance Admin</div>
      <h1>明月律动设备运营台</h1>
      <p>面向坐垫售卖方、运营人员和售后人员，集中查看设备运行、地区使用和待跟进设备。</p>
      <div class="login-capabilities">
        <span>设备运营</span>
        <span>地区分析</span>
        <span>售后跟进</span>
      </div>
    </section>

    <el-card class="login-card" shadow="never">
      <div class="login-title">
        <strong>管理员登录</strong>
        <span>登录后可查看设备台账和运营数据</span>
      </div>

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
        <el-form-item label="接口访问密钥">
          <el-input v-model="form.apiKey" placeholder="请输入 X-API-Key" />
        </el-form-item>
        <el-button class="login-button" type="primary" :loading="loading" @click="submit">
          进入管理端
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { loginAdmin } from "../api/admin";

const props = defineProps({
  apiKey: {
    type: String,
    default: "myh",
  },
});
const emit = defineEmits(["login-success"]);
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
    emit("login-success", {
      token: data.token,
      apiKey: form.apiKey,
    });
  } catch (error) {
    ElMessage.error(error.message || "登录失败");
  } finally {
    loading.value = false;
  }
}
</script>
