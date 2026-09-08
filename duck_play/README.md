# duck_play — 追球 / 认人 闭环模块（纯仿真）

与网页驾驶舱共用同一套 MuJoCo 场景与 ONNX 策略（复用 `sim_server.py` 的
LocalSim / PolicyBank / LocalKick），因此闭环结果与 Web 遛鸭一致。
CPU 推理 + 单环境仿真 → 与云端 RL 训练并行运行也不会抢 GPU。

## 结构
```
duck_play/
├── config.py                  # 常量与追球/认人/绕桩调参
├── perception/
│   ├── detections.py          # Detection / Perception 数据结构（检测器无关）
│   └── ground_truth.py        # 真值感知：直接从 MuJoCo 状态算球/人方位+伪bbox
├── behavior/
│   ├── chase.py               # 追球状态机 SEARCH→ALIGN→APPROACH→FOOT_SELECT→KICK
│   ├── person_follow.py       # 认人跟随（stub，待 L1 人代理）
│   └── slalom.py              # 带球绕桩（stub，衍生玩法）
├── control/runner.py          # 50Hz 闭环：obs构建=sim_server 同款，LocalKick 踢球
├── sim/env.py                 # 场景工具：放球/随机化（人代理、绕桩后续加）
├── eval/metrics.py            # 触球次数/路径/耗时/事件
└── launch/min_chase.py        # 最小闭环入口（真值bbox）
```

## 运行（CPU，不占训练 GPU）
```bash
cd /root/microduck_sim/duck_play
python3 launch/min_chase.py --time 12 --max-touches 1
python3 launch/min_chase.py --time 30 --max-touches 3 --randomize-ball   # 连续触球(无墙，球会滚远)`npython3 launch/min_chase.py --time 90 --max-touches 2 --arena             # 围墙场地：球被挡回可多次追踢`npython3 launch/person_demo.py --time 34                                 # L1 认人：召唤->跟随->陌生人绕圈`npython3 launch/min_chase.py --time 60 --max-touches 3 --arena --auto-restart  # 多轮连续追球(每轮重置)`npython3 launch/composite_demo.py --time 40                            # M1 组合: 找到主人->把球带给他
```
报告输出到 `duck_play/runs/*.json`。

## 里程碑（真值 → 真实视觉）
- [ ] M1 最小闭环：真值 bbox 追球 + 踢球（本骨架）
- [ ] M2 连续追同一颗球触球 N 次（踢后不重置球，等自然滚动再追）
- [ ] M3 换成渲染第一视角 RGB + 轻量检测器（YOLO 系），去掉真值
- [ ] M4 认人：L1 人代理 + 跟随/注视/认特定人
- [ ] M5 组合叙事：“找到主人→带球靠近主人”
- [ ] M6（可选）带球绕桩 slalom / 多鸭足球角色分工

## 注意
- 训练期间勿跑 `--randomize-ball` 大规模扫描；单次短测试没问题。
- `allow_reset_on_fall` 只用于开发调试；正式评测置 False。
- 不要与 sim_server.py 同端口/同进程跑（无冲突但会抢 CPU 单核）。



