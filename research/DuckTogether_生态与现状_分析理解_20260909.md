# Duck Together｜MicroDuck 生态与现状 —— 分析理解盘点（2026-09-09）

> 阶段：仅分析理解，不做设计开发。事实标注 [实测 2026-09-09] 的均为当天核实；其余来自本地调研记录与官方文档。

## 0. 一句话结论
- 我们走「无 RDK X5、纯云端仿真」路线，对应 Duck Together 的 **A-仿真与强化学习** + **C-具身智能交互** 赛道（活动 35663）。
- 可用的三层仿真/训练能力已经齐备且契约统一（观测 [1,61] → 动作 [1,14]）：
  1. **RoboGo 云端镜像（开箱）**：网页驾驶舱遛鸭/踢球/Chase 接口，适合演示与闭环联调；
  2. **microduck_rl（训练栈）**：mjlab(MuJoCo Warp)+PPO，5090 单卡即可 4096 env 训练；
  3. **官方 microduck 主仓 duck-sim（真栈仿真）**：跑与真机完全相同的 Rust daemon（robotd/tofd/mediad）对接 MuJoCo 躯体，无板时最贴近真机软件边界。
- 今天资源实测：包月 DuckTogether 8×5090 仅剩 **2 空闲**（9/8 曾为 7，群组其他人占用增加）；开发机 microduck-kickfix-ydx 正在运行约 2h45m、GPU 空闲、服务健康。

## 1. 社区资料理解
### 1.1 招募帖 topic/35663（活动规则）
- 时间：即日起 ~ 2026-12-31（GMT+8）；不要求有整机，阶段成果/项目线索均可参加；评审需报名 + 在 Duck Together 专区（c/duck-together/49）发含可验证材料的项目帖。
- 五方向：仿真与强化学习 / 仿真×实体连接 / RDK 端侧推理 / 具身智能交互（追球、认人、语音、Agent、多模态）/ 硬件与整机。
- 奖项：全场最佳 1 名=机器鸭套件；仿真与强化学习优秀 ×10=RoboGo 2000 积分；RDK 端侧 ×5；硬件 ×3=RDK X5。
- 发帖建议标题：[Duck Together] 项目名｜共建方向；正文需写清问题/环境版本/已完成/证据/遗留问题/下一步。
### 1.2 云仿真+板端原帖 topic/35645
- 架构：浏览器 ← 云 5090（MuJoCo 200Hz 仿真+渲染）← RDK X5（50Hz 运控 + BPU DOSOD 视觉）。
- 关键工程结论：控制环必须放板端/本地（公网 ~50ms 会把鸭子摔了）；观测向量与训练时完全一致是最高危点；BPU NV12 要喂 numpy；颜色对比度、25Hz 指令心跳重发等坑。
- 对我们：无板时这些「板端能力」由云端程序/真值观测替代，作为仿真内交互验证。
### 1.3 云端镜像教程 topic/35661
- 群组共享镜像 `microduck-cloud-sim-kickfix-20260907`：开机托管服务、云端左右踢球 Q/E、动作状态反馈；无 X5 时坐/滚/捡/推倒按钮禁用（非缺模型而是无板端实现）。
- 验收命令：`cd /root/microduck_sim && python3 service.py status`、`curl -fsS http://localhost:8080/healthz`（ok:true）；异常 `./restart.sh`。
- 工作目录约定：Web 用系统 Python，训练用 `microduck_rl/.venv`，不混 pip。
### 1.4 标杆/参考帖
- topic/35683（Datawhale）：4096 env × 6000 iter 走路训练（1h27m）→ checkpoint/ONNX 发 HF；后续 V2 板端 ONNX server、V3 三视角追同一球连踢 3 次+摔倒恢复、V4 视觉语言导航/3v3 网页仿真。
- topic/35692：与本项目几乎同场景（无 X5、RoboGo 1×5090、4096 env、WANDB_MODE=offline；实测 ~78k steps/s 首轮）。
- topic/35664：MicroDuck RL 课程目录（14 集）。

