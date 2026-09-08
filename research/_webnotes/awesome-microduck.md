Awesome Microduck 

Software, simulators, policies, agent tools and coverage for Microduck, the open-source biped robot from Pollen Robotics and Hugging Face.

Microduck is a 25 cm, ~800 g walking duck with 15 motors, a camera, an 8×8 ToF depth sensor, two IMUs and a grasping beak. Every behavior it ships with (walking, sit/stand, kicking, ground pick, roller-skating, self-recovery) is a neural policy trained in MuJoCo and exported to ONNX, and the full sim-to-real stack is Apache-2.0 on GitHub. Pre-orders opened on 27 August 2026; first units are expected before Christmas 2026.

Microduck is a product of Pollen Robotics and Hugging Face. This is an independent, community-maintained list — not affiliated with, endorsed by, or sponsored by either company. Product names, logos and brands are the property of their respective owners, and every linked project belongs to its own authors under its own license.

Contents
Ecosystem Status
Official
Documentation
Simulation and Training
Policies and Skills
Datasets and Benchmarks
Agent Tools and MCP
Community Hubs and Registries
Apps and Ports
Hardware and Fabrication
Articles and Coverage
Videos
Community
Lineage
Ecosystem Status

The robot is pre-hardware: pre-orders are open, shipping is targeted for December 2026, and almost nobody outside Pollen has a physical unit yet. That shapes what is real today:

Simulation tools work now. The official browser sandbox, microduck_rl, and everything built on the published ONNX policies can be run and verified without a robot.

Hardware-facing tools are pre-validation. MCP servers, gateways and CLIs that target the real robotd API are written against the published design docs and mock transports; none listed here has been exercised on a shipped unit.

Policy distribution is landing now. Pollen published the nine shipped policies to the Hub as microduck-policies on 31 August 2026, and the policy channel (roadmap milestone M8) is being built on the policy-hub-design branch, with parts of it done as of the same date. The design sets a convention worth building against: one .onnx per Hub repo alongside a manifest.json giving observation and action dimensions, model API version and robot compatibility, driven by robotctl policy list | load | reset | check | update | search. None of it is on main yet, so today a policy still reaches a robot by hand.

Entries marked sim-only have not been validated on hardware.

Official
pollen-robotics/microduck - The robot's software: robotd 50 Hz control loop, mediad camera/WebRTC, padd gamepad, updater, and the nine shipped ONNX policies.
pollen-robotics/microduck_rl - RL training environments on mjlab (MuJoCo Warp) with PPO, BAM actuator models, backlash simulation and domain randomization. Needs a CUDA GPU.
pollen-robotics/microduck-gst-plugins - Prebuilt aarch64 GStreamer plugins (Rockchip MPP encoders, gst-plugins-rs WebRTC) used by the on-robot media daemon.
microduck-policies - The nine shipped ONNX policies published as a standalone Apache-2.0 repository on the Hugging Face Hub, so they can be pulled without cloning the daemon.
Microduck Sandbox - Official in-browser simulator: MuJoCo compiled to WebAssembly plus onnxruntime-web running the real policies at 50 Hz, with gamepad support and the roller-skate variant.
Product page - Specs, colorways and the launch story.
Store - Pre-orders at $399.
Press kit - Facts, full spec sheet, photos and downloads.
Meet Microduck - Launch blog post from Pollen Robotics.
Documentation

All from the pollen-robotics/microduck repository.

