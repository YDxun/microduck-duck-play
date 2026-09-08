# MicroDuck “认人”方向：仓库/模型调研与训练思路分析（2026-09-09）

> 输入：你的 Duck Together 帖子 https://forum.d-robotics.cc/t/topic/35703 （L1 认人闭环，Day 1）+ 仓库 YDxun/microduck-duck-play
> 调研方式：Codex + in-app 浏览器 + 本地浅克隆（microduck-duck-play、pollen-robotics/microduck_rl）逐文件核对
> 结论先行：**“认人 + 个体社交行为”在 microduck 全生态是零占用**（GitHub 仓库搜索=0、HF 模型=0、上游 issues/docs=无、awesome 列表=无）。真正没人做、且能做出“研究味”的是：把“人”放进 RL 训练环路（而不是只做检测/状态机），即 **identity/proxemics-conditioned 的社交运动策略 + 鸭子视角合成数据 + 人-鸭交互任务进 mjlab**。

---

## 1. 生态盘点：microduck 里“和人相关”的仓库/资产到底有哪些

### 1.1 直接与“人”相关的 = 0（证据）
- GitHub repo 搜索：microduck person / human / reid / face detection / follow person / perception —— **0 个仓库**（仅 21 个 commit/11 个 PR 里的自然语言“person/personal”误命中）。
- HF models：搜索 “microduck person” = 空；microduck 模型池全部是技能策略与鸭检测。
- 上游 microduck issues（19 个）：无任何视觉/认人条目（只有 WebRTC 双向音频、NFC 等）。
- microduck_rl 源码逐文件 grep：`src/mjlab_microduck/` 无 person/human 任务，无相机/像素观测（唯一含 “camera” 的是 export 视频渲染）；任务表 = 运动/球/滚轮，全是“物”不是“人”。
- 官方 ideas（autonomous_behavior.md）里的“认人”是 **鸭认鸭**（BLE 身份），不是认人。

### 1.2 可当“模板/地基”复用的（重点）
| 仓库/资产 | 为什么对认人有用 | 出处 |
|---|---|---|
| microduck-detector + detection dataset | **方法论模板**：合成渲染+真照片 → 训 YOLO11n 小模型（2.6M 参数）→ mAP50 评测。把类别从“鸭”换成“人”，流程照抄即可 | pngwn，awesome 列表 |
| microduck-tracking | **流水线模板**：head-camera 帧 → 检测（RF-DETR/分割真值）→ SORT 跟踪 → “轨道即身份”→ 驱动官方策略抓特定球。认人可复用它的检测/跟踪/导航部分，把“抛球速度选目标”换成“ReID 选人” | AlexBodner/microduck-tracking |
| microduck_rl 自带 `scene_apartment.xml` + `apartment.xml`、`vslam_room.xml` | **室内认人场景现成**：纹理墙、多房间/开阔室，head_camera 有东西可看（注释原话）。当前无人用它做任务——直接作为 L2 室内认人场地 | pollen-robotics/microduck_rl robot/microduck/ |
| 你的 sim 栈（sim_server 的 LocalSim/PolicyBank/LocalKick + head_camera EGL 320×240） | 第一视角 RGB 渲染现成；Detection 接口已预留“learned detector 替换真值” | duck-play ground_truth.py 注释 |
| microduck-ai-world | **架构模板**：VLM 大脑异步出 bounded intent、不阻塞 50 Hz 控制环、离线 wander 兜底。L3 社交大脑可照此分层 | shaibuafeez/microduck-ai-world |
| quackd | 现状基准：LLM 把“目标”拆成鸭子自带技能（秒级离散选择）。L3 必须差异化（见 §3） | rokbenko/quackd |
| MicroDuck TinyVLA | 现状基准：VLA 从 head-cam 帧+61 维状态出动作（CPU ONNX）。说明“像素→动作”已被试，但无身份/信任层 | awesome 列表 |
| pollen-robotics face_detection_yunet（HF） | 人脸检测参考（Reachy 用，非鸭；说明厂内有人脸方向沉淀） | HF pollen-robotics |
| Datawhale trajectory dataset | 离线 RL/IL 素材（14-DOF 轨迹）；可扩出“认人轨迹”版 | awesome 列表 |
| RDK 侧 DOSOD/BPU 模型 | 若未来接 RDK X5：BPU 可直接跑人检测（D-Robotics 生态有现成人检测模型） | 地瓜生态 |

