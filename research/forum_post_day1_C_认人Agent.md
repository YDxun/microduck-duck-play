Duck Together｜D-具身智能交互：云端仿真里的鸭子“认人+Agent”第一步 —— L1 认人闭环（Day 1 阶段成果）

> 无 RDK X5 / 无实体鸭，全部在 RoboGo 云端 5090 仿真里完成。基于 MicroDuck（Pollen Robotics 开源）与 microduck_rl 官方策略搭建。本帖为 Day 1 阶段性成果 + 后续设计研究，欢迎拍砖。

【赛道】
D 具身智能交互（认人 → Agent 为主线；另含 A 仿真训练链路：4096 env × 6000 iter 走路基线训练 + 追球闭环）

【目标】
一句话：先在纯仿真里让鸭子“认得出人、分得清该跟谁、该绕谁”，为后续“把鸭子做成能理解人意图与情绪的家庭社交 Agent”打地基。
本次验证三件事：
1. 用官方模型搭建可复现的“认人闭环”（召唤 → 只跟主人 → 陌生人靠近绕圈 → 回归主人）；
2. 沉淀可复用工程骨架：感知 → 行为状态机 → 控制（复用网页驾驶舱同一套 MuJoCo/ONNX/观测契约）→ 评测/录像；
3. 输出“认人 → Agent”的后续设计路线，明确不做社区已有的追球/导航/多鸭足球，专注“个体人识别 + 意图 + 信任社交”。

【环境与版本】
- 硬件/平台：RoboGo DuckTogether 群组，dsp-24c192g-5090_32g-x1（1×RTX 5090 / 24 核 / 192GB）；镜像 microduck-cloud-sim-kickfix-20260907
- 软件：系统 Python 3.10（Web/演示）；训练 venv Python 3.12.14；torch 2.9.1+cu128；mjlab；MuJoCo 3.12（EGL 渲染）；ONNX Runtime
- 模型（契约 [1,61]→[1,14]）：官方 alpha_walking / alpha_stand / ball_kick_left / ball_kick_right；自训走路基线（4096×6000 PPO）
- 感知：当前为 MuJoCo 真值（阶段说明）；L1 人形代理为 mocap 运动学体，用衣服颜色/标签区分“主人/陌生人”
- 代码：https://github.com/YDxun/microduck-duck-play
- 模型仓库：https://huggingface.co/XenderYang/microduck-cloud-policies 、https://huggingface.co/XenderYang/microduck-rl-ydx-walk

【复现步骤】（RoboGo kickfix 开发机内，开机即可）
git clone https://github.com/YDxun/microduck-duck-play
cd microduck-duck-play
# 说明：duck_play 会自动复用 /root/microduck_sim 的 LocalSim/PolicyBank/LocalKick（与网页驾驶舱同源）

python3 duck_play/launch/person_demo.py --time 34          # L1 认人：召唤→跟随→陌生人绕圈
python3 duck_play/launch/min_chase.py --time 60 --max-touches 3 --arena --auto-restart   # 多轮连续追球
python3 duck_play/launch/composite_demo.py --time 40       # 组合：找到主人→把球带(踢传)给他
# 录像：export DUCKPLAY_RECORD=/tmp/out.mp4（可调 DUCKPLAY_REC_EVERY/_W/_H）

【成果证据】
1) 认人 L1（召唤→跟随→陌生人绕圈）视频：仓库 research/demo_videos/person_l1.mp4
   指标：召唤到位 7.5s（summon_ok=true）；跟随带内占比 26.1/34s；陌生人贴身(<0.3m)时绕圈 1 次 2.7s 后回归主人
2) 多轮连续追球视频：chase_3rounds.mp4 —— 20s 内自主完成 3 次“逼近→站稳→踢→触球”，每轮自动重置并再次追球
3) 组合叙事视频：composite_deliver.mp4 —— 先找到红衣主人(5.7s) → 绕到球后 → 把球踢送到主人附近（球-主距离 0.92→0.735m，delivered=true）
4) 自训走路基线：reward≈81.5 / 回合≈920 / 无 NaN（能站能走不摔；直行跟踪弱于官方 alpha_walking，作为可续训中间基线）
5) 仓库与模型链接见【环境与版本】