Docs index - Map of every doc in the repo.
Cheat sheet - robotctl commands for day-to-day use of the robot.
Architecture - How the daemons, control loop, policies and updater fit together.
Design docs - robotd, updater, remote WebRTC, boot recovery, restart order and the WebRTC console.
Policy channel design - How community policies will reach robots: the Hub repo layout, the manifest.json contract and the robotctl policy commands. On a branch, not yet merged.
Roadmap - Milestones M1–M9, including the Hub model channel (M8) and autonomous brain (M9).
duckctl - Controlling the robot from a laptop over Bluetooth.
Pair a gamepad - Bonding a controller to the robot.
Dev board setup - Setting up a development board and pushing branches.
Contributing guide - Upstream contribution standards.
Simulation and Training
microduck-rl-genesis - Genesis port of the walking task for AMD/ROCm GPUs, actuator model validated bit-exact against upstream. Sim-only.
Isaac Lab Microduck port - Isaac Lab extension with Microduck assets, BAM/backlash actuators and RSL-RL tasks for walking, kicking and parkour. Sim-only.
isaaclab-microduck - Isaac Lab 3.0 (Newton MJWarp) port with locomotion, running, ball-kick and two-robot rally tasks, each A/B'd against the mjlab baseline. Sim-only.
microduck-ros2-isaac - Tutorial for driving the public Microduck model from ROS 2 Jazzy and NVIDIA Isaac Sim, with joint control in RViz and the released walking policy in USD. Sim-only.
microduck_description - ROS 2 description package: URDF and xacro generated from the public model, with 38 visual meshes and a robot_state_publisher launch file.
microduck-ai-world - Embodied-AI playground pairing a robot runtime and RL policies with a detailed MuJoCo world and a vision-language brain that stays off the control loop. Sim-only.
microduck-lab - Reproducible training and evaluation workspace for NVIDIA DGX Spark that pins the official runtime, simulator and microduck_rl as submodules.
microduck-sim-playground - Lightweight educational workspace: bootstrap script, CPU MuJoCo viewer with keyboard poses, upstream pinned as submodules.
microduck-rl-lab - Retrains five official skills and composes them into one automatic MuJoCo obstacle course. Sim-only.
microduck-miniverse - Every published ONNX policy repackaged as a deterministic Miniverse simulation bundle.
microduck-lab (Apple Silicon) - Trains policies on a Mac with no CUDA GPU, against the same MJCF model and 61/14 contract as upstream, with a live browser viewer. Sim-only.
microduck-rl-on-thor - Getting the official training stack to run on aarch64 CUDA hardware (Thor, DGX Spark, Jetson), with every trap documented and verified on real machines. In English and Chinese.
Microduck RL Ball Follow - MuJoCo Warp training repo adding a target-following task, a command-block contract layer and a drag-the-ball demo. Sim-only.
Microduck School - Hosted Space where you set a lesson in plain English and watch the duck fail, retry and improve while the score climbs.
MicroDuck Playground - Independent continuation of microduck_rl collecting reproducible experiments, policy demonstrations and printable hardware add-ons, rebased on a pinned upstream commit.
Wicroduck - Attempt to put the whole loop behind a URL: MuJoCo compiled to WebAssembly steps the real MJCF in the browser with no Python and no backend. Simulation works today; in-browser training is the goal, not yet the state. Sim-only.
isaaclab_microduck - Full port of the official training stack to IsaacLab and PhysX: 37 environments across walking, collision, roller, backlash and testbench models, BAM M6 actuator dynamics, PPO configs and ONNX export. The published checkpoint is an integration smoke test, not a converged gait. Sim-only.
microduck-rl-torch - PyTorch-native rewrite of the training stack for machines without CUDA, with the same workflow carried up to an NVIDIA box or the cloud. Continuous integration and coverage on every commit. Sim-only.
MicroDuck Unity Sim2Sim - Runs the official MJCF and ONNX policies inside Unity/Tuanjie with native MuJoCo kept as the physics authority and Barracuda doing inference, so the engine owns only scene, input and rendering. A Godot/Jolt counterpart exists. Non-commercial use only, per the model license. Sim-only.
MicroDuck Swan Lake - Trains a walking policy in the MotrixSim simulator, then blends it per joint with open-loop choreography (policy on the legs, choreography on the head and neck) for a two-minute ballet with a written root-cause log. In Chinese. Sim-only.
duckbench - The physics bench under the golden vectors and the scored challenges: MuJoCo plus the shipped policies behind an HTTP service, a WebAssembly phone build, and the same bench exposed as MCP tools. Every published number names the plant it was measured in.
Policies and Skills

Community-trained policies and task definitions built on microduck_rl.

microduck-backflip - Reproducible mjlab backflip task with an evaluation battery, experiment log and explicit safety gates. Sim-only.
microduck-courier - Pick-carry-place task in an apartment scene with a trained policy, rollout clip and telemetry. Sim-only.
Jump playground - Browser sandbox fork with a custom-trained vertical-jump policy; live demo. Sim-only.
microduck-sidekick-dance - Drop-in mjlab task for a lateral dance step, with reward design notes. Task only, not yet trained.
microduck-step-up-policy - Policy pair for crossing a 25 mm square-edged step using the head as a temporary brake, then recovering upright; weights on the Hub. Sim-only.
microduck-max-height-jump - Deployable ONNX export and reproducibility evidence for a one-shot PPO jump, with the height claim stated as a training objective rather than a physical maximum. Sim-only.
microduck-walking yaw ablation - Single-variable reward ablation that cuts yaw-rate variance against the released alpha_walking baseline, with the evaluation harness that makes the comparison reproducible. Sim-only.
Microduck Circus - Three ducks learn to skip a shared long rope, two turning and one jumping, through an act-fail-practice-adapt agent loop with a holdout round. Sim-only.
nottyduck - Desk-companion persona with trained gesture policies, a 3D office mapper and a Hugging Face Jobs training CLI; policies on the Hub.
microduck-flamingo-cycle - One-legged flamingo pose policy on the Hugging Face Hub.
microduck-polite-bow - Bow gesture policy on the Hugging Face Hub.
microduck-moonwalk-backward - Backward moonwalk gait on the Hugging Face Hub.
More policies on the Hub - The growing long tail of community-trained gaits and gestures, searchable on the Hugging Face Hub.
microduck-detector - YOLO11n detector that finds a Microduck in an image, 2.6M parameters, scored at 0.63 mAP50 on a held-out split of synthetic renders and real press photos; try it in what-the-microduck.
Microduck RL 4096x6000 - Velocity-tracking reproduction pinned to an upstream commit: 4096 parallel environments, 6000 PPO iterations, with intermediate checkpoints, the ONNX export, training config, TensorBoard events and closed-loop replay video all kept. Sim-only.
Datasets and Benchmarks

