# MicroDuck 开源设计与已有玩法调研（2026-09-08）

> 调研方式：Codex + in-app 浏览器；范围：Pollen Robotics 上游 + Hugging Face/GitHub 社区 + D-Robotics Duck Together（RDK）。
> 用途：为后续“目前没有的有趣尝试”提供事实底座。社区条目多数为 sim-only（真机 2026-12 前尚未发货）。

## 0. 三句话结论

1. **硬件基本“半开源”**：上游只公开 MJCF/STL 网格与整套软件/RL 代码（Apache-2.0），BOM/CAD/PCB 不公开；但社区已有逆向与 DIY 复刻（含中文项目）。
2. **“已有玩法”已从‘会走路’快速膨胀到‘会杂技 + 会被 LLM 指挥 + 会追球抓球’**：仅 2026 年 8 月底~9 月初，HF 上就出现 20+ 个社区技能策略（后空翻、月亮步、芭蕾、篮球、高跷、电动滑步……），且有 quackd（LLM 目标规划）、TinyVLA、microduck-tracking（抓特定球）等“Agent/视觉闭环”作品。
3. **最大空白恰好是官方 roadmap M9“自主大脑”**：一个“放养 10 分钟也值得看”的能量/心情驱动的行为栈，官方只写了 ideas 文档没有实现；社区最接近的是 nottyduck 桌面陪伴人格与 WebXR 的简单 wander，**在 mjlab/云仿真里用真实 ONNX 技能做自主行为栈还没有人做**——这正是纯仿真团队能做的、目前没有的方向。

## 1. 上游开源设计（Pollen Robotics + Hugging Face）

### 1.1 产品与硬件
- 尺寸/重量：约 25 cm、~800 g 双足鸭；15 个舵机（14 关节 + 嘴/头部执行）；头部 8×8 ToF（VL53L8CX，15 Hz）、IMX219 摄像头、麦克风+喇叭、双 IMU、可抓取嘴。
- 主控：RK3566（Radxa Zero 3W 级别）；50 Hz 控制环 + 15 舵机跑 ONNX 神经策略。
- 硬件开源边界：BOM/CAD/PCB 未开源；公开 MJCF 物理模型 + STL 网格（部分 license 限制非商用）。社区逆向/复刻：OpenMicroDuck、microduck-replica、microduck-hardware-replica、microduck-diy（中文）、ChinaMicroDuck（中文，四条量产路线对比）。
- 售价 $399 预售（2026-08-27 开订），预计 2026-12 前发货 → 现在全球几乎没有真机；仿真/策略/网页体验是唯一可验证面。

### 1.2 主仓库 pollen-robotics/microduck（7.7k★，Rust，Apache-2.0）
- 守护进程架构（Unix socket + 统一 JSON-RPC 契约）：
  - robotd：50 Hz 控制环、Dynamixel 总线、ONNX 策略、安全层（关节限位/摔倒 limp/意图 deadman）、运动学、接触里程计、gaze IK、语音/Theremin/Chorale 都挂在同一 tick。
  - updaterd：签名 OTA、健康门禁、原子切换、回滚。
  - configd（wifi/身份）、btd（BLE）、padd（手柄）、mediad（摄像头 WebRTC 推流）、tofd（ToF）。
  - robotctl（操作 CLI）、duckctl（笔记本经 BLE 控制）。
- 能力（出厂即会，即“官方玩法”）：走路/手柄驾驶、滚轮滑行（roller 模式）、roulade 后滚翻、地面叼物 ground_pick、坐下/站起 sitstand、踢球（左/右）、polite-bow、flamingo 等均可通过策略热换；语音（每只鸭子按 SoC 序列号生成独有音色，可 quack/问候/告别/被摸头时 coo）、ToF Theremin（手在嘴前=乐器）、Chorale 多鸭无指挥合唱（BLE 信标共享节拍 ±20 ms，自动分部）。技能可通过 HF Hub 策略通道下发（roadmap M8：policy list/load/reset/check/update/search，manifest 校验 obs/action 维度与 model_api）。