---

## 2. 你现在的 L1 本质，以及“不够研究”在哪

代码核对后的结构：
- 场景：`robot_allcollisions.xml` + 球 + **2 个胶囊 mocap 人**（owner 红衣/stranger 蓝衣，胸前一个 tag geom）→ 本质是“颜色/标签=身份”。
- 感知：`GroundTruthPerception` 直接读 MuJoCo 状态 → 转 trunk 系 bearing/range + 伪 bbox（320×240 针孔近似）。
- 行为：`PersonFollowController` **手写 P 控制状态机**（SUMMON/FOLLOW/ORBIT/SEARCH），输出 [vx,vy,wz]。
- 控制：`LocalKick.select` 选 walk/stand 官方 ONNX → 标准 61 维 obs → 50 Hz。

一句话：**感知是上帝视角，决策是手写规则，运动是官方走路模型。** 这三层都还不是“你训出来的研究”。
用户诉求“不想只复用走路模型”→ 关键是 **让 2/3 层里至少一层变成你训练出的模型，且输入里带上“人”**。

---

## 3. 建议的研究/训练路线（三档，按“研究增量 × 可实现度”排）

### 档位 A：感知层换血——鸭子视角（25cm 高度）的人检测 + ReID（工程+数据贡献）
目标：把“真值/颜色标签”换成“渲染 RGB → 检测 → ReID → 身份”，仍可先挂手写状态机跑通。
- 造数据（这是可发布资产，microduck 无先例）：
  - 用 MuJoCo EGL 从 head_camera 渲染合成人（建议把胶囊人换成带纹理的人形：MuJoCo Menagerie CC0 humanoid 有 skin，或用 SMPL 网格离线烘焙；衣服用 2D texture 做花纹而不是纯色，**必须打破“颜色即身份”**）。
  - 域随机化：光照/相机噪声/距离 0.5–3m/多人重叠/出画/鸭子自身遮挡/不同人形与体型/坐姿走姿。
  - 标注：bbox + instance id（+可选 2D keypoints + 动作标签），MuJoCo 直接出真值框。
  - 发布 `Microduck-Person-Ego` 数据集（学 microduck-detection-dataset 的做法，附划分与评测）。
- 模型：
  - 检测：YOLO11n/RTMDet-nano（照 microduck-detector 模板，320 输入）；
  - ReID：两个可选项——
    (a) 小 triplet embedder（在合成身份上训，评测 “top-1 owner 检索”）；
    (b) **CLIP/视觉-语言“按描述找人”**（“穿红衣服的人”“戴帽子的”→ embedding 匹配），这条与后续 LLM Agent 天然连通，且天然支持“新访客不用注册”。
  - 跟踪：SORT/ByteTrack（复用 microduck-tracking 已验证的 SORT+BIoU 50Hz 方案）→ 轨道稳定性补单帧检测抖动。
- 接缝：替换 `GroundTruthPerception` → 新 `VisionPerception`，输出仍是你的 `Detection(label=owner/stranger/unknown, cx,cy,w,h,range,bearing…)`，下游状态机零改动。注意：**感知不用 50Hz**——5–10Hz 异步即可，检测/ReID 放线程，避免吃掉控制核。

### 档位 B（主菜/研究核心）：把“人”放进 RL 训练环路 —— identity/proxemics-conditioned 社交运动策略
这是 microduck 生态真正没有的东西：**不是“官方走路模型 + 手写规则”，而是你训练出的、以“人”为观测与奖赏的策略**。两种做法：

