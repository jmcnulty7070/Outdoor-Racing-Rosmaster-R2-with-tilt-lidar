# r2_tg30_race — Outdoor Racing Stack
### ROSMASTER R2 · TG30 Tilted LiDAR · ROS 1 Noetic

Complete outdoor racing system: SLAM → localize → record path → close loop → race with pure-pursuit + FTG obstacle avoidance.

---

## Cartographer vs GMapping — Which to Use?

**Use Cartographer. Here is why:**

| Capability | Cartographer | GMapping |
|---|---|---|
| IMU fusion | ✅ Native (`tracking_frame = imu_link`) | ❌ None |
| Loop closure | ✅ Pose-graph global optimization | ❌ Particle filter only — drifts on loops |
| Outdoor performance | ✅ Handles sparse outdoor scans well | ⚠️ Struggles without dense indoor walls |
| Tilted LiDAR | ✅ Works with derived `/scan_obstacles` | ⚠️ Works but no IMU compensation |
| Map quality after full lap | ✅ Start/end align after loop closure | ❌ Start/end often misaligned by 0.3–1 m |
| Save/reload for AMCL | ✅ Export `.pbstream` + `.pgm/.yaml` | ✅ Direct `map_saver` |
| CPU on Jetson Orin Nano | ~15–25% | ~5–10% |

**The verdict:** Cartographer's pose-graph loop closure is essential for a race circuit. When you drive a full lap and return to the start, Cartographer will snap the map closed globally. GMapping will leave a visible seam. AMCL then localizes against the Cartographer-quality map with high reliability.

GMapping is available as a fallback (`mapping_gmapping.launch` is an alias to Cartographer in this package). It is not recommended.

---

## System Architecture

```
Hardware: ROSMASTER R2 (Ackermann) + TG30 LiDAR (tilted -5°) + board IMU

TF tree at runtime:
  map ──(AMCL)──► odom ──(EKF: wheel+IMU)──► base_footprint
                                                     │
                                             base_link (z=+21.5mm)
                                             ├── laser_link  (pitch=-5°, z=+164.9mm)
                                             ├── imu_link
                                             └── camera_link

Sensor pipeline:
  /scan (raw TG30, laser_link frame)
    │
    ▼ laser_filters (range + shadow + speckle)
  /scan_filtered
    │
    ▼ scan_to_cloud  (laser_geometry projectLaser)
  /scan_cloud (PointCloud2 in laser_link frame)
    │
    ▼ pointcloud_to_laserscan (height slice 0.025–0.28 m in base_footprint)
  /scan_obstacles  ← used by AMCL, Cartographer, FTG, pure pursuit

IMU pipeline:
  /imu/imu_raw → imu_filter_madgwick → /imu/imu_data
                                              │
                              ┌───────────────┴──────────────────┐
                              ▼                                  ▼
                       ekf_localization                   Cartographer
                       → /odom (EKF-smoothed)             (tracking_frame=imu_link)

Racing control pipeline:
  /race_path (map frame)
      ▼
  pure_pursuit_twist.py → /cmd_vel_auto_raw
      ▼
  cmdvel_gate.py (deadman) → /cmd_vel_auto
      ▼
  steering_modifier.py ← /scan_obstacles ← follow_the_gap.py
      ▼
  /cmd_vel_safety
      ▼
  twist_mux → /cmd_vel → twist_to_ackermann → /ackermann_cmd → hardware
```

---

## Step-by-Step Workflow

### Prerequisites — build once

```bash
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

---

### Step 1 — Bringup (always run first)

Starts the hardware driver, EKF, IMU filter, joint state publisher.

```bash
roslaunch yahboomcar_bringup bringup.launch use_ekf:=true
```

Verify:
```bash
rostopic hz /imu/imu_data    # should be ~50 Hz
rostopic hz /odom            # should be ~20 Hz
rosrun tf tf_echo map odom   # will fail until Step 2 provides map→odom
```

---

### Step 2a — Map the Course with Cartographer

```bash
# Terminal 2
roslaunch r2_tg30_race mapping_cartographer.launch start_driver:=true

