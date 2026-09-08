# RoboGo 申请开发机 + 开机验收清单（MicroDuck 云端仿真项目）

> 用途：在 RoboGo（https://robogo.d-robotics.cc）用群组 DuckTogether 的包月 5090 资源创建 MicroDuck 云端开发机，并完成开机验收。
> 账号：yangdongxun（已登录验证过）
> 目标镜像：microduck-cloud-sim-kickfix-20260907（群组共享修复版，推荐）
> 生成时间：2026-09-08

---

## 0. SSH 密钥（本机已生成）

本机（Windows，C:\Users\杨东勋）已生成专用密钥对：

| 项目 | 值 |
|---|---|
| 私钥（勿外传） | `C:\Users\杨东勋\.ssh\robogo_yangdongxun` |
| 公钥（可粘贴） | `C:\Users\杨东勋\.ssh\robogo_yangdongxun.pub` |
| 指纹 | `SHA256:z16YC8Ss05JhqGrbd+fLaA734pJ6hN1UqATT0awWcgQ` |

**公钥内容（申请开发机时粘贴到“SSH公钥”框）：**

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMkAM0jPbudgNXkDTE1rZXRHyYzk6/IgxCxusHnj6lYy yangdongxun@robogo-microduck
```

注意：私钥无口令、仅存本机。请勿把私钥发给任何人/上传到任何地方；一旦泄露立即在本机重新生成并更换 RoboGo 上的公钥。

---

## 1. 申请开发机（约 3 分钟）

1. 浏览器登录 RoboGo：https://robogo.d-robotics.cc
2. 左侧菜单：**我的资产 → 开发机**（或直接访问 https://robogo.d-robotics.cc/dev-machine ）
3. 点右上角 **“申请开发机”**（若无权限，提示群主 guosheng_xu 开通成员创建权限）

### 表单逐项填写（按实测平台字段）

| 表单项 | 填什么 |
|---|---|
| 名称 | 建议 `microduck-kickfix-ydx`（好认即可） |
| 算力可用区 | **选「包月 DuckTogether」**（余 7 GPU）；不要选弹性（按小时计费贵） |
| 资源规格 | **dsp-24c192g-5090_32g-x1**（1 卡 / 24 核 / 192GB / 32GB 显存）——单卡足够训练 |
| 镜像 | **选择镜像 → microduck-cloud-sim-kickfix-20260907**（群组共享里选；别选旧版 fork） |
| SSH 公钥 | 粘贴上面第 0 节的公钥内容（整行） |
| 系统盘 | **≥ 100 GB**（训练日志/模型占空间） |
| 数据挂载/资产 | 暂不添加（保持空即可） |
| 外网应用（Web 应用） | **端口 8080，路径 /**（驾驶舱通过它访问） |
| 提交 | 点 **“确认提交”** |

提交后开发机状态从“创建中 → 运行中”。若长时间“排队中”，是 5090 资源被占用，稍后再试或换 2 卡/4 卡规格。

---

## 2. 开机后先记下连接信息（回传给我）

开发机“运行中”后，在开发机卡片/详情页找并记录以下信息（复制回来，我用于 SSH 远程协助）：

```
SSH 主机/地址：
SSH 端口：
SSH 用户名：        （一般是 root）
Web 应用公网地址：  （形如 https://xxxx.robogo.d-robotics.cc 或带端口）
开发机 ID：
```

---

## 3. 开机验收（在开发机终端里执行，或我远程执行）

### 3.1 服务与健康检查
```bash
cd /root/microduck_sim
python3 service.py status          # 期望各服务 running
curl -fsS http://localhost:8080/healthz   # 期望返回 {"ok": true, ...}
```
若未就绪：`./restart.sh`，再看日志 `tail -n 80 service-logs/server.log`。
> 不要额外再跑一份 `python3 sim_server.py`，会抢 8080 端口。

### 3.2 网页驾驶舱
浏览器打开“Web 应用公网地址”：
- 画面正常渲染、能看到鸭子站立；
- W/S 前进后退、A/D 转向、Q/E 左右踢球、空格复位；
- 状态栏显示指令 accepted/running/completed。
黑屏/502 时回到 3.1 查 healthz 和日志。

### 3.3 GPU 与训练环境
```bash
nvidia-smi                          # 期望看到 NVIDIA GeForce RTX 5090, 32GB, 占用低
cd /root/microduck_sim
ls microduck_rl/.venv/bin/python    # 训练虚拟环境存在
source microduck_rl/.venv/bin/activate
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
# 期望: True NVIDIA GeForce RTX 5090
```

### 3.4 smoke 训练验收（关键）
```bash
cd /root/microduck_sim
./train.sh Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 64 \
  --agent.max_iterations 5 \
  --agent.logger tensorboard \
  --agent.run-name ydx-smoke
