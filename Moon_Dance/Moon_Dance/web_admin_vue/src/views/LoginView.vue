<template>
  <div class="login-page">
    <el-card class="login-card" shadow="always">
      <template #header>
        <div class="login-title">
          <strong>Moon Dance</strong>
          <span>坐垫运营管理台</span>
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
        <el-button class="login-button" type="primary" :loading="loading" @click="submit">
          登录
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