### 1.3 RL 仓库 pollen-robotics/microduck_rl（1.9k★，mjlab + MuJoCo Warp + PPO）
- 观测契约：actor [1,61]（48 proprioception + 命令 twist3/head4/body6），critic [1,76]，输出 [1,14]（14 关节：左右腿 0–4/9–13，头颈 5–8）。50 Hz，导出 ONNX 时烘焙归一化器。
- Sim2Real 要素：BAM M6 电压级电机模型（对应 XL330）、±1° 齿隙 backlash 建模、域随机化（电压/压降/命令延迟/摩擦）、关节限位+摔倒处理。
- 官方任务注册表（uv run list-envs；Flat/Rough/Backlash 变体后更多）：
  - 运动：Velocity（走+头姿命令）、VelStand（走+摔倒恢复一体）、StandUp（趴/仰/坐起）、SitStand、GroundPick、Roulade
  - 踢球：BallKick（70 mm/15 g 球，actor 本身球盲，纯命令踢）
  - 滚轮系：Velocity-Rollers、Swizzle、RollerCrouch、RollerSlope、RollerStandUp、Spin
  - 官方已发布 9 个策略到 HF：pollen-robotics/microduck-policies
- 官方 roadmap 关键点：M8 策略通道基本完成（社区策略可被真机一键安装/撤销）；M9 自主大脑=最大未实现空白；明确“不做”：A/B 镜像、遥测、舰队面板等。

### 1.4 官方“自主大脑”ideas 文档（docs/ideas/autonomous_behavior.md）——空白点金矿
- 16 状态行为机：Chill / LookAround / Wander / TurnInPlace / Zoomies / Startle / Stretch / Ruffle / Preen / Sneeze / Dance / GroundPick / Nap / BallPlay / Petted / Held，基于能量/心情模型 + 新奇度网格探索记忆 + ToF 避障 + 对比度惊吓 + 声音反应 + 球戏 + 打盹周期 + 被摸反应。
- 社交玩法设想（依赖 BLE 多鸭在场）：认鸭与问候（记忆好友/陌生）、孤单/满足情绪、接近兴奋、Marco Polo、跟着头鸭走、掌声社会反馈、传话游戏、投票选行为。
- 节拍同步动作：群鸭同步点头/摇摆/康加舞/同步舞；音乐：对唱应答、轮唱、分工（低音+节奏啄+旋律）。
- 鸭体检测（NPU YOLO 级）：视觉=方向、ToF=距离、BLE=身份 三者融合。
- 官方建议：先做“认鸭与问候”（charm-per-line 最高、无需同步）；chorale 未来应是自发事件而非命令。

## 2. 已有玩法全景（社区，2026-08/09 密集涌现）

> 依据：joeynyc/awesome-microduck（社区维护大全）+ HF 模型/仓库检索 + D-Robotics 论坛。标注 ★ 的与“追球/认人/Agent”最相关。

### 2.1 技能/杂技类（多为 HF 上已发布 ONNX，sim-only）
| 玩法 | 出处/Repo |
|---|---|
| Flamingo 单腿循环、Polite-bow | RemiFabre/microduck-flamingo-cycle、fffiloni/microduck-polite-bow |
| Running、Swing、Stilts、Electric-slide、Happy-hop、Moonwalk 倒退 | HannesVonEssen（running/swing/stilts）、Histochemichael、joanfox、moonwalk |
| Basketball、Beak-throw | HannesVonEssen/microduck-basketball、q2p/microduck-beak-throw |
| Backflip、Max-height-jump、Step-up(head-brake)、Jump playground | microduck-backflip、Nupr-Haokun/step-up、Jump playground |
| 芭蕾（腿=策略+头颈=开环编舞，两分钟 Swan Lake） | MicroDuck Swan Lake（中文） |
| 侧步舞 sidekick-dance、命令编舞（Datawhale 4096×6000） | microduck-sidekick-dance、Datawhale/Microduck-RL-4096x6000 |

### 2.2 交互/任务玩法
- ★ Microduck Ball Challenge：可打分追球基准（固定物理 hash），另有 stairs 挑战——追球评测有“标准答案”了。
- ★ microduck-tracking：认“刚被抛出的那颗球”——头戴相机帧 + RF-DETR/SORT + 官方策略，穿过多个相同球抓指定球、每抛一次重锁（MuJoCo sim，7/11 成功）。
- ★ Ball Follow / drag-the-ball（mjlab 训练，目标跟随+拖球 demo）。
- Microduck Circus：三只鸭跳一根共享长绳（agent 循环 act-fail-practice-adapt）——多鸭协同已有雏形。
- microduck-courier：公寓场景 pick-carry-place。
- Datawhale V4：LightNav-0 视觉语言导航（跨房间找沙发）+ MPC；3v3 多鸭足球网页仿真（角色脚本）。
- Microduck School（HF Space）：用英文给鸭子“上课”，LLM 驱动失败-重试-进步闭环。