Fixtures and scored tasks for checking a runner or a policy against numbers rather than against a video.

Policy golden vectors - Observation and action pairs recorded from the shipped policies, so an independent runner can be checked against the same numbers. A conformance fixture, not weights.
Microduck Ball Challenge - Scored ball-chasing benchmark with the physics plant pinned by hash; a stairs challenge follows the same discipline. Sim-only.
Trajectory dataset - Multi-modal state-action trajectories from the 14-DOF simulated robot, aimed at offline reinforcement learning and imitation. Sim-only.
Microduck detection dataset - Labelled bounding boxes over synthetic renders, composites and real press photographs, the training and validation split behind the detector above.
Agent Tools and MCP

Ways for LLM agents and scripts to drive a duck.

joeynyc/microduck-mcp - Agent-agnostic MCP server modeled on the real-robot robotd architecture: mock, MuJoCo sim, Unix-socket and SSH transports behind one tool set, with a safety layer. Hardware transports are pre-validation.
aj-dev-smith/microduck-mcp - MCP server driving the simulated duck (CPU MuJoCo with the official policies), with rendered camera frames as tool output and a live agent-experience debug page. Sim-only.
quackd - LLM goal-planning daemon named after the duck's own services: describe a task in plain language and Claude, OpenAI, Gemini or Grok sequences the robot's existing skills. Bundled simulator, .duck task files, safety rules, MCP support, on PyPI. Since 0.4 it drives other small robots too.
meckie-duck-gateway - Holds the robot's WebRTC/JSON-RPC session and re-exposes it as a small local HTTP API, with a hardware-free protocol double for testing.
OpenCastor Microduck integration - Third-party robot-agent framework that discovers Microducks, sends intents through robotd and composes routines.
Strands Robots Microduck provider - Python/MuJoCo provider wrapping the shipped ONNX policies behind a common simulation and hardware interface.
Microduck Lab (gr.Workflow) - Hosted Space that turns a plain-English routine into a sequence of the robot's skills through a language model, then plays it back.
quacksat - Turns the duck into a roaming voice satellite, with interchangeable Home Assistant Wyoming, agent-bridge and direct backends selected from one config file.
MicroDuck TinyVLA - Vision-language-action model driving a live MuJoCo duck from a head-camera frame, the 61-float state and a plain-English instruction, all on ONNX Runtime CPU. Sim-only.
microduck-cli - Same verbs for an agent and for a human: five noun groups over robotd's own JSON-RPC socket, --json on every command, and an empty runtime dependency list. On PyPI; checked against the real daemon and the MuJoCo body.
Community Hubs and Registries
MicroduckHub - Community policy browser listing the shipped behaviors and Hub retrains, with one-click deploy planned for when upstream's model channel ships.
uDuck Registry - Independent catalog of community policy descriptors with contract specs and verification status.
Apps and Ports
DuckKit - The Microduck as a pure Swift package: runs the real ONNX policies with the real 61-float observation at 50 Hz, plus kinematics, protocol types and Linux tests.
microduck-sim (iPhone) - The nine shipped policies plus MuJoCo running natively on iPhone in Swift/RealityKit, with an AR mode at true scale.
Microduck WebXR - Physics-driven Microduck for Meta Quest and ordinary browsers, with controller walking, learned skills, room placement and an autonomous wander mode.
Microduck Anatomy - Interactive holographic anatomy viewer with staged component focus and exploded assembly views.
microduck-tracking - Multi-object tracking on top of roboflow/trackers that gives the duck a target lock, so it fetches one thrown ball past identical distractors.
Microduck AR - WebXR adaptation of the official sandbox with AR placement and ground-pick interaction.
specs-microduck - Hand-gesture teleoperation of the simulated duck from Snap Spectacles, with in-lens telemetry.
MicroDuckModels - Browser simulator rebuilt on Three.js and React Three Fiber with MuJoCo WebAssembly physics and local ONNX inference, running all nine shipped policies. Readme in Chinese and English.
microquack - Procedural droid-voice synthesis for the duck: a Rust core rendered live in the browser via WebAssembly, also on Hugging Face.
RL Physics Overlay - Dependency-free telemetry overlay for the browser simulator showing joint forces, torques, contacts and learning signals without blocking the training loop. In Chinese and English.
MicroDuckSwarm - Authors a flock choreography once, compiles it to a show file preloaded on every duck, and syncs only the clock at showtime so a dropped network costs nothing. Runs against a protocol-faithful mock duck. Sim-only.
Microduck Studio - Local control room that puts robotd status, safe control and the MuJoCo body behind one browser page, deliberately duplicating none of the safety, inference or physics it fronts. Readme in English and Chinese.
Kinematic viewer - Drag any joint through its real range and watch the chain follow, with axis, hard limits, trainable limits and home angle shown live. One index.html, no build step; also a hosted Space.
3D bipedal teleop - Browser digital twin driven by the shipped policies over ONNX Runtime, with omnidirectional teleoperation and reported velocity-tracking error. In English and Korean. Sim-only.
Hardware and Fabrication