B1 命令级社交策略（推荐先做，稳健、可演示、可发布 ONNX）
- 定位：接替 `PersonFollowController`，成为 **学出来的高层控制器**，输出仍是 [vx,vy,wz] 喂官方 walk（策略热切换不变）。
- 观测：≤N 个人的相对量（bearing、range、range_rate、person 速度、身份 embedding 或 one-hot 信任级）+ 自身状态（IMU/高度/是否摔倒）+ 当前社会意图（summon/follow/orbit/ignore）。
- 奖赏（把“社交常识”写成可学目标）：
  - follow：与主人保持 0.6–0.9m 带内、正对主人、主人动则跟；
  - proxemics/个人空间：任何人不进 <0.45m（除非 petting/互动态）；
  - stranger 靠近 → orbit（保持 0.9–1.3m 环形）或侧移让路，而不是无差别跟随；
  - summon：接近到带内并保持 → 成功奖；
  - 平滑性/能耗/少摔倒（复用 velocity 任务的正则化配方）。
- 训练：PPO，mjlab 4096 env；人代理用 scripted 随机路径（走/停/召唤/逼近），带域随机。导 ONNX（[1,?]->[1,3] 命令）→ 50Hz 部署，运行时可被官方 walk 直接消费。可发布 `microduck-social-proxemics-ctrl`。
- 关键区别（避免“有人做过”）：
  - vs community “Ball Follow”RL 任务：那是**点目标跟随**，无身份、无陌生人回避、无个人空间、无信任级；
  - vs quackd：那是 LLM 秒级离散挑技能；B1 是 50Hz 连续、可微分、学过 proxemics 的运动控制；
  - vs 你现在的状态机：状态机是 if-else + 固定增益，B1 学会“多人同时在场/被夹击/人突然转向”的鲁棒策略（状态机在这些场景会抖）。

B2 关节级人-社交一体化策略（研究分量最重，风险高）
- 在 velocity 任务基础上改：obs 加“人相对量 + 身份”，把 follow/orbit/summon 直接写进关节级奖赏，训练一个 **端到端“看到人就能走/绕/停”的 ONNX**（不再是命令-策略两级）。好处：与人相关的运动被联合优化（转身看人+迈步更协调）；坏处：训练时长与摔倒率管理成本高（预估 1 张 5090 数小时~1 天级）。这是把“认人”写进 locomotion 本身，属于强研究 claim。

B3（可选项，最前沿但最重）：第一视角像素进策略（E2E vision policy）
- head-cam RGB/深度 → CNN → 动作；需 MuJoCo GPU 栅格化 + 视觉域随机化，算力吃紧。
- 坦白讲：**single 5090 训双足视觉策略属于高风险高投入**，建议排在 B1/B2 之后作为论文级延伸，Duck Together 演示不必押注在此。
- 现有 TinyVLA 只是“用 VLM 从像素出动作”的 demo，不是 RL 训出来的视觉运动策略，二者不冲突。

### 档位 C：L3 “社交大脑”差异化（避免做成第二个 quackd）
你的 L2/L3 规划很好，但社区已有 quackd（目标→技能）+ ai-world（VLM intent）+ Lab/School（LLM 上课）。要“没做过”，差异化点放在：
1. **身份/信任是第一公民**：quackd 无身份概念；你按 owner/guest/stranger 分级响应（可配置策略表）——这是社交机器人里“信任/隐私”层，microduck 生态无人做；
2. **记忆与个性化**：episodic 记忆（何时认识、常坐位置、喜欢被摸与否）+ 熟悉度连续量（不只是 owner/stranger 二值）→ 影响行为参数；
3. **意图从“状态估计”来，不是只从 LLM 来**：视觉手势/坐姿/久坐/靠近远离 → 隐状态（HMM/小 RNN），LLM 只消费“慢事件”（召唤/指路/闲聊），连续社交运动交给 B1/B2 的 RL 策略——即 **“LLM 管慢、RL 管快”的双脑**，这是结构上的新组合；
4. 决策链可解释输出（看到谁→推断什么→做什么）用于评审。

> 提醒：把 quackd/ai-world 当 L3 的 baseline 在帖子里对比引用，能抬高新颖性论证，但别把它当自己的卖点。

