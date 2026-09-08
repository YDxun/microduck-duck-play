# MicroDuck / RDK 鸭子机器人 — 云端仿真 + RL 调研笔记

> 调研时间：2026-09-08　|　研究目标：基于 RDK 提供的鸭子仿真与开源代码，在**无 RDK X5 开发板**条件下，用 **RoboGo 云端 5090** 做仿真/强化学习/具身智能交互（追球、认人、Agent）。

## 1. 生态全景
- **MicroDuck（Pollen Robotics 开源双足鸭）**：~800 g、~25 cm、15 舵机（14 关节 + 头部）、RK3566 主控。
  - 主仓库：https://github.com/pollen-robotics/microduck （Rust 运行时 robotd/updaterd/...，跑 50Hz ONNX 策略）
  - RL 仓库：https://github.com/pollen-robotics/microduck_rl （mjlab + MuJoCo Warp + PPO，50Hz 训练，导出 ONNX）
- **地瓜 D-Robotics Duck Together 共建计划**（活动到 2026-12-31）：五个方向可参加——
  仿真与强化学习 / 仿真×实体连接 / RDK 端侧推理 / 具身智能交互（追球、认人、语音、Agent、多模态）/ 硬件与整机
  - 招募帖：https://forum.d-robotics.cc/t/topic/35663
  - 奖项：全场最佳=机器鸭开发套件；仿真与强化学习优秀=RoboGo 2000 积分 ×10；RDK 端侧=充电宝×5；硬件=RDK X5×3
- **云仿真+板端运控方案原帖**（qiaolongli 乔龙）：https://forum.d-robotics.cc/t/topic/35645/1
  - 架构：浏览器 ←→ 云端 5090（MuJoCo 200Hz 仿真+渲染）←→ RDK X5（50Hz 运控 + BPU DOSOD 视觉认球）
  - 关键结论：控制环必须放板端/本地闭环，公网 50ms 延迟会摔鸭子；云只做状态回放渲染。
- **云端镜像教程帖**：https://forum.d-robotics.cc/t/topic/35661
  - RoboGo DuckTogether 群组共享镜像（2 个）：
    1. `microduck-cloud-sim-kickfix-20260907`（修复版：开机服务托管、云端左右踢球 Q/E、动作状态反馈；推荐）
    2. `microduck-cloud-sim_fork`（乔龙原版）
  - 工作目录：`/root/microduck_sim/`；Web 用系统 Python，训练用 `microduck_rl/.venv`，不要混 pip。
- **MicroDuck RL 系列课程（14 集）** 目录帖：https://forum.d-robotics.cc/t/topic/35664 （每集帖子 35665~）
- **社区高完成度项目（标杆/参照）**：
  - https://forum.d-robotics.cc/t/topic/35683 A-仿真 4096 环境×6000 迭代走路训练（耗时 1:27:41），checkpoint/ONNX 发布在
    - HF: `Datawhale/Microduck-RL-4096x6000`（含 model_5999.pt + 最终 ONNX [1,61]->[1,14]）
    - HF: `Datawhale/Microduck-BallKick-4096x6000`
    - V2：RDK X5 当策略大脑（ONNX server）跑单鸭/3×3 方阵闭环
    - V3：三视角闭环连续追同一颗球踢 3 次 + 物理摔倒恢复（视觉 bbox 用 MuJoCo 真值投影，非训练检测器）
    - V4：LightNav-0 视觉语言导航（跨房间走到沙发）+ MPC；3v3 多鸭足球网页仿真
  - https://forum.d-robotics.cc/t/topic/35692 （与本用户场景几乎一致：无 RDK X5，RoboGo 1×RTX5090，`microduck-cloud-sim_fork`，4096 env 训练；WANDB_MODE=offline；实测 5090 首轮约 78k steps/s）
- **中文教程仓库**：datawhalechina/every-embodied，目录 `05-具身场景的深度和强化学习/05-OpenDuckMini与Microduck双足强化学习/`

## 2. RoboGo 平台实测（已用 yangdongxun 登录）
- 群组 DuckTogether：20 成员，创建者 guosheng_xu，2 个资产（上面两个镜像）
- 资源：**包月 DuckTogether：NVIDIA-GeForce-RTX-5090 × 8（1 节点 / GPU 总数 8 / 可用 7）**，到期时间 --（无到期）
- 可用规格 4 种：
  - dsp-24c192g-5090_32g-x1：1 卡 / 24 核 / 192GB / 32GB 显存（**推荐日常训练**）
  - dsp-48c384g-5090_32g-x2：2 卡 / 48 核 / 384GB
  - dsp-96c768g-5090_32g-x4：4 卡 / 96 核 / 768GB（需排队）
  - dsp-192c1536g-5090_32g-x8：8 卡 / 192 核 / 1536GB（需排队）