The hardware is not open source (no BOM, CAD or PCB files), but the MJCF and STL meshes are public.

OpenMicroDuck - Independent reverse-engineering and documentation project mapping what the robot contains and how its stack works, in English and Chinese, explicit that the hardware is not open source.
microduck-diy - Month-long build log for a hand-made duck from the public simulation meshes and printable parts, with staged files and a parts list. In Chinese.
microduck-replica - Reconstruction study deriving assembly and exploded drawings, CAD-importable assemblies, a fastener list and an electronics teardown (Radxa Zero 3W, TTL servo bus, the two custom boards) from the public MJCF, STL meshes and runtime source, in English and Chinese and not verified against physical hardware.
microduck-hardware-replica - FreeCAD multi-part assemblies, printable meshes and a planning-stage bill of materials derived from the public MJCF and STL models. In Chinese, and explicit that it is unaffiliated and unverified.
ChinaMicroDuck - Replication reference library: four costed manufacturing routes compared, an audit of which official assets may be reused under which license, environment verification reports and Chinese translations of the official docs.
Articles and Coverage
TechCrunch - Launch coverage.
Engadget - Pre-order details and specs.
The Register - Launch coverage with a developer angle.
The New Stack - Why the duck is a reinforcement-learning teaching platform.
IEEE Spectrum - Video Friday feature.
Digital Trends - On making physical-AI training cheaper and less fragile.
MarkTechPost - Technical summary of the RL stack.
Interesting Engineering - Overview of the robot's fall recovery and learning loop.
Hacker News discussion - Launch thread with 700+ points, including Pollen engineers answering questions.
Pointcast 031 - Long-form feature on the hardware, the open stack and programming behavior with agents.
Videos
We made a new robot. - Official launch film from Pollen Robotics.
Meet Microduck, the $399 Tiny Robot You Can Teach New Tricks - Official product overview.
Microduck Sim 2 Real - Official side-by-side of policies in simulation and on the robot.
Hugging Face Pushes Deeper Into Robotics With MicroDuck - Bloomberg Tech segment.
'Microduck' robot enters growing market of AI toys - Global News segment.
Community
Pollen Discord - Official community server; the Microduck channels are where the team answers questions.
Pollen Robotics on Hugging Face - Organization page hosting the sandbox Space and models.
Pollen Robotics on YouTube - Official channel.
@pollenrobotics on X - Official account.
Lineage

Microduck grew out of Open Duck Mini, Antoine Pirrone's open-hardware BDX-style droid, and the Open Duck community still shares Discord space, actuator models and sim-to-real lessons with it.

Open Duck Mini - The open-hardware predecessor: BOM, CAD, and the original mjlab training work.
Open Duck Mini Runtime - Raspberry Pi runtime for Open Duck Mini.
microduck_runtime (legacy) - Pre-launch Raspberry Pi runtime for the Microduck prototype; superseded by pollen-robotics/microduck.
microduck_maploc_rs - Time-of-flight submap SLAM, relocalization and A* planning in Rust, written by a Pollen engineer for the prototype duck runtime. The runtime it targets is not public; the crate is.
Contributing

Contributions welcome! Read the contribution guidelines first.