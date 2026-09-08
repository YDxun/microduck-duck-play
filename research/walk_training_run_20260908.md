# 正式走路训练运行记录 (2026-09-08)

- 任务: Mjlab-Velocity-Flat-MicroDuck（平地速度跟踪 = 走路基线）
- 配置: 4096 并行环境 x 6000 PPO 迭代, WANDB_MODE=offline, tensorboard
- run-name: ydx-walk-4096x6000
- 启动: pid 8804 @ 08:04 UTC; 首轮迭代 ~1.23s; ETA ~2h08m
- 日志: /root/microduck_sim/train_walk_4096x6000.log
- 脚本(远端): /root/microduck_sim/train_walk_ydx.sh
- 产物目录: /root/microduck_sim/microduck_rl/logs/rsl_rl/velocity/<时间>_ydx-walk-4096x6000/
  - model_*.pt (每~500轮), events.out.tfevents.*, 结束后自动 ONNX
- 导出: cd /root/microduck_sim && ./export.sh Mjlab-Velocity-Flat-MicroDuck <abs model.pt> <abs out.onnx>
- 监控: tensorboard http://127.0.0.1:16006 (本机隧道->远端6006)
- 验收基线(参考): 社区 4096x6000 -> mean reward ~119.6, mean episode length ~972

## 训练完成结果 (2026-09-08)
- 6000/6000 迭代完成，耗时 ~1h59m；进程正常退出，GPU 已释放
- 最终指标：mean reward ~81.5，mean episode length ~919.9（鸭基本能撑满回合不摔），fell_over≈0.63，nan=0
- checkpoint：model_0..model_5999.pt（每 250 轮一个，共 25 个）
- 自动导出 ONNX：<运行目录>/2026-09-08_08-04-08_ydx-walk-4096x6000.onnx
- CPU 直行 5s 验证：ours fwd=0.48m/avg0.10m/s/航向漂移+108.6deg；official alpha_walking fwd=0.85m/0.17m/s/漂移-25.8deg
- 结论：能站能走不摔，但“走得慢且不直”，速度跟踪弱于官方 alpha_walking —— 属“可继续训练的中间基线”
- 建议：如要与官方相当，可断点续训（--resume model_5999.pt 再训 6000 迭代，约再 2h）；期间 duck_play 演示仍用官方 alpha_walking