### 2.3 Agent / LLM / VLA（与“Agent 玩法”最相关）
- ★ quackd（rokbenko）：LLM 目标规划守护进程。“find the ball and kick it”这类目标 → 逐个调用鸭子自带技能、看相机再决策；支持 Claude/OpenAI/Gemini/Grok/Ollama；.duck 任务文件；MCP；web 演示；flock 模式与多鸭分工（“最近的鸭去踢”“头鸭发现、鸭踢、头鸭判定”）。MuJoCo 真物理上 10/10 通过（fake provider）。
- ★ microduck-ai-world（shaibuafeez）：头戴相机 → VLM 出 bounded intent（不阻塞 50 Hz 控制环），语音/文本指令，离线 wander 兜底；Water Court 场景 + race。
- ★ MicroDuck TinyVLA：head-camera 帧 + 61 维状态 + 自然语言 → 动作，ONNX Runtime CPU，sim-only。
- nottyduck：桌面陪伴人格（手势策略 + 3D 办公室地图 + HF Jobs 训练 CLI）。
- MCP/网关类：joeynyc/microduck-mcp、aj-dev-smith/microduck-mcp、meckie-duck-gateway、OpenCastor、Strands provider、microduck-cli、quacksat（语音卫星/Home Assistant）、duckbench（MCP 化物理基准）。

### 2.4 视觉/感知
- pngwn/microduck-detector：YOLO11n 单类鸭检测（2.6M 参数，0.63 mAP50，合成渲染+真照片训练），配套检测数据集；what-the-microduck 演示 Space。
- ★ 认人：上游只给过 Reachy 的 face_detection_yunet 模型；microduck 的“认特定人/ReID/跟随某人”在社区尚未出现（D-Robotics 赛道 V3 做过视觉认球闭环，未做认人；本地 duck_play 的 person_follow 仍是 stub）→ 真空白。

### 2.5 仿真/平台/移植（做“新玩法”的现成地基）
- 官方 Sandbox：huggingface.co/spaces/pollen-robotics/microduck-simulator（MuJoCo WASM + onnxruntime-web，真策略 50 Hz，支持手柄/滚轮）。D-Robotics 的 RoboGo 云镜像/网页遛鸭即同源。
- 移植与端口：Genesis、Isaac Lab ×2、microduck-rl-torch、Apple Silicon lab、Unity Sim2Sim（含国产团结引擎）、WebXR/AR、iPhone Swift、DuckKit(Swift)、MicroDuckModels、RL Physics Overlay、kinematic viewer、3D bipedal teleop（hwihwalab）、specs-microduck（眼镜手势遥操）。
- Wicroduck：纯浏览器（无 Python）跑 MJCF，目标是在浏览器里训练——未完成。
- 数据/基准：golden vectors（官方策略的 obs/action 一致性向量）、Trajectory dataset（14-DOF 多模态轨迹，面向 offline RL/IL，sim-only）、Ball Challenge、检测数据集。
- maploc：ToF submap SLAM/重定位/A*（Rust，prototype 时代）。

### 2.6 D-Robotics Duck Together（RDK，我们所在的赛道）
- 计划至 2026-12-31；招募帖 35663；课程 14 集（35664~）；云镜像教程 35661；标杆 A-仿真 4096×6000 走路（1h27m，HF: Datawhale/Microduck-*）；云端遛鸭+RDK X5 闭环（35645/35692）；实体方向：RDK X5+微雪 ESP32 板方案（35686）。
- 社区完成度：V1 训练 → V2 板端 ONNX server 方阵 → V3 视觉追球闭环（MuJoCo 真值投影 bbox）→ V4 LightNav-0 + 3v3 足球仿真。尚无认人、多鸭 RL、自主行为栈类作品。

## 3. 空白分析与“目前没有”的方向建议（纯仿真 + RL + 交互约束下）

先排除已被占的：语言→技能编排（quackd/Lab/School）、VLA 底层控制（TinyVLA）、单鸭视觉追球/抓指定球（V3/Ball Challenge/tracking）、编舞/杂技技能（HF 一堆）、脚本化多鸭（3v3/Circus/Swarm）、VLM 世界（ai-world）。

**真正没人做的（按可行性与“有意思程度”排序）：**