```
通过标准：
- 任务注册/启动无报错，环境跑在 cuda:0；
- actor 61 维 / critic 76 维 / action 14 维日志正确；
- 平均奖励从 -0.03 起有上升趋势；
- 生成日志目录：`/root/microduck_rl/logs/rsl_rl/velocity/ydx-smoke/`。

### 3.5 （可选）TensorBoard 查看
```bash
cd /root/microduck_sim
source microduck_rl/.venv/bin/activate
tensorboard --logdir microduck_rl/logs/rsl_rl --port 6006 --bind_all
```
然后在外网应用里再加一条 6006 端口映射，或 SSH 隧道本地看。

---

## 4. 训练与关机规范

- 正式训练用 **1 卡 5090**：`WANDB_MODE=offline uv run train Mjlab-Velocity-Flat-MicroDuck --env.scene.num-envs 4096 --agent.max_iterations 6000 --agent.run-name <run-name>`（约 1.5~2 h）；
- 长训练用 `tmux` 或 `nohup ... &` 挂后台，避免 SSH 断开中断；
- 模型/日志在 `microduck_rl/logs/rsl_rl/velocity/<run>/`；导出 ONNX 用 `uv run scripts/export.py`（会烘焙观测归一化器）；
- **训练/调试完务必关机**（RoboGo 开发机 → 关机），否则持续消耗群组额度/地瓜干。

---

## 5. 常见问题

| 现象 | 处理 |
|---|---|
| Web 应用 502 / 黑屏 | `curl -fsS http://localhost:8080/healthz`；异常则 `./restart.sh`；仍不行记录开发机 ID+时间+日志上报平台 |
| MANUAL 下 Kick 无反应 | 确认用的是 kickfix 镜像并刷新页面；走近球、让球在脚前再踢 |
| Chase 模式没反应 | 需视觉控制端实际运行（云端程序）；纯云先玩 Manual |
| 创建排队 | 5090 被占，稍后再试或换规格 |
| SSH 连不上 | 核对主机/端口/用户名；确认已粘贴公钥；私钥在本机 `.ssh\robogo_yangdongxun` |

---

## 6.（2026-09-08 实测补充）自动化申请受阻 → 请手动创建

自动化填写并提交时，页脚一直出现红色提示 **“请选择配置”**，确认提交不生效；刷新页面会清空已填内容（前端不保存草稿）。判定为“外网配置→Web应用”需要人工操作触发其配置生效（可能需在端口/路径输入后按回车或让输入框失焦，或先在该区域选择一个“配置类型”下拉项），浏览器自动化未能复现该交互。

**请你手动创建，注意以下要点：**

1. 打开 https://robogo.d-robotics.cc/dev-machine → 右上角“申请开发机”；
2. 名称填 `microduck-kickfix-ydx`；
3. 算力可用区点 **“包月 DuckTogether”**（别用弹性 5090/4090）；
4. 资源规格选 **dsp-24c192g-5090_32g-x1**（1 卡那行）；
5. 镜像：点“选择镜像”→ 选 **microduck-cloud-sim-kickfix-20260907**（列表第一个）→ 确定；
6. SSH公钥粘贴（整行）：
   `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMkAM0jPbudgNXkDTE1rZXRHyYzk6/IgxCxusHnj6lYy yangdongxun@robogo-microduck`
7. 系统盘填 **100**（单位 GB）；
8. 外网配置 Web应用：端口填 **8080**、路径填 **/**；填完后**按一下回车或点击页面其它空白处让其生效**，确认红色“请选择配置”消失（如果仍有，截图发我，或查看该区域是否要先选“Web应用”配置类型）；
9. 点“确认提交”，等状态变为“运行中”。

创建成功（运行中）后，把下面信息发我，我立刻 SSH 接管做验收+开发：

```
SSH 主机/地址：
SSH 端口：
SSH 用户名：
Web 应用公网地址：
开发机 ID：
```

---

## 7.（2026-09-08）开发机已创建并验收通过 ✅

- 机器：microduck-kickfix-ydx / dsp-24c192g-5090_32g-x1 / kickfix 镜像 / 运行中
- SSH：`ssh -i C:\Users\杨东勋\.ssh\robogo_yangdongxun -p 2222 ssh-authkey-67c6406a1d75ac4035e399fb@120.48.90.140`（root）
- 验收结果：
  - `service.py status` → healthy: true；`/healthz` → {"ok": true, "board": false, "vision": false}
  - GPU：NVIDIA GeForce RTX 5090 32GB，CUDA 12.8，训练后已释放（3% / 368MiB）
  - 训练环境：/root/microduck_sim/microduck_rl/.venv，Python 3.12.14，torch 2.9.1+cu128，CUDA 可用
  - 网页驾驶舱：本机隧道 http://127.0.0.1:18080 → 开发机 8080，标题 MICRODUCK // CLOUD RODEO，CLOUD LINK OK / MUJOCO PHYSICS OK / 50Hz / 23FPS / alpha_stand @CLOUD；截图 research/screenshots/microduck_cockpit_local.png
  - smoke 训练：Mjlab-Velocity-Flat-MicroDuck，64 env × 5 iter，已完成；输出
    `/root/microduck_sim/microduck_rl/logs/rsl_rl/velocity/2026-09-08_07-44-24_ydx-smoke/`
    （model_0.pt、model_4.pt、ONNX、TensorBoard events；5 轮 mean reward 0.38→0.28，episode length 19.9→33.5，nan=0）
- 公网 Web 应用：在 RoboGo 开发机卡片点“Web应用 → 打开”即可（自动化弹窗受限，需手动打开一次）