# Terminal 3 — watch in RViz
roslaunch r2_tg30_race view_mapping.launch
```

**Drive the full course at low speed (0.2–0.3 m/s).** Complete at least one full lap so Cartographer can find the loop closure.

**Closing the loop in Cartographer** (important):
When you return to the start position, Cartographer will automatically detect that the current scan matches the beginning of the map and trigger a global pose-graph optimization. In RViz you will see the map "snap" into alignment. Wait 5–10 seconds for this to settle before saving.

Signs the loop closed successfully:
- The trajectory line in RViz reconnects to the start cleanly
- The map image shows consistent walls/edges with no double-image artefacts
- `rostopic echo /constraint_list` shows a loop-closure constraint (type=INTER_SUBMAP)

**Save the map:**
```bash
# In a new terminal — saves both the 2D occupancy map and the pbstream
rosservice call /finish_trajectory 0
rosservice call /write_state "{filename: '$(rospack find r2_tg30_race)/maps/driveway_course.pbstream'}"
rosrun map_server map_saver -f $(rospack find r2_tg30_race)/maps/driveway_course
```

This creates:
- `maps/driveway_course.pgm` — occupancy grid image
- `maps/driveway_course.yaml` — map metadata
- `maps/driveway_course.pbstream` — Cartographer internal state (for re-localization)

---

### Step 2b — (Optional) GMapping fallback

Only use if Cartographer is unavailable:

```bash
roslaunch yahboomcar_nav yahboomcar_map.launch
# Save:
rosrun map_server map_saver -f $(rospack find r2_tg30_race)/maps/driveway_course
```

Note: GMapping maps will have a seam at the loop closure. AMCL will still work but localization quality is lower.

---

### Step 3 — Record the Race Path (0.2 m waypoints, live)

With AMCL running (Step 4 below, OR replay from Cartographer), drive the race line and record waypoints directly into the map frame.

```bash
# Terminal: start the live recorder BEFORE driving
rosrun r2_tg30_race record_waypoints_live.py \
    _spacing_m:=0.20 \
    _out_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints.yaml

# Drive the circuit with the joystick at race speed.
# Watch /recorded_path_live in RViz to see waypoints appear in real time.
# When done, press Ctrl-C — the YAML is saved automatically.
```

**Check the result:**
```bash
python3 -c "
import yaml
with open('$(rospack find r2_tg30_race)/waypoints/waypoints.yaml') as f:
    d = yaml.safe_load(f)
wps = d['waypoints']
print(f'frame_id: {d[\"frame_id\"]}')
print(f'waypoints: {len(wps)}')
print(f'first: {wps[0]}')
print(f'last:  {wps[-1]}')
"
```

**The frame_id must be "map".** If it says "odom", something is wrong with the TF chain — check that AMCL is running and converged before recording.

Alternatively, extract from a pre-recorded bag:
```bash
python3 $(rospack find r2_tg30_race)/scripts/waypoint_extractor.py \
    --bag ~/bags/driveway_run01.bag \
    --mode auto \
    --spacing_m 0.20 \
    --map_frame map \
    --out_yaml $(rospack find r2_tg30_race)/waypoints/waypoints.yaml