---

## 4. “不想做有人做过的”核对表（做之前先对一遍）
| 已有人做（microduck 生态内） | 你的规避/差异点 |
|---|---|
| 追球/连踢/抓指定球（Ball Challenge、tracking、V3、Ball Follow） | 不做球，或只把球当“主人指派的物”出现 |
| 目标点跟随 RL（Ball Follow / drag-the-ball） | 那是点目标；你是**人**：身份、信任、proxemics、绕陌生人、被召唤 |
| LLM 目标→技能（quackd/Lab/School） | 不做通用任务规划；做“身份+意图+信任”的社交闭环；RL 管连续运动 |
| VLA 像素→动作（TinyVLA） | 不做通用 VLA；做低视角人 ReID + RL 社交运动 |
| 导航（LightNav） | 不做跨房找沙发；做“人跟随/绕行/召唤到位”这类社交近程行为 |
| 多鸭（3v3/Circus/Swarm/flock） | 不做鸭-鸭；做鸭-人 |
| 官方走路/技能（alpha_*、ball_kick…） | 只当“小脑/底座”，真正产出是 B1/B2 训出的社交策略与新任务 |
| 鸭检测/鸭识别（detector/ideas 里 duck-duck） | 你做的是**人**检测/ReID |

诚实的新颖性边界（写帖/汇报时用）：
- 通用机器人学里“人跟随/ReID/proxemics 导航”有先例（如 proxemics-based DRL navigation、合成 ReID 域适应 PersonX→Alice）。所以**不要声称“全世界首创认人”**。
- 真正可主张的：① 首次在 **25cm 双足鸭的低视角（≈宠物/小孩高度）** 做人感知与社交运动；② 与 **双足 RL 步态耦合的 identity/proxemics 策略**（不是轮式底盘/全向底盘）；③ 全链路 open（数据集/env/策略/评测）落在 microduck 开源栈上；④ Duck Together 赛道内该方向目前无人。

---

## 5. 落地路线与提交物（结合你已有资产）
- M1（本周）：L2 数据管线——把人代理升级（纹理/体型/动作多样化），EGL 渲染 head-cam 数据集 1–2 万帧（多场景含 apartment.xml），跑通 YOLO 人检测 + SORT + 真值对照。
- M2：ReID（triplet 或 CLIP 文本匹配），把 person_demo 切到 VisionPerception，保持状态机不变，复测原指标（summon_ok / follow 带内占比 / orbit 次数）→ 证明“真值→真实视觉”不掉点。
- M3：B1 社交策略训练（4k env），导 ONNX，替换手写状态机；新增场景（多人、被夹击、主人走动召唤、陌生人逼近）并给新指标（个人空间入侵次数、跟随成功、平滑度）。发布 HF 策略 + mjlab 任务代码。
- M4（可选加分）：B2 关节级一体化；或“认人+取物叙事”（主人指红色杯子→鸭子 ground_pick 官方技能→踢/送到主人）——用官方技能做“物”，人只做“身份/意图”。
- 提交物模板：mjlab 任务注册（list-envs 可见）+ ONNX+manifest(schema2) + 数据集 HF + 评测 JSONL/视频 + 论坛帖（含对比 quackd/tracking/Ball-Follow 的差异表）。

---

## 6. 关键参考
- 你的帖子：https://forum.d-robotics.cc/t/topic/35703 ；仓库 YDxun/microduck-duck-play
- 上游：pollen-robotics/microduck、microduck_rl（scene_apartment.xml / vslam_room.xml / head_camera 已具备）
- 模板：pngwn microduck-detector（含检测数据集）、AlexBodner/microduck-tracking、shaibuafeez/microduck-ai-world、rokbenko/quackd
- 社区大全：joeynyc/awesome-microduck；官方策略 HF：pollen-robotics/microduck-policies
- 通用先例（界定新颖性用）：proxemics-based DRL 社会导航；合成域 ReID（PersonX/AliceBench）；低视角/宠物视角感知（小众）