1. **自主大脑行为栈（官方 M9 的仿真版）**：把 16 状态 + 能量/心情 + 新奇度网格 wander + 惊吓/声音反应 + 球戏/打盹/被摸，叠在真实 ONNX 技能上跑起来；评测标准就用官方的“放养 10 分钟值得看”。纯仿真可做：ToF/视觉用 MuJoCo 真值/渲染替代，BLE 多鸭用虚拟信标模拟。→ 这是“目前没有”最硬的一个，且能直接投稿 Duck Together 的“具身智能交互”。
2. **认特定人（ReID）+ 社交跟随**：头戴相机渲染帧 + 人体/人脸检测 + ReID → “只跟主人、绕圈打量陌生人、被召唤过来”；把“主人出现/消失”作为情绪输入。全球无 microduck 先例，D-Robotics 赛道也无。
3. **多鸭社会交互的 RL（不是脚本）**：follow-the-leader（保持间距、学出来的跟走）、keepaway/护球（两只鸭一只带球一只抢）、同步 dance（学到节拍一致，而非编舞）；2–4 只鸭 mjlab MARL/多 agent PPO，5090 可跑。现有 Circus/3v3/Swarm 全是脚本或假鸭。
4. **端到端视觉策略（egocentric pixels→actions）**：上游 BallKick 球盲、社区都靠 bbox+规则；真正训“第一视角 RGB/深度 + 本体感 → 追球/找球”的端到端策略（含视觉域随机化）没人做成。难但价值大，5090 集群是合适算力。
5. **分层/技能组合 RL（learned router over 9 skills）**：把 walk/kick/roulade/sitstand/ground_pick 当 options，用 RL 学“什么时候切哪个技能”（如连续追球）——介于 quackd 的 LLM 手选与我们 chase.py 的手写状态机之间的中间档没人做。
6. **离线 RL / 模仿学习**：社区发布了 trajectory dataset 但没人跑出 offline 策略；在 5090 上验证 offline RL→ONNX→可安装技能，是“数据玩法”空白。
7. **人在环实时互动（浏览器远程陪玩）**：网页端真人用鼠标/摄像头当“主人或球源”，与云端鸭实时玩 fetch/keepaway/躲猫猫；现有 WebXR 只做遥操，不是“学出来的人鸭互动玩法”。
8. **新奇度/好奇心驱动的长时探索 + 归巢**：官方 novelty-grid wander 的“探索房间-记得-回窝-打盹”长时序闭环，纯 RL 或 RL+状态机混合，可讲故事可评测。

> 注：方向 1/2/3 可拼成一个大叙事 Demo（例：鸭子在房间里自主生活 → 认出主人 → 主人抛球时去追/捡 → 心情好时主动求摸/唱歌），比单点技能更符合“做点有意思的目前没有的尝试”。

### 落地提示（结合我们现有资产）
- 已有 duck_play（chase.py / person_follow / slalom stub + 云端 50 Hz 闭环）正好是方向 2/5 的骨架：先补“L1 人代理 + ReID”，再把 chase 状态机换成“学出来的 router/option”。
- 云端 kickfix 镜像里 45 个任务可直接扩展：新增“多鸭场景”“人代理”“端到端视觉”等 env 与奖励。
- 社区发布物格式已统一：ONNX + manifest.json（schema 2）+ HF repo + README；任何成品按此发布即可被真机用户一键 robotctl policy add（M8 通道）→ “仿真产物可被真机安装”是 Duck Together 参赛加分点。

## 4. 关键出处
- 上游仓库：github.com/pollen-robotics/microduck、github.com/pollen-robotics/microduck_rl
- 上游文档：docs/README.md（索引）、docs/project/roadmap.md（M1–M9）、docs/robot/cheatsheet.md（能力全表）、docs/ideas/autonomous_behavior.md（自主大脑 ideas）
- 官方策略：huggingface.co/pollen-robotics/microduck-policies；官方沙箱 Space：huggingface.co/spaces/pollen-robotics/microduck-simulator
- 社区大全：github.com/joeynyc/awesome-microduck
- 重点作品：github.com/rokbenko/quackd、github.com/AlexBodner/microduck-tracking、github.com/shaibuafeez/microduck-ai-world
- D-Robotics：forum.d-robotics.cc /t/topic/35663（招募）、35645、35661、35683、35692 等；RoboGo DuckTogether 群组