```

---

### Step 4 — Close the Loop

After recording, the last waypoint is wherever you stopped — probably near but not exactly at the first waypoint. This step bridges them smoothly so pure pursuit can loop infinitely without a teleport.

```bash
python3 $(rospack find r2_tg30_race)/scripts/close_loop.py \
    --in_yaml  $(rospack find r2_tg30_race)/waypoints/waypoints.yaml \
    --out_yaml $(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml \
    --spacing_m 0.20 \
    --close_thresh 2.0

# Inspect:
python3 -c "
import yaml
with open('$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml') as f:
    d = yaml.safe_load(f)
wps = d['waypoints']
print(f'{len(wps)} waypoints, first={wps[0]}, last={wps[-1]}')
"
```

If you get `ERROR: gap X.XX m > close_thresh`:
- The gap is too large. Either drive the course again and stop closer to the start, or use `--close_thresh <larger_value>` or `--force`. A gap > 3 m will produce a visible shortcut on the path.

Optional smoothing at the seam (recommended if gap > 0.5 m):
```bash
python3 close_loop.py ... --smooth_window 7
```

Update `racing_stack.launch` to use the closed path:
```xml
<arg name="waypoint_yaml"
     default="$(find r2_tg30_race)/waypoints/waypoints_closed.yaml"/>
```

---

### Step 5 — Verify the Path in RViz Before Racing

```bash
# Terminal 1: bringup
roslaunch yahboomcar_bringup bringup.launch use_ekf:=true

# Terminal 2: localization
roslaunch r2_tg30_race localization_amcl.launch start_driver:=true

# Terminal 3: just the waypoint publisher (no driving yet)
rosrun r2_tg30_race waypoint_map_builder.py \
    _yaml_file:=$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml \
    _path_topic:=/race_path

# Terminal 4: RViz localization view
roslaunch r2_tg30_race view_localization.launch
```

In RViz you will see:
- **Yellow line** — the `/race_path` pure pursuit will follow
- **Green spheres** — individual waypoints at 0.2 m spacing
- **Red arrow** — current AMCL pose estimate
- **Red particles** — AMCL particle cloud

Set the 2D Pose Estimate (click the toolbar button) to initialize AMCL if the particles are scattered. The particles should collapse to a tight cluster within a few seconds of driving.

**Checklist before racing:**
- [ ] Yellow path is smooth with no teleports or gaps
- [ ] Path loop closes cleanly at the start
- [ ] AMCL particles are converged (tight cluster)
- [ ] `/scan_obstacles` (green dots) shows curb/grass edges where expected
- [ ] TF tree shows `map → odom → base_footprint → base_link → laser_link`

---

### Step 6 — Race

```bash
# Terminal 1: bringup (if not already running)
roslaunch yahboomcar_bringup bringup.launch use_ekf:=true

# Terminal 2: localization
roslaunch r2_tg30_race localization_amcl.launch start_driver:=true

# Terminal 3: racing stack
roslaunch r2_tg30_race racing_stack.launch \
    waypoint_yaml:=$(rospack find r2_tg30_race)/waypoints/waypoints_closed.yaml

# Terminal 4: RViz racing view (shows path + lookahead + obstacles)
roslaunch r2_tg30_race view_racing.launch
```

**Enable autonomous mode:** Hold the deadman button on the joystick (default: button 4 / LB).

**What you see in racing.rviz:**
- **Yellow line** — the recorded race path
- **Orange sphere** — current pure-pursuit lookahead point (moves ahead of the robot)
- **Green dots** — `/scan_obstacles` — curb faces and grass edges
- **Red arrow** — AMCL pose
- **Driving Mode text** — "AUTO" when deadman held, "MANUAL" otherwise

**Release deadman at any time** to hand back to manual control immediately.

---

## Displaying the Pure-Pursuit Path in RViz

The racing.rviz config already includes all needed displays. To add them manually to any RViz session:

**Race Path (the recorded waypoints):**
- Add → Path
- Topic: `/race_path`
- Color: 255, 210, 0 (yellow)
- Line Width: 0.10

**Lookahead Point (where PP is steering toward):**
- Add → PointStamped
- Topic: `/pure_pursuit/lookahead_point`
- Color: 255, 170, 0 (amber)
- Radius: 0.14

**Waypoint Markers (individual sphere per waypoint):**
- Add → MarkerArray
- Topic: `/race_waypoints`

**Live recorded path (during recording only):**
- Add → Path
- Topic: `/recorded_path_live`
- Color: 0, 200, 255 (cyan)

---

## Loop Closure — Detailed Guide

### What "closing the loop" means

When you drive a circuit and stop, your last waypoint is some distance from your first. Pure pursuit needs a continuous loop to race indefinitely. `close_loop.py` bridges the gap by:

1. Computing the straight-line distance from last waypoint → first waypoint
2. Inserting bridge waypoints at 0.2 m intervals along that line
3. Interpolating heading (yaw) linearly across the bridge
4. Optionally smoothing the entire path with a moving average

### How Cartographer closes the loop (independently)

Cartographer's loop closure is a separate, map-quality operation:
- When the robot returns near the start, Cartographer matches the current scan against stored submaps
- A loop-closure constraint is added to the pose graph
- The entire trajectory is re-optimized globally — start and end snap together in the MAP frame
- This makes the map consistent, so AMCL can localize reliably at all points on the circuit

You should always wait for Cartographer's loop closure before saving the map and recording waypoints. The map quality difference is large: without loop closure, AMCL will struggle at the seam.

### Signs Cartographer loop closure fired

```bash
# In a terminal while Cartographer is running:
rostopic echo /constraint_list | grep -A5 "INTER_SUBMAP"
```
You'll see constraints with `tag: INTER_SUBMAP` — each one is a loop closure. One or more of these should appear after you complete a full lap.

### Troubleshooting loop closure failures

| Symptom | Cause | Fix |
|---|---|---|
| No loop closure after full lap | Course too featureless (open park) | Slow down, drive more carefully near start, add `min_score: 0.55` to lua |
| Map looks doubled at start | Loop closure fired but optimization incomplete | Wait 10s after returning to start before saving |
| Large gap in waypoints | Stopped too far from start | Re-record, or use `--force` with a larger `--close_thresh` |

---

## Key Topics

| Topic | Type | Description |
|---|---|---|
| `/scan` | LaserScan | Raw TG30 |
| `/scan_filtered` | LaserScan | After filter chain |
| `/scan_obstacles` | LaserScan | Height-sliced (curb/grass included) |
| `/race_path` | nav_msgs/Path | Waypoints in **map** frame |
| `/race_waypoints` | MarkerArray | Sphere per waypoint in RViz |
| `/recorded_path_live` | nav_msgs/Path | Path during live recording |
| `/pure_pursuit/lookahead_point` | PointStamped | PP steering target |
| `/driving_mode` | String | "AUTO" or "MANUAL" |
| `/auto_enable` | Bool | Deadman gate signal |
| `/cmd_vel_auto_raw` | Twist | Pure pursuit output |
| `/cmd_vel_ftg_raw` | Twist | FTG output |
| `/cmd_vel_safety` | Twist | Blended output |
| `/cmd_vel` | Twist | Final muxed command |
| `/ackermann_cmd` | AckermannDriveStamped | To hardware |
| `/imu/imu_data` | Imu | EKF-fused → Cartographer + EKF |
| `/odom` | Odometry | EKF output (wheel + IMU) |
| `/amcl_pose` | PoseWithCovarianceStamped | Localization result |
| `/map` | OccupancyGrid | Saved 2D map from Cartographer |

---

## Scripts Reference

| Script | Purpose | Usage |
|---|---|---|
| `record_waypoints_live.py` | Record waypoints during teleoperated drive | `rosrun r2_tg30_race record_waypoints_live.py _spacing_m:=0.20` |
| `close_loop.py` | Bridge last waypoint back to first | `python3 close_loop.py --in_yaml waypoints.yaml --out_yaml waypoints_closed.yaml` |
| `waypoint_extractor.py` | Extract from rosbag (offline, map-frame) | `python3 waypoint_extractor.py --bag run.bag --spacing_m 0.20` |
| `waypoint_map_builder.py` | Publish Path + MarkerArray from YAML | Launched by `racing_stack.launch` |
| `pure_pursuit_twist.py` | Pure-pursuit follower (map-frame TF) | Launched by `racing_stack.launch` |
| `follow_the_gap.py` | Reactive obstacle avoidance | Launched by `racing_stack.launch` |
| `steering_modifier.py` | Blend PP + FTG by obstacle proximity | Launched by `racing_stack.launch` |
| `bag_control_recorder.py` | Start/stop bag recording via service | `rosservice call /bag_recorder/set_recording "data: true"` |
| `scan_to_cloud.py` | LaserScan → PointCloud2 | Launched by `scan_cleanup.launch` |
| `twist_to_ackermann.py` | Twist → AckermannDriveStamped | Launched by `racing_stack.launch` |

---

## All Fixes Applied (v1 + v2)

| Component | Fix |
|---|---|
| URDF `laser_joint` | Pitch = **−0.08726646 rad** (exactly −5°), real mass/inertia |
| Pure pursuit | Pose from `map→base_link` TF (was raw `/odom`) |
| Waypoint extractor | TF BufferCore from bag — true map-frame coordinates |
| Cartographer lua | `tracking_frame=imu_link`, `use_imu_data=true`, IMU remapped |
| AMCL | `base_footprint` frame, 500–3000 particles, outdoor laser model |
| Scan height slice | `min_height=0.025m`, `max_height=0.28m` — captures curb/grass |
| FTG | Subscribes to `/scan_obstacles` — curb/grass are automatic obstacles |
| scan_filters | `neighbors=3` preserves thin edge returns |
| All RViz files | 1280×800, left panel open, right hidden, 100×100 grid, scale 40 |
| New: `record_waypoints_live.py` | Live 0.2 m waypoint recorder in map frame |
| New: `close_loop.py` | Loop closure with bridge interpolation + optional smoothing |
| New: `racing.rviz` | Racing view with path, lookahead, obstacles, driving mode |