诚实边界：以上为“真值感知 + mocap 人形代理”的无头跑分与录像；仿真无抓取，“带球给主人”采用踢传；“每轮重置”的多轮追球 ≠ 同一颗球连续三脚（后者在后续调优中）。

【开源与授权】
- 本仓代码：Apache-2.0；基于 pollen-robotics/microduck、microduck_rl（Apache-2.0）二次开发
- 官方 ONNX 策略重发布：HF XenderYang/microduck-cloud-policies，注明上游来源与许可
- 3D 模型/素材按上游 CC BY-SA-NC；本贴视频/截图供社区交流

【后续设计研究（认人 → Agent，不重复已有设计）】
社区已有：连续追球/连踢、LightNav 跨房导航、3v3 足球、BPU 认球等 —— 本项目不做这些。
路线分三阶段，重点在“个体人 + 意图 + 信任社交”，而非通用导航/足球：

L1（本次）认人几何闭环：身份标签 + 召唤/跟随/陌生人绕圈 + “信任边界”雏形（只响应主人召唤）。

L2 意图与情绪感知（设计）：
- 多模态意图通道：视觉手势（挥手=召唤、指方向=去那、伸手/蹲下=互动）、语音情绪（ASR+情绪维度）、近距触碰；
- 把“人的状态”建模为隐状态：站/走/坐/久坐/靠近/远离 → 鸭子据此调整行为（久坐→安静陪伴或取物倾向；靠近→欢迎；陌生人→警戒绕行）；
- 记忆与个性化：episodic 记忆 + 轻量身份画像（何时认识、常坐位置、喜欢被摸与否），做到“认主人 + 记得主人习惯”。

L3 Agent 化（新做法）：
- “社交大脑 + RL 小脑”双脑架构：VLM/LLM 只负责把“人的意图/情绪”翻译成高层行为意图（如“主人看起来累→安静陪伴/去门口等待”），动作仍由 50Hz RL 走路/站立策略执行 —— 绕开 VLA 频率与安全短板；
- 信任与隐私分级：按身份+熟悉度给不同响应权限（主人=可执行召唤/任务；访客=礼貌保持边界；陌生人=警戒绕行且不响应指令），做成可配置策略表；
- 决策可解释：输出“看到了谁 → 推断意图 → 选择行为”的文本/图链，方便社区评审与调试。

【需要的支持】
- 有 RDK X5 / 实体鸭的朋友：后续想联调 Sim2Real（认人策略热切换、头部注视、真机相机）；
- 欢迎认人/多模态/情绪理解方向一起共创。

---

## Demo 素材（3 条复现视频 + 预览图）

视频原文件已随代码仓库公开，可点击下方链接直接播放/下载：

**1) L1 认人：召唤 → 只跟主人 → 陌生人靠近绕圈 → 回归主人**
[▶ 播放 person_l1.mp4](https://github.com/YDxun/microduck-duck-play/raw/master/research/demo_videos/person_l1.mp4)
![person_l1 预览](https://raw.githubusercontent.com/YDxun/microduck-duck-play/master/research/demo_videos/person_l1.png)

**2) 多轮连续追球（20s 内 3 次自主触球，每轮自动重置再追）**
[▶ 播放 chase_3rounds.mp4](https://github.com/YDxun/microduck-duck-play/raw/master/research/demo_videos/chase_3rounds.mp4)
![chase_3rounds 预览](https://raw.githubusercontent.com/YDxun/microduck-duck-play/master/research/demo_videos/chase_3rounds.png)

**3) 组合叙事：找到主人 → 绕到球后 → 把球带(踢传)到主人附近（0.92→0.735m）**
[▶ 播放 composite_deliver.mp4](https://github.com/YDxun/microduck-duck-play/raw/master/research/demo_videos/composite_deliver.mp4)
![composite_deliver 预览](https://raw.githubusercontent.com/YDxun/microduck-duck-play/master/research/demo_videos/composite_deliver.png)