## 2. 开源项目理解（两仓均克隆至 _ref，HEAD=2026-09-08 最新）
### 2.1 pollen-robotics/microduck（鸭脑运行时，Rust，约 7.8k star）
- daemons：robotd（50Hz 控制环/ONNX 策略热切换/安全/里程计）、mediad（相机/WebRTC/控制台 :8080）、configd、btd、padd（手柄）、tofd（ToF 8×8）、updaterd（签名更新+健康回滚）。
- 契约：策略 ONNX [1,61]→[1,14]；观测=48 本体感受 + 命令(twist3/head_pose4/body_pose6)，策略可按 manifest 在 walk/recover/trick 槽位热切换。
- **仿真缝 RobotIo**（read/write/set_gain/set_torque/slow_sensors）：`robotd --sim` 用 RemoteIo 对接 MuJoCo；`--fake` 无物理只测逻辑。
- **scripts/duck-sim**（对我们最重要）：`up`（无容器单/多鸭）与 `boot N`（systemd-nspawn 每鸭一容器 + duck-ether 假无线电多鸭合唱）；场景默认公寓/apartment；相机按需（渲染 12ms/帧 vs 物理 0.3ms/鸭）；实时性 ≥1×（低于 45Hz 健康门限会不健康）。
- 硬件边界：Dynamixel 总线、BLE、相机 ISP、NPU、编码器不在仿真内 → 这些只能在真机验。
### 2.2 pollen-robotics/microduck_rl（训练栈，develop，约 2k star）
- 技术栈：mjlab（MuJoCo Warp）+ rsl_rl PPO；50Hz；任务 `uv run list-envs`（Velocity/VelStand/StandUp/SitStand/GroundPick/BallKick/Roulade/Rollers/Spin 等 45 个注册任务）。
- sim2real 要点：BAM M6 XL330 执行器模型（电压级+负载摩擦+回差）、ENABLE_* 域随机化开关、观测归一化必须由 `scripts/export.py` 烘焙进 ONNX（禁止手转 checkpoint）。
- 发布：`uv run publish` → HF（manifest schema2，episodic/perpetual gait/held pose）；无 GPU 可 `--hf-jobs`。
- 许可：代码 Apache-2.0；3D 模型 CC BY-SA-NC（发布时需标注）。
### 2.3 官方两仓与 RoboGo 云端镜像的关系（理解要点）
- 云端镜像本质是 microduck_rl 的 MuJoCo 躯体 + 官方 ONNX 策略 + 自研 sim_server/Web 驾驶舱（不是完整 Rust daemon 栈）；它给出「仿真↔网页/WebSocket」的交互层，并保留训练仓库。
- 官方 duck-sim 则跑完整真栈（需 cargo build + libonnxruntime，来自 microduck_rl venv），适合验证「真机软件语义」类问题；在 x86 Linux 上可行。

## 3. RoboGo 平台与资源 [实测 2026-09-09 ~03:00 CST]
- 账号：yangdongxun（页面显示名 Xander_yang；手机 18406659281；邮箱 18406659281@163.com）；地瓜干 50；存储 0/50GB；Token 0/500（每 5h 重置，有 API Key 管理）。
- 群组 DuckTogether：24 人；2 个展示资产（两个云镜像）；创建者 guosheng_xu。
- 「我的资源」算力：包月 DuckTogether = NVIDIA-GeForce-RTX-5090 × 8；节点 1；GPU 总数 8；**可用 GPU 2**；到期 --；状态正常。
- 按量市场（备选，贵）：5090 单卡 160.94 元/h（当前标注「紧张」）；4090 单卡 123.8 元/h；多卡需排队。正常只用包月。
- 开发机：microduck-kickfix-ydx **运行中**；规格 dsp-24c192g-5090_32g-x1（1 卡/24 核/192GB/32GB）；镜像 microduck-cloud-sim-kickfix-20260907；开机时长 2h42m（最近开机 2026/09/09 00:12:05 CST）；计费正常；创建 2026/09/08 15:30:04。
- 截图留档：research/screenshots/robogo_resources_20260909.png、robogo_devmachine_20260909.png。

## 4. 开发机环境核实 [实测 2026-09-09]
- 连接（本机须带私钥）：`ssh -i C:\Users\杨东勋\.ssh\robogo_yangdongxun -o IdentitiesOnly=yes -p 2222 ssh-authkey-67c6406a1d75ac4035e399fb@120.48.90.140`（root；容器 9/9 00:12 CST 起；外层是百度云 BCC 9/7 起）。
- 服务：`service.py status` → healthy:true；`/healthz` → {"ok":true,"board":false,"vision":false}；sim_server 运行中（PID 411）。
- GPU：NVIDIA RTX 5090 32GB，当前 0% / 140MiB（空闲）；磁盘 97G 可用。
- 训练环境：/root/microduck_sim/microduck_rl/.venv（Python 3.12、torch 2.9.1+cu128、CUDA 可用 True）。
- 已有成果物：microduck_rl/logs/rsl_rl/velocity/2026-09-08_08-04-08_ydx-walk-4096x6000（我们训的走路基线）；artifacts/ 含官方 alpha_stand/alpha_walking/ball_kick_left|right 与 pose-gesture-v2、ydx-walk-4096x6000（model_5999.pt/final.onnx/params）。
- 机器内无 robogo CLI/凭据（平台操作走网页）；SSH 仅进开发机。

## 5. 对后续的含义（仅分析）
- 三条链路契约一致（61/14），成果可互相迁移：训练→导出 ONNX→云端驾驶舱/duck_play 闭环已验证可行（本地 duck_play 即复用 LocalSim/PolicyBank/LocalKick 同一契约）。
- 认人/Agent 交互（C 赛道）在仿真内的可行基础：第一视角相机（云端镜像已带）→ 检测/ReID → 高层行为状态机；RL 侧可训行走/踢球等基础策略作为动作原语。
- 资源纪律：单卡 5090 足够 4096×6000 训练（约 1.5–2h）；训练完及时关机。当前池只剩 2 空闲，正式训练前先确认资源。

## 6. 提醒事项（非开发）
- 开发机现处于运行中且 GPU 空闲（约 2h45m），若分析后暂不训练，建议到 RoboGo「开发机→关机」省额度（保留镜像/数据，可再开机）。
- 发布材料注意许可标注：microduck 代码 Apache-2.0、3D 图纸 CC BY-SA-NC、官方策略/镜像按群组共享约束；论坛标题示例「Duck Together｜A-仿真：…」。