- 另有“弹性”按量资源：弹性 5090（余 3 GPU）、弹性 4090（余 1 GPU）——按小时计费（5090 单卡 160.94 元/h），**正常只用群组包月资源，别用弹性**
- 开发机创建表单字段：名称 / 算力可用区（选 包月 DuckTogether）/ 资源规格 / 镜像（选 kickfix）/ SSH 公钥（必填，需先准备）/ 系统盘 ≥100GB / 外网应用端口 8080、路径 / / 确认提交
- 注意：**用完关机**，否则持续消耗资源/额度（地瓜干）。

## 3. 关键命令速查（在 RoboGo 开发机内）
```bash
# 服务健康检查（kickfix 镜像）
cd /root/microduck_sim && python3 service.py status
curl -fsS http://localhost:8080/healthz          # 期望 "ok": true
./restart.sh && tail -n 80 service-logs/server.log

# 训练（microduck_rl 自带 venv；smoke test 先跑小规模）
cd /root/microduck_sim
./train.sh Mjlab-Velocity-Flat-MicroDuck --env.scene.num-envs 64 \
  --agent.max_iterations 5 --agent.logger tensorboard --agent.run-name my-smoke
# 正式训练 4096 env（约 1~2 小时出可用步态；参考 4096x6000=1h27m）
WANDB_MODE=offline uv run train Mjlab-Velocity-Flat-MicroDuck \
  --env.scene.num-envs 4096 --agent.max_iterations 6000 \
  --agent.run-name my-4096x6000
# 日志/模型：microduck_rl/logs/rsl_rl/velocity/<run>/

# ONNX 导出（必须用 scripts/export.py，烘焙观测归一化器）
uv run scripts/export.py Mjlab-Velocity-Flat-MicroDuck --wandb-run-path <...>
# CPU MuJoCo 彩排
uv run scripts/infer_policy.py --walking output.onnx
```
- 观测契约：[1,61] -> [1,14]（actor 61 维：48 proprioception + commands twist3/head4/body6）；critic 76 维
- 14 关节布局：0-4 左腿(hip_yaw/roll/pitch, knee, ankle)，5-8 脖子/头(neck_pitch, head_pitch, head_yaw, head_roll)，9-13 右腿
- 任务注册：`uv run list-envs`（45 个任务：walk/stand/sitstand/groundpick/ballkick/roulade/rollers/spin/backlash 变体等）
- 电机：BAM M6 XL330 电压级模型 + 域随机化；无滤波器加在动作上
- 环境变量：CUDA 12.8 / torch 2.9.1 / mjlab 1.3.0 / rsl-rl-lib 5.0.1 / mujoco 3.10 / mujoco-warp 3.8.1 / Python 3.12（uv 管理）

## 4. 本地电脑配置（薄客户端即可，不需要好显卡）
- Windows 11 + PowerShell + OpenSSH（系统自带）或 MobaXterm/Termius
- VS Code + Remote-SSH 插件（编辑开发机内代码最顺）
- 浏览器（访问 RoboGo Web 应用驾驶舱、TensorBoard 转发）
- Git + GitHub 账号（发布 Duck Together 项目帖/成果）
- （可选）本地装 Python 3.12 + uv：仅在本地 CPU 上跑 infer_policy 回放/看代码
- （可选）WSL2：本地更贴近 Linux 环境
- SSH 密钥：`ssh-keygen -t ed25519`，公钥粘贴进 RoboGo 开发机申请
- 无需本地 NVIDIA GPU；训练/仿真全部在云端 5090

## 5. 推荐工作路线（无板，纯仿真+交互）
- L0 领镜像→建开发机→网页遛鸭→smoke train：先把基线跑通（镜像已含 45 任务训练环境）
- L1 复现/改进：4096×6000 走路训练、BallKick、命令编舞，导出 ONNX，网页验证
- L2 视觉追球闭环（仿真内）：MuJoCo 第一视角 RGB → 检测（先真值 bbox，再换 YOLO/轻量检测）→ 状态机(search/align/approach/kick)→ walking+BallKick 策略切换；目标：追**运动/滚动的球**，社区已做“追同一颗球连踢 3 次”（V3）
- L3 认人（仿真内）：第一视角人形/人脸检测（预训练模型或真值）→ 跟随/环绕/头部注视；可加 ReID/身份
- L4 Agent/具身智能：LLM/VLM 高层指令 → 拆成速度/转向/踢球命令（参考 V4 LightNav-0 室内导航）；或语音交互（ASR/TTS）+ 行为
- L5 进阶（可选）：多鸭 3v3 足球分工、RL 端到端视觉策略、Sim2Real 文档/接口
- 参与 Duck Together：在“Duck Together｜机器鸭共建”版块发项目帖，附可复现材料（代码/镜像/日志/视频）